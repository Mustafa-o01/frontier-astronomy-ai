"""Benchmark astronomical systems catalog, metadata registry, and Parquet/CSV I/O.

Provides high-performance columnar serialization for light curves (Apache Parquet via pyarrow)
and standardized CSV ingestion for space transmission spectra.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from frontier_astronomy.core.types import BenchmarkSystem, LightCurveData, SpectrumData


# Default directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BENCHMARKS_DIR = DATA_DIR / "benchmarks"


# ==============================================================================
# Curated Benchmark Target Catalog Registry
# ==============================================================================
BENCHMARK_REGISTRY: Dict[str, BenchmarkSystem] = {
    "KIC 12557548": BenchmarkSystem(
        target_id="KIC 12557548",
        common_name="Kepler-1520b",
        category="disintegrating",
        mission="Kepler",
        ra=290.96622,
        dec=51.50472,
        period_days=0.6535538,
        t0_bkjd_or_btjd=120.5683,
        depth_ppm=10000.0,
        duration_hours=1.6,
        host_star_teff=4400.0,
        host_star_radius=0.65,
        host_star_mass=0.70,
        key_features=[
            "Prototype disintegrating rocky exoplanet",
            "Steep ingress and long exponential egress cometary tail",
            "Pre-ingress Mie forward scattering bump",
            "Erratic orbit-to-orbit depth variability (0.1% to 1.3%)",
        ],
        reference="Rappaport et al. 2012, Brogi et al. 2012",
        local_filename="KIC_12557548_kepler.parquet",
    ),
    "EPIC 201637175": BenchmarkSystem(
        target_id="EPIC 201637175",
        common_name="K2-22b",
        category="disintegrating",
        mission="K2",
        ra=169.4828,
        dec=2.6191,
        period_days=0.381078,
        t0_bkjd_or_btjd=1983.121,
        depth_ppm=7500.0,
        duration_hours=0.8,
        host_star_teff=3800.0,
        host_star_radius=0.45,
        host_star_mass=0.40,
        key_features=[
            "Ultra-short period disintegrating planet in K2",
            "Variable depth 0.45% - 1.4%",
            "Leading dust cloud features and chromatic forward scattering",
        ],
        reference="Sanchis-Ojeda et al. 2015",
        local_filename="EPIC_201637175_k2.parquet",
    ),
    "KIC 8639908": BenchmarkSystem(
        target_id="KIC 8639908",
        common_name="KOI-2700b",
        category="disintegrating",
        mission="Kepler",
        ra=297.0035,
        dec=44.7751,
        period_days=0.910022,
        t0_bkjd_or_btjd=132.176,
        depth_ppm=3600.0,
        duration_hours=1.8,
        host_star_teff=4300.0,
        host_star_radius=0.55,
        host_star_mass=0.60,
        key_features=[
            "Second Kepler disintegrating planet",
            "Steady trailing dust cloud morphology",
            "Mild depth variance across quarters",
        ],
        reference="Rappaport et al. 2014",
        local_filename="KIC_8639908_kepler.parquet",
    ),
    "EPIC 201563166": BenchmarkSystem(
        target_id="EPIC 201563166",
        common_name="WD 1145+017",
        category="disintegrating",
        mission="K2",
        ra=179.3193,
        dec=1.4832,
        period_days=0.1876,
        t0_bkjd_or_btjd=2062.15,
        depth_ppm=350000.0,
        duration_hours=0.8,
        host_star_teff=15900.0,
        host_star_radius=0.014,
        host_star_mass=0.60,
        key_features=[
            "Disintegrating planetesimal orbiting helium-rich white dwarf",
            "Catastrophic asymmetric dips up to 50% depth",
            "Rapid dynamic clumping and multi-period fragmentation",
        ],
        reference="Vanderburg et al. 2015",
        local_filename="EPIC_201563166_k2.parquet",
    ),
    "Kepler-1625b": BenchmarkSystem(
        target_id="Kepler-1625b",
        common_name="KIC 4760478",
        category="exomoon_ttv",
        mission="Kepler",
        ra=295.4293,
        dec=39.8865,
        period_days=287.3789,
        t0_bkjd_or_btjd=169.825,
        depth_ppm=12000.0,
        duration_hours=19.0,
        host_star_teff=5550.0,
        host_star_radius=1.79,
        host_star_mass=1.08,
        key_features=[
            "Proposed Neptune-sized exomoon candidate Kepler-1625b I",
            "TTV ~ 78 minute early transit arrival in HST observations",
            "Secondary ~ 500 ppm auxiliary dip detected post-planetary egress",
        ],
        reference="Teachey & Kipping 2018",
        local_filename="Kepler_1625b_kepler.parquet",
    ),
    "Kepler-1708b": BenchmarkSystem(
        target_id="Kepler-1708b",
        common_name="KIC 7906827",
        category="exomoon_ttv",
        mission="Kepler",
        ra=296.8241,
        dec=43.6248,
        period_days=737.11,
        t0_bkjd_or_btjd=289.95,
        depth_ppm=8500.0,
        duration_hours=21.5,
        host_star_teff=6150.0,
        host_star_radius=1.12,
        host_star_mass=1.09,
        key_features=[
            "Mini-Neptune exomoon candidate Kepler-1708b-i",
            "Resolved catalog identifier KIC 7906827",
            "Secondary transit shoulder distortion and egress absorption excess",
        ],
        reference="Kipping et al. 2022",
        local_filename="Kepler_1708b_kepler.parquet",
    ),
    "Kepler-9": BenchmarkSystem(
        target_id="Kepler-9",
        common_name="KIC 3323887",
        category="exomoon_ttv",
        mission="Kepler",
        ra=285.5740,
        dec=38.4009,
        period_days=19.243,
        t0_bkjd_or_btjd=191.16,
        depth_ppm=6000.0,
        duration_hours=4.2,
        host_star_teff=5770.0,
        host_star_radius=1.02,
        host_star_mass=1.00,
        key_features=[
            "Historic first exoplanet system with confirmed TTVs",
            "Planets b and c near 2:1 Mean Motion Resonance",
            "Anti-correlated sinusoidal TTVs with +/- 40 minute amplitudes",
        ],
        reference="Holman et al. 2010",
        local_filename="Kepler_9_kepler.parquet",
    ),
    "Kepler-89": BenchmarkSystem(
        target_id="Kepler-89",
        common_name="KOI-94 / KIC 6462863",
        category="exomoon_ttv",
        mission="Kepler",
        ra=297.3331,
        dec=41.8911,
        period_days=22.34,
        t0_bkjd_or_btjd=145.2,
        depth_ppm=4500.0,
        duration_hours=6.5,
        host_star_teff=6180.0,
        host_star_radius=1.52,
        host_star_mass=1.28,
        key_features=[
            "Four-planet resonant architecture",
            "Planet-planet mutual eclipse observed during primary transit",
            "High-precision TTVs near 5:2 orbital resonance",
        ],
        reference="Hirano et al. 2012",
        local_filename="Kepler_89_kepler.parquet",
    ),
    "WASP-39b": BenchmarkSystem(
        target_id="WASP-39b",
        common_name="WASP-39b",
        category="jwst_atmospheric",
        mission="JWST",
        ra=217.0256,
        dec=-3.4475,
        period_days=4.055259,
        t0_bkjd_or_btjd=2456401.397,
        depth_ppm=21500.0,
        duration_hours=2.8,
        host_star_teff=5400.0,
        host_star_radius=0.932,
        host_star_mass=0.93,
        key_features=[
            "JWST Transiting Exoplanet Community ERS benchmark target",
            "Unprecedented > 25 sigma detection of CO2 at 4.3 um in NIRSpec PRISM",
            "Prominent H2O bands at 1.4, 1.8, 2.7 um and photochemically generated SO2 at 4.05 um",
        ],
        reference="Rustamkulov et al. 2023, Alderson et al. 2023",
        local_filename="WASP_39b_jwst_prism.csv",
    ),
    "WASP-96b": BenchmarkSystem(
        target_id="WASP-96b",
        common_name="WASP-96b",
        category="jwst_atmospheric",
        mission="JWST",
        ra=0.9708,
        dec=-47.3625,
        period_days=3.425,
        t0_bkjd_or_btjd=2456400.1,
        depth_ppm=18000.0,
        duration_hours=2.4,
        host_star_teff=5500.0,
        host_star_radius=1.05,
        host_star_mass=1.06,
        key_features=[
            "JWST Early Release Observations benchmark target",
            "NIRISS SOSS (0.6 - 2.8 um) transmission spectrum",
            "Clear water vapor signature with optical haze slope",
        ],
        reference="JWST Program 2722",
        local_filename="WASP_96b_jwst_niriss.csv",
    ),
}


# ==============================================================================
# Catalog Lookup API
# ==============================================================================
def list_benchmark_systems(category: Optional[str] = None) -> List[BenchmarkSystem]:
    """List all registered benchmark systems, optionally filtered by category."""
    if category is None:
        return list(BENCHMARK_REGISTRY.values())
    return [b for b in BENCHMARK_REGISTRY.values() if b.category == category]


def get_benchmark_system(target_id: str) -> BenchmarkSystem:
    """Retrieve metadata for a benchmark system by target ID or common name."""
    clean_id = target_id.strip()
    if clean_id in BENCHMARK_REGISTRY:
        return BENCHMARK_REGISTRY[clean_id]

    # Search by common name or case-insensitive match
    for b in BENCHMARK_REGISTRY.values():
        if clean_id.lower() in (b.target_id.lower(), b.common_name.lower()):
            return b

    raise KeyError(f"Target '{target_id}' not found in benchmark catalog.")


# ==============================================================================
# Parquet Serialization for LightCurveData
# ==============================================================================
def save_light_curve_parquet(lc: LightCurveData, filepath: Union[str, Path]) -> None:
    """Save LightCurveData to an Apache Parquet columnar file using pyarrow.

    Embeds target metadata and coordinates in the Parquet file key-value metadata.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_arrays(
        [
            pa.array(lc.time, type=pa.float64()),
            pa.array(lc.flux, type=pa.float64()),
            pa.array(lc.flux_err, type=pa.float64()),
            pa.array(lc.quality, type=pa.int32()),
        ],
        names=["time", "flux", "flux_err", "quality"],
    )

    # Encode metadata as JSON in schema metadata
    custom_metadata = {
        "target_id": lc.target_id,
        "mission": lc.mission,
        "ra": str(lc.ra),
        "dec": str(lc.dec),
        "user_metadata": json.dumps(lc.metadata),
    }

    existing_meta = table.schema.metadata or {}
    combined_meta = {
        **{k.encode("utf-8"): v.encode("utf-8") for k, v in custom_metadata.items()},
        **existing_meta,
    }
    table = table.replace_schema_metadata(combined_meta)

    pq.write_table(table, path, compression="snappy")


