"""Frontier Astronomy AI Discovery Suite.

High-performance astrophysics detection and atmospheric inversion platform
for NASA observational archives (Kepler, K2, TESS, JWST).
"""

__version__ = "0.1.0"
__author__ = "Frontier Astronomy AI Discovery Suite Team"

from frontier_astronomy.core.types import (
    LightCurveData,
    FoldedTransit,
    DustTailDetectionResult,
    ExomoonPerturbationResult,
    SpectrumData,
    AtmosphericInversionResult,
)

__all__ = [
    "__version__",
    "LightCurveData",
    "FoldedTransit",
    "DustTailDetectionResult",
    "ExomoonPerturbationResult",
    "SpectrumData",
    "AtmosphericInversionResult",
]
