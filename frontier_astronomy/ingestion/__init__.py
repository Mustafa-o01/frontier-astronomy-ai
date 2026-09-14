"""Data ingestion, FITS binary table reading, MAST REST queries, and synthetic signal generation."""

from frontier_astronomy.ingestion.fits_reader import (
    read_fits_binary_table,
    read_fits_light_curve,
    create_fits_binary_table,
    parse_bintable_dtype,
    read_header_block,
)
from frontier_astronomy.ingestion.mast_client import (
    MASTClient,
    MAST_API_URL,
    MAST_DOWNLOAD_URL,
)
from frontier_astronomy.ingestion.catalog import (
    BENCHMARK_REGISTRY,
    BENCHMARKS_DIR,
    list_benchmark_systems,
    get_benchmark_system,
    save_light_curve_parquet,
    load_light_curve_parquet,
    save_spectrum_csv,
    load_spectrum_csv,
    load_benchmark_light_curve,
    load_benchmark_spectrum,
)
from frontier_astronomy.ingestion.synthetic_generator import (
    generate_disintegrating_dust_tail_light_curve,
    generate_symmetric_transit_light_curve,
    generate_exomoon_perturbation_light_curve,
    generate_trojan_light_curve,
    generate_jwst_transmission_spectrum,
)

__all__ = [
    # FITS Reader
    "read_fits_binary_table",
    "read_fits_light_curve",
    "create_fits_binary_table",
    "parse_bintable_dtype",
    "read_header_block",
    # MAST Client
    "MASTClient",
    "MAST_API_URL",
    "MAST_DOWNLOAD_URL",
    # Catalog & I/O
    "BENCHMARK_REGISTRY",
    "BENCHMARKS_DIR",
    "list_benchmark_systems",
    "get_benchmark_system",
    "save_light_curve_parquet",
    "load_light_curve_parquet",
    "save_spectrum_csv",
    "load_spectrum_csv",
    "load_benchmark_light_curve",
    "load_benchmark_spectrum",
    # Synthetic Generators
    "generate_disintegrating_dust_tail_light_curve",
    "generate_symmetric_transit_light_curve",
    "generate_exomoon_perturbation_light_curve",
    "generate_trojan_light_curve",
    "generate_jwst_transmission_spectrum",
]