def load_light_curve_parquet(filepath: Union[str, Path]) -> LightCurveData:
    """Load LightCurveData from an Apache Parquet file using pyarrow."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Parquet light curve file not found: {path}")

    table = pq.read_table(path)
    meta = table.schema.metadata or {}

    target_id = meta.get(b"target_id", b"UNKNOWN").decode("utf-8")
    mission = meta.get(b"mission", b"Kepler").decode("utf-8")
    ra = float(meta.get(b"ra", b"0.0").decode("utf-8"))
    dec = float(meta.get(b"dec", b"0.0").decode("utf-8"))

    user_meta_json = meta.get(b"user_metadata", b"{}").decode("utf-8")
    try:
        user_meta = json.loads(user_meta_json)
    except Exception:
        user_meta = {}

    df = table.to_pandas()
    return LightCurveData(
        target_id=target_id,
        mission=mission,
        time=df["time"].to_numpy(dtype=np.float64),
        flux=df["flux"].to_numpy(dtype=np.float64),
        flux_err=df["flux_err"].to_numpy(dtype=np.float64),
        quality=df["quality"].to_numpy(dtype=np.int32),
        ra=ra,
        dec=dec,
        metadata=user_meta,
    )


# ==============================================================================
# CSV Serialization for SpectrumData
# ==============================================================================
def save_spectrum_csv(spec: SpectrumData, filepath: Union[str, Path]) -> None:
    """Save SpectrumData to a standardized CSV format."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame({
        "wavelength_um": spec.wavelength,
        "transit_depth": spec.transit_depth,
        "uncertainty": spec.uncertainty,
    })

    # Header comments storing target and instrument
    header_comment = f"# target_id: {spec.target_id}\n# instrument: {spec.instrument}\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(header_comment)
        df.to_csv(f, index=False)


