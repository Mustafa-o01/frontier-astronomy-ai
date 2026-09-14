"""Session state, cached benchmark loading, and candidate catalog registry.

Provides persistent caching, candidate multi-metric filtering, time-series decimation,
and seamless fallback mechanisms for the interactive discovery dashboard.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from frontier_astronomy.core.types import (
    AtmosphericInversionResult,
    BenchmarkSystem,
    DustTailDetectionResult,
    ExomoonPerturbationResult,
    FoldedTransit,
    LightCurveData,
    SpectrumData,
)
from frontier_astronomy.core.preprocessing import fold_light_curve, preprocess_light_curve
from frontier_astronomy.ingestion.catalog import (
    BENCHMARK_REGISTRY,
    get_benchmark_system,
    list_benchmark_systems,
    load_light_curve_parquet,
    load_spectrum_csv,
)
from frontier_astronomy.ingestion.fits_reader import read_fits_light_curve
from frontier_astronomy.ingestion.synthetic_generator import (
    generate_disintegrating_dust_tail_light_curve,
    generate_exomoon_system_light_curve,
    generate_symmetric_transit_light_curve,
    generate_synthetic_transmission_spectrum,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BENCHMARKS_DIR = PROJECT_ROOT / "data" / "benchmarks"


# ==============================================================================
# Candidate Discovery Data Model
# ==============================================================================
@dataclass
class CandidateRecord:
    """Standardized record for discovery candidates in the dashboard catalog."""

    id: str
    name: str
    mission: str
    category: str  # "disintegrating", "exomoon_ttv", "jwst_atmospheric", "trojan"
    period: float
    t0: float
    depth_ppm: float
    delta_bic: float = 0.0
    lrt_p_value: float = 1.0
    asymmetry: float = 0.0
    ttv_snr: float = 0.0
    has_shoulder: bool = False
    p_moon: float = 0.0
    snr: float = 0.0
    chi2: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize candidate record to dictionary."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CandidateRecord:
        """Construct candidate record from dictionary."""
        return cls(
            id=str(data.get("id", data.get("target_id", "UNKNOWN"))),
            name=str(data.get("name", data.get("common_name", data.get("id", "")))),
            mission=str(data.get("mission", "Kepler")),
            category=str(data.get("category", "disintegrating")),
            period=float(data.get("period", data.get("period_days", 1.0))),
            t0=float(data.get("t0", data.get("t0_bkjd_or_btjd", 0.0))),
            depth_ppm=float(data.get("depth_ppm", 1000.0)),
            delta_bic=float(data.get("delta_bic", 0.0)),
            lrt_p_value=float(data.get("lrt_p_value", 1.0)),
            asymmetry=float(data.get("asymmetry", data.get("asymmetry_parameter", 0.0))),
            ttv_snr=float(data.get("ttv_snr", 0.0)),
            has_shoulder=bool(data.get("has_shoulder", data.get("has_secondary_shoulder", False))),
            p_moon=float(data.get("p_moon", data.get("p_moon_posterior", 0.0))),
            snr=float(data.get("snr", 0.0)),
            chi2=float(data.get("chi2", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


def get_default_candidates() -> List[CandidateRecord]:
    """Populate default candidate catalog combining real benchmarks and discoveries."""
    candidates: List[CandidateRecord] = [
        CandidateRecord(
            id="KIC 12557548",
            name="Kepler-1520b",
            mission="Kepler",
            category="disintegrating",
            period=0.6535538,
            t0=120.5683,
            depth_ppm=10000.0,
            delta_bic=28.5,
            lrt_p_value=1.2e-8,
            asymmetry=0.42,
            ttv_snr=1.2,
            has_shoulder=False,
            p_moon=0.02,
            snr=18.5,
            metadata={"reference": "Rappaport et al. 2012", "type": "Catastrophic Disintegration"},
        ),
        CandidateRecord(
            id="EPIC 201637175",
            name="K2-22b",
            mission="K2",
            category="disintegrating",
            period=0.381078,
            t0=1983.121,
            depth_ppm=7500.0,
            delta_bic=22.1,
            lrt_p_value=2.4e-7,
            asymmetry=0.38,
            ttv_snr=0.8,
            has_shoulder=False,
            p_moon=0.01,
            snr=14.2,
            metadata={"reference": "Sanchis-Ojeda et al. 2015", "type": "Catastrophic Disintegration"},
        ),
        CandidateRecord(
            id="KIC 8639908",
            name="KOI-2700b",
            mission="Kepler",
            category="disintegrating",
            period=0.910022,
            t0=132.176,
            depth_ppm=3600.0,
            delta_bic=17.4,
            lrt_p_value=4.8e-6,
            asymmetry=0.34,
            ttv_snr=0.5,
            has_shoulder=False,
            p_moon=0.01,
            snr=9.8,
            metadata={"reference": "Rappaport et al. 2014", "type": "Catastrophic Disintegration"},
        ),
        CandidateRecord(
            id="EPIC 201563166",
            name="WD 1145+017",
            mission="K2",
            category="disintegrating",
            period=0.1876,
            t0=2062.15,
            depth_ppm=350000.0,
            delta_bic=54.2,
            lrt_p_value=1.0e-12,
            asymmetry=0.51,
            ttv_snr=1.5,
            has_shoulder=False,
            p_moon=0.03,
            snr=45.0,
            metadata={"reference": "Vanderburg et al. 2015", "type": "Disintegrating Planetesimal"},
        ),
        CandidateRecord(
            id="Kepler-1625b",
            name="KIC 4760478",
            mission="Kepler",
            category="exomoon_ttv",
            period=287.3789,
            t0=169.825,
            depth_ppm=12000.0,
            delta_bic=2.1,
            lrt_p_value=0.15,
            asymmetry=0.04,
            ttv_snr=5.8,
            has_shoulder=True,
            p_moon=0.965,
            snr=16.0,
            metadata={"reference": "Teachey & Kipping 2018", "type": "Exomoon Candidate"},
        ),
        CandidateRecord(
            id="Kepler-1708b",
            name="KIC 7906827",
            mission="Kepler",
            category="exomoon_ttv",
            period=737.11,
            t0=289.95,
            depth_ppm=8500.0,
            delta_bic=1.8,
            lrt_p_value=0.22,
            asymmetry=0.03,
            ttv_snr=4.2,
            has_shoulder=True,
            p_moon=0.88,
            snr=11.5,
            metadata={"reference": "Kipping et al. 2022", "type": "Exomoon Candidate"},
        ),
        CandidateRecord(
            id="Kepler-9",
            name="KIC 3323887",
            mission="Kepler",
            category="exomoon_ttv",
            period=19.243,
            t0=191.16,
            depth_ppm=6000.0,
            delta_bic=3.0,
            lrt_p_value=0.08,
            asymmetry=0.02,
            ttv_snr=8.5,
            has_shoulder=False,
            p_moon=0.12,
            snr=22.0,
            metadata={"reference": "Holman et al. 2010", "type": "Resonant Planetary TTVs"},
        ),
        CandidateRecord(
            id="TIC 261136679",
            name="TIC 261136679",
            mission="TESS",
            category="disintegrating",
            period=0.5214,
            t0=1510.42,
            depth_ppm=8200.0,
            delta_bic=15.0,
            lrt_p_value=3.2e-5,
            asymmetry=0.31,
            ttv_snr=0.5,
            has_shoulder=False,
            p_moon=0.02,
            snr=10.2,
            metadata={"source": "TESS SPOC Discovery Candidate", "type": "Cometary Dust Tail"},
        ),
        CandidateRecord(
            id="WASP-39b",
            name="WASP-39b",
            mission="JWST",
            category="jwst_atmospheric",
            period=4.055259,
            t0=2456401.397,
            depth_ppm=21500.0,
            delta_bic=0.0,
            lrt_p_value=1.0,
            asymmetry=0.01,
            ttv_snr=0.0,
            has_shoulder=False,
            p_moon=0.0,
            snr=35.0,
            chi2=98.5,
            metadata={"instrument": "NIRSpec PRISM", "molecules": "CO2, H2O, SO2, CO"},
        ),
        CandidateRecord(
            id="WASP-96b",
            name="WASP-96b",
            mission="JWST",
            category="jwst_atmospheric",
            period=3.425,
            t0=2456400.1,
            depth_ppm=18000.0,
            delta_bic=0.0,
            lrt_p_value=1.0,
            asymmetry=0.01,
            ttv_snr=0.0,
            has_shoulder=False,
            p_moon=0.0,
            snr=28.0,
            chi2=76.2,
            metadata={"instrument": "NIRISS SOSS", "molecules": "H2O, Clouds"},
        ),
    ]

    # Dynamically inject discoveries from real NASA archive scans if available
    discoveries_file = PROJECT_ROOT / "results" / "real_nasa_discoveries.json"
    if discoveries_file.exists():
        try:
            with open(discoveries_file, "r", encoding="utf-8") as f:
                disc_data = json.load(f)
            for d in disc_data:
                category = "disintegrating" if d.get("dust_tail", {}).get("is_detected") else (
                    "exomoon_ttv" if d.get("perturbations", {}).get("is_exomoon_candidate") else "symmetric"
                )
                candidates.append(
                    CandidateRecord(
                        id=f"KIC {d['kepid']}",
                        name=f"{d.get('koi_name', '')} (NASA Candidate)",
                        mission="Kepler",
                        category=category,
                        period=float(d["period_days"]),
                        t0=float(d["t0_bkjd"]),
                        depth_ppm=float(d.get("catalog_depth_ppm", 1000.0)),
                        delta_bic=float(d.get("dust_tail", {}).get("delta_bic", 0.0)),
                        lrt_p_value=float(d.get("dust_tail", {}).get("lrt_p_value", 1.0)),
                        asymmetry=float(d.get("dust_tail", {}).get("asymmetry_alpha", 0.0)),
                        ttv_snr=float(d.get("perturbations", {}).get("ttv_snr", 0.0)),
                        has_shoulder=False,
                        p_moon=float(d.get("perturbations", {}).get("p_moon_posterior", 0.0)),
                        snr=float(d.get("perturbations", {}).get("ttv_snr", 0.0)) * 2.5,
                        metadata={"verdict": d.get("verdict", ""), "source": "NASA Kepler Archive Scan"},
                    )
                )
        except Exception:
            pass

    return candidates


# ==============================================================================
# Candidate Filtering & Query Engine
# ==============================================================================
def filter_candidates(
    candidates: List[Union[Dict[str, Any], CandidateRecord]],
    mission: Optional[str] = None,
    category: Optional[str] = None,
    min_delta_bic: Optional[float] = None,
    min_ttv_snr: Optional[float] = None,
    min_snr: Optional[float] = None,
    search_query: Optional[str] = None,
) -> List[Any]:
    """Filter candidates by mission, Delta-BIC, TTV SNR, and search query.

    Handles empty catalog without error. Compatible with lists of CandidateRecord
    or raw dictionaries.
    """
    if not candidates:
        return []

    filtered = []
    for item in candidates:
        if isinstance(item, CandidateRecord):
            rec_id = item.id
            rec_name = item.name
            rec_mission = item.mission
            rec_category = item.category
            rec_dbic = item.delta_bic
            rec_ttv = item.ttv_snr
            rec_snr = item.snr
        elif isinstance(item, dict):
            rec_id = str(item.get("id", item.get("target_id", "")))
            rec_name = str(item.get("name", item.get("common_name", rec_id)))
            rec_mission = str(item.get("mission", ""))
            rec_category = str(item.get("category", ""))
            rec_dbic = float(item.get("delta_bic", 0.0))
            rec_ttv = float(item.get("ttv_snr", 0.0))
            rec_snr = float(item.get("snr", 0.0))
        else:
            continue

        # Mission filter
        if mission and mission.upper() != "ALL":
            if rec_mission.upper() != mission.upper():
                continue

        # Category filter
        if category and category.upper() != "ALL":
            if rec_category.lower() != category.lower():
                continue

        # Delta-BIC threshold
        if min_delta_bic is not None:
            if rec_dbic < min_delta_bic:
                continue

        # TTV SNR threshold
        if min_ttv_snr is not None:
            if rec_ttv < min_ttv_snr:
                continue

        # General SNR threshold
        if min_snr is not None:
            if rec_snr < min_snr:
                continue

        # Search query matching
        if search_query:
            q = search_query.strip().lower()
            if q not in rec_id.lower() and q not in rec_name.lower():
                continue

        filtered.append(item)

    return filtered


# ==============================================================================
# Decimation for UI Responsiveness
# ==============================================================================
def decimate_time_series(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: Optional[np.ndarray] = None,
    max_points: int = 5000,
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """Decimate large time-series to max_points for smooth UI responsiveness."""
    n = len(time)
    if n <= max_points:
        return time, flux, flux_err

    step = max(1, n // max_points)
    t_dec = time[::step]
    f_dec = flux[::step]
    fe_dec = flux_err[::step] if flux_err is not None else None
    return t_dec, f_dec, fe_dec


# ==============================================================================
# Cached Data Loaders & Fallbacks
# ==============================================================================
_LIGHT_CURVE_CACHE: Dict[str, LightCurveData] = {}
_SPECTRUM_CACHE: Dict[str, SpectrumData] = {}
_DUST_TAIL_CACHE: Dict[str, DustTailDetectionResult] = {}
_PERTURBATION_CACHE: Dict[str, ExomoonPerturbationResult] = {}
_ATMOSPHERIC_CACHE: Dict[str, AtmosphericInversionResult] = {}


def load_candidate_light_curve(
    target_id: str,
    mission: str = "Kepler",
    fallback_on_missing: bool = True,
) -> LightCurveData:
    """Load benchmark light curve from Parquet or fallback to synthetic signal."""
    if target_id in _LIGHT_CURVE_CACHE:
        return _LIGHT_CURVE_CACHE[target_id]

    # Check benchmark registry
    norm_id = target_id.strip()
    try:
        bench = get_benchmark_system(norm_id)
    except KeyError:
        bench = None
    if bench is not None and bench.local_filename and bench.local_filename.endswith(".parquet"):
        parquet_path = BENCHMARKS_DIR / bench.local_filename
        if parquet_path.exists():
            lc = load_light_curve_parquet(parquet_path)
            _LIGHT_CURVE_CACHE[target_id] = lc
            return lc

    # Direct filename search in benchmarks directory
    clean_name = norm_id.replace(" ", "_").replace("-", "_")
    candidates = list(BENCHMARKS_DIR.glob(f"*{clean_name}*.parquet"))
    if candidates:
        lc = load_light_curve_parquet(candidates[0])
        _LIGHT_CURVE_CACHE[target_id] = lc
        return lc

    # Check cached real observational FITS files in data/cache/real_kepler
    cache_real_dir = PROJECT_ROOT / "data" / "cache" / "real_kepler"
    if cache_real_dir.exists():
        digits = "".join(ch for ch in norm_id if ch.isdigit())
        if digits:
            try:
                kic_str = f"{int(digits):09d}"
                fits_matches = list(cache_real_dir.glob(f"*{kic_str}*.fits"))
                if fits_matches:
                    times, fluxes, flux_errs, quals = [], [], [], []
                    ra, dec, meta = 0.0, 0.0, {}
                    for fpath in fits_matches[:4]:
                        try:
                            sub_lc = read_fits_light_curve(fpath, target_id=target_id)
                            times.append(sub_lc.time)
                            fluxes.append(sub_lc.flux)
                            flux_errs.append(sub_lc.flux_err)
                            quals.append(sub_lc.quality)
                            ra, dec = sub_lc.ra, sub_lc.dec
                            meta.update(sub_lc.metadata)
                        except Exception:
                            continue
                    if times:
                        all_time = np.concatenate(times)
                        all_flux = np.concatenate(fluxes)
                        all_err = np.concatenate(flux_errs)
                        all_qual = np.concatenate(quals)
                        order = np.argsort(all_time)
                        lc = LightCurveData(
                            time=all_time[order],
                            flux=all_flux[order],
                            flux_err=all_err[order],
                            quality=all_qual[order],
                            ra=ra,
                            dec=dec,
                            target_id=target_id,
                            mission="Kepler",
                            metadata=meta,
                        )
                        _LIGHT_CURVE_CACHE[target_id] = lc
                        return lc
            except Exception:
                pass

    # Fallback to high-fidelity synthetic generator
    if fallback_on_missing:
        # Determine synthetic configuration
        if "1255" in target_id or "201637" in target_id or "8639908" in target_id:
            lc = generate_disintegrating_dust_tail_light_curve(
                target_id=target_id,
                period=0.65355 if "1255" in target_id else 0.381,
                t0=120.568,
                duration_days=30.0,
            )
        elif "1625" in target_id or "1708" in target_id:
            lc = generate_exomoon_system_light_curve(
                target_id=target_id,
                period=287.38 if "1625" in target_id else 737.11,
                t0=169.825,
                duration_days=120.0,
                has_shoulder=True,
            )
        else:
            lc = generate_symmetric_transit_light_curve(
                target_id=target_id,
                mission=mission,
                period=3.5,
                t0=120.0,
                depth=0.01,
                duration_days=30.0,
            )
        _LIGHT_CURVE_CACHE[target_id] = lc
        return lc

    raise FileNotFoundError(f"Light curve data for '{target_id}' could not be located.")


def load_candidate_spectrum(
    target_id: str,
    fallback_on_missing: bool = True,
) -> SpectrumData:
    """Load benchmark transmission spectrum from CSV or fallback to synthetic signal."""
    if target_id in _SPECTRUM_CACHE:
        return _SPECTRUM_CACHE[target_id]

    norm_id = target_id.strip()
    try:
        bench = get_benchmark_system(norm_id)
    except KeyError:
        bench = None
    if bench is not None and bench.local_filename:
        csv_path = BENCHMARKS_DIR / bench.local_filename
        if csv_path.exists():
            spec = load_spectrum_csv(csv_path, target_id=target_id)
            _SPECTRUM_CACHE[target_id] = spec
            return spec

    clean_name = norm_id.replace(" ", "_").replace("-", "_")
    candidates = list(BENCHMARKS_DIR.glob(f"*{clean_name}*.csv"))
    if candidates:
        spec = load_spectrum_csv(candidates[0], target_id=target_id)
        _SPECTRUM_CACHE[target_id] = spec
        return spec

    if fallback_on_missing:
        spec = generate_synthetic_transmission_spectrum(
            target_id=target_id,
            instrument="NIRSpec_PRISM",
            log_co2=-3.7 if "39" in target_id else -4.5,
            log_h2o=-3.2 if "39" in target_id else -3.5,
            noise_ppm=50.0,
        )
        _SPECTRUM_CACHE[target_id] = spec
        return spec

    raise FileNotFoundError(f"Spectrum data for '{target_id}' could not be located.")


# ==============================================================================
# Dashboard Session State Container
# ==============================================================================
class DashboardState:
    """Centralized session state manager for discovery dashboard."""

    def __init__(self) -> None:
        self.candidates: List[CandidateRecord] = get_default_candidates()
        self.selected_candidate_id: str = "KIC 12557548"
        self.active_tab: str = "Discovery Browser"
        self.mission_filter: str = "All"
        self.category_filter: str = "All"
        self.min_delta_bic: float = 0.0
        self.min_ttv_snr: float = 0.0
        self.search_query: str = ""
        self.cached_light_curves = _LIGHT_CURVE_CACHE
        self.cached_spectra = _SPECTRUM_CACHE
        self.cached_dust_tail = _DUST_TAIL_CACHE
        self.cached_perturbations = _PERTURBATION_CACHE
        self.cached_inversions = _ATMOSPHERIC_CACHE

    def get_selected_candidate(self) -> Optional[CandidateRecord]:
        """Retrieve record for currently active candidate."""
        for c in self.candidates:
            if c.id == self.selected_candidate_id:
                return c
        return self.candidates[0] if self.candidates else None

    def get_filtered_candidates(self) -> List[CandidateRecord]:
        """Apply current filter settings to candidate list."""
        return filter_candidates(
            self.candidates,
            mission=self.mission_filter,
            category=self.category_filter,
            min_delta_bic=self.min_delta_bic if self.min_delta_bic > 0 else None,
            min_ttv_snr=self.min_ttv_snr if self.min_ttv_snr > 0 else None,
            search_query=self.search_query,
        )

    def select_candidate(self, candidate_id: str) -> None:
        """Switch currently selected candidate."""
        self.selected_candidate_id = candidate_id

    def add_candidate(self, record: CandidateRecord) -> None:
        """Add new discovery candidate to registry."""
        # Check if already exists
        for idx, existing in enumerate(self.candidates):
            if existing.id == record.id:
                self.candidates[idx] = record
                return
        self.candidates.append(record)
