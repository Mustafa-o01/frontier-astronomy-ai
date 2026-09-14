"""NASA MAST REST API and static HTTP client with transparent disk caching and offline fallbacks.

Enables automated discovery and download of Kepler, K2, and TESS space transit data
products from STScI archive endpoints with zero network crashes when offline.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import requests

from frontier_astronomy.core.types import LightCurveData
from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
from frontier_astronomy.ingestion.catalog import BENCHMARKS_DIR, load_benchmark_light_curve, get_benchmark_system


MAST_API_URL: str = "https://mast.stsci.edu/api/v0/invoke"
MAST_DOWNLOAD_URL: str = "https://mast.stsci.edu/api/v0.1/Download/file"

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"


class MASTClient:
    """Client for querying and downloading data from NASA's Mikulski Archive for Space Telescopes (MAST)."""

    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        timeout: float = 10.0,
        offline_only: bool = False,
    ) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.offline_only = offline_only
        self.session = requests.Session()

    def _invoke(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke STScI MAST REST Mashup service."""
        if self.offline_only:
            raise ConnectionError("MAST client is configured in offline-only mode.")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "text/plain",
            "User-Agent": "FrontierAstronomyAI/0.1.0",
        }
        data = {"request": json.dumps(request_payload)}

        response = self.session.post(
            MAST_API_URL,
            data=data,
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def resolve_target(self, target_name: str) -> Dict[str, Any]:
        """Resolve astronomical target identifier to celestial coordinates (RA, Dec) via MAST.

        Returns:
            Dict containing 'ra', 'dec', 'target_name', etc.
        """
        payload = {
            "service": "Mast.Name.Lookup",
            "params": {"input": target_name, "format": "json"},
        }
        resp = self._invoke(payload)
        resolved = resp.get("resolvedCoordinate", [])
        if not resolved:
            raise ValueError(f"Target '{target_name}' could not be resolved by MAST Name Lookup.")

        primary = resolved[0]
        return {
            "target_name": target_name,
            "ra": float(primary.get("ra", 0.0)),
            "dec": float(primary.get("decl", 0.0)),
            "canonical_name": primary.get("canonicalName", target_name),
        }

    def query_observations(
        self,
        target_name: str,
        mission: str = "Kepler",
        product_type: str = "timeseries",
    ) -> List[Dict[str, Any]]:
        """Query MAST CAOM for observations of a target.

        Args:
            target_name: e.g. "KIC 12557548" or "Kepler-1625"
            mission: "Kepler", "K2", or "TESS"
            product_type: "timeseries" (LightCurve) or "image" (TPF)

        Returns:
            List of matching observation metadata records.
        """
        coords = self.resolve_target(target_name)
        ra = coords["ra"]
        dec = coords["dec"]

        payload = {
            "service": "Mast.Caom.Filtered.Position",
            "params": {
                "position": f"{ra}, {dec}, 0.02",
                "filters": [
                    {"paramName": "obs_collection", "values": [mission]},
                    {"paramName": "dataproduct_type", "values": [product_type]},
                ],
                "format": "json",
            },
        }

        resp = self._invoke(payload)
        data = resp.get("data", [])
        return data

    def download_file(
        self,
        data_uri: str,
        output_filename: Optional[str] = None,
    ) -> Path:
        """Download a data file by URI or direct URL, with caching in cache_dir."""
        # Generate cache key from URI
        cache_key = hashlib.sha256(data_uri.encode("utf-8")).hexdigest()[:16]
        if output_filename:
            dest_path = self.cache_dir / output_filename
        else:
            ext = ".fits" if "fits" in data_uri.lower() else ".dat"
            dest_path = self.cache_dir / f"mast_{cache_key}{ext}"

        if dest_path.exists() and dest_path.stat().st_size > 0:
            return dest_path

        if self.offline_only:
            raise ConnectionError(f"Cannot download {data_uri} in offline-only mode and file not cached.")

        # If data_uri is already a full URL
        if data_uri.startswith("http://") or data_uri.startswith("https://"):
            url = data_uri
        else:
            url = f"{MAST_DOWNLOAD_URL}?uri={data_uri}"

        resp = self.session.get(url, stream=True, timeout=self.timeout)
        resp.raise_for_status()

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        return dest_path

    def fetch_light_curve(
        self,
        target_id: str,
        mission: str = "auto",
        quarter_or_sector: Optional[int] = None,
        offline_ok: bool = True,
    ) -> LightCurveData:
        """Fetch a light curve for a target, with transparent offline fallback.

        1. Checks local cache for previously downloaded FITS.
        2. If online, queries MAST API and downloads the latest LC file.
        3. If offline or download fails, checks bundled benchmarks (data/benchmarks/).
        4. If not in benchmarks, raises an informative error.

        Args:
            target_id: Target identifier (e.g. "KIC 12557548", "Kepler-1625b", "TIC 261136679")
            mission: "Kepler", "K2", "TESS", or "auto"
            quarter_or_sector: Optional quarter (Kepler) or sector (TESS) filter
            offline_ok: If True, falls back to bundled benchmarks when offline.

        Returns:
            LightCurveData object
        """
        # 1. First check if cached FITS files match this target in cache_dir
        safe_target = target_id.replace(" ", "_").replace("-", "_")
        cached_matches = list(self.cache_dir.glob(f"*{safe_target}*.fits"))
        if cached_matches:
            return read_fits_light_curve(cached_matches[0], target_id=target_id)

        # 2. Try online MAST download if not in offline-only mode
        if not self.offline_only:
            try:
                obs = self.query_observations(target_id, mission=mission if mission != "auto" else "Kepler")
                if obs:
                    # Pick first matching observation
                    data_uri = obs[0].get("dataURL") or obs[0].get("dataURI")
                    if data_uri:
                        fits_path = self.download_file(data_uri, output_filename=f"{safe_target}.fits")
                        return read_fits_light_curve(fits_path, target_id=target_id)
            except Exception:
                if not offline_ok:
                    raise

        # 3. Offline fallback to bundled benchmarks
        if offline_ok:
            try:
                return load_benchmark_light_curve(target_id)
            except (KeyError, FileNotFoundError):
                pass

        raise FileNotFoundError(
            f"Could not retrieve light curve for '{target_id}' from MAST or local benchmarks."
        )