def load_spectrum_csv(filepath: Union[str, Path], target_id: Optional[str] = None) -> SpectrumData:
    """Load SpectrumData from a standardized CSV file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Spectrum CSV file not found: {path}")

    tid = target_id or "UNKNOWN"
    instrument = "NIRSpec_PRISM"

    # Read comment metadata headers
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                if "target_id:" in line and target_id is None:
                    tid = line.split("target_id:", 1)[1].strip()
                elif "instrument:" in line:
                    instrument = line.split("instrument:", 1)[1].strip()
            else:
                break

    df = pd.read_csv(path, comment="#")
    wl_col = [c for c in df.columns if "wave" in c.lower() or "lambda" in c.lower()][0]
    depth_col = [c for c in df.columns if "depth" in c.lower() or "transit" in c.lower()][0]
    err_col = [c for c in df.columns if "err" in c.lower() or "unc" in c.lower()][0]

    return SpectrumData(
        target_id=tid,
        instrument=instrument,
        wavelength=df[wl_col].to_numpy(dtype=np.float64),
        transit_depth=df[depth_col].to_numpy(dtype=np.float64),
        uncertainty=df[err_col].to_numpy(dtype=np.float64),
    )


# ==============================================================================
# Bundled Benchmark Data Loaders
# ==============================================================================
def load_benchmark_light_curve(target_id: str, benchmarks_dir: Optional[Path] = None) -> LightCurveData:
    """Load a bundled benchmark light curve by target ID or common name.

    If the parquet file exists in data/benchmarks/, it loads it directly.
    """
    b = get_benchmark_system(target_id)
    b_dir = benchmarks_dir or BENCHMARKS_DIR
    target_file = b_dir / b.local_filename

    if target_file.exists():
        return load_light_curve_parquet(target_file)

    raise FileNotFoundError(
        f"Benchmark light curve for '{target_id}' not found at {target_file}. "
        "Run the benchmark initialization routine to bundle fixtures."
    )


def load_benchmark_spectrum(target_id: str, benchmarks_dir: Optional[Path] = None) -> SpectrumData:
    """Load a bundled benchmark JWST transmission spectrum."""
    b = get_benchmark_system(target_id)
    b_dir = benchmarks_dir or BENCHMARKS_DIR
    target_file = b_dir / b.local_filename

    if target_file.exists():
        return load_spectrum_csv(target_file)

    raise FileNotFoundError(
        f"Benchmark spectrum for '{target_id}' not found at {target_file}. "
        "Run the benchmark initialization routine to bundle fixtures."
    )
