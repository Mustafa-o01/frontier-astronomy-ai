"""Typed dataclasses and interface contracts for the Frontier Astronomy AI Discovery Suite.

All contracts follow the architectural specifications defined in PROJECT.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass(frozen=True)
class LightCurveData:
    """Represents calibrated photometric time-series observations.

    Standard container passed between ingestion, preprocessing, and detection pipelines.
    """
    target_id: str                      # e.g., "KIC 12557548" or "TIC 261136679"
    mission: str                        # "Kepler", "K2", or "TESS"
    time: np.ndarray                    # 1D float64 array of BKJD or BTJD cadences
    flux: np.ndarray                    # 1D float64 array of normalized PDC flux
    flux_err: np.ndarray                # 1D float64 array of 1-sigma photometric uncertainty
    quality: np.ndarray                 # 1D int32 array of NASA quality flags (0 = nominal)
    ra: float                           # Target right ascension (degrees)
    dec: float                          # Target declination (degrees)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Header parameters

    def __post_init__(self) -> None:
        # Ensure NumPy array types and 1D dimensionality
        time_arr = np.asarray(self.time, dtype=np.float64)
        flux_arr = np.asarray(self.flux, dtype=np.float64)
        flux_err_arr = np.asarray(self.flux_err, dtype=np.float64)
        qual_arr = np.asarray(self.quality, dtype=np.int32)

        if not (time_arr.ndim == flux_arr.ndim == flux_err_arr.ndim == qual_arr.ndim == 1):
            raise ValueError(
                f"All light curve arrays must be 1D. Got shapes: time={time_arr.shape}, "
                f"flux={flux_arr.shape}, flux_err={flux_err_arr.shape}, quality={qual_arr.shape}"
            )
        if not (len(time_arr) == len(flux_arr) == len(flux_err_arr) == len(qual_arr)):
            raise ValueError(
                f"Length mismatch: time={len(time_arr)}, flux={len(flux_arr)}, "
                f"flux_err={len(flux_err_arr)}, quality={len(qual_arr)}"
            )

        object.__setattr__(self, "time", time_arr)
        object.__setattr__(self, "flux", flux_arr)
        object.__setattr__(self, "flux_err", flux_err_arr)
        object.__setattr__(self, "quality", qual_arr)

    @property
    def n_points(self) -> int:
        """Total number of cadences in light curve."""
        return len(self.time)

    @property
    def time_span_days(self) -> float:
        """Total baseline duration in days."""
        if len(self.time) == 0:
            return 0.0
        return float(np.ptp(self.time))

    @property
    def median_flux(self) -> float:
        """Median flux level."""
        if len(self.flux) == 0:
            return 0.0
        return float(np.nanmedian(self.flux))

    def copy_with(
        self,
        time: Optional[np.ndarray] = None,
        flux: Optional[np.ndarray] = None,
        flux_err: Optional[np.ndarray] = None,
        quality: Optional[np.ndarray] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LightCurveData:
        """Return a modified copy with new arrays or metadata."""
        return LightCurveData(
            target_id=self.target_id,
            mission=self.mission,
            time=self.time if time is None else time,
            flux=self.flux if flux is None else flux,
            flux_err=self.flux_err if flux_err is None else flux_err,
            quality=self.quality if quality is None else quality,
            ra=self.ra,
            dec=self.dec,
            metadata=dict(self.metadata if metadata is None else metadata),
        )


@dataclass(frozen=True)
class FoldedTransit:
    """Represents a phase-folded and epoch-indexed transit profile."""
    phase: np.ndarray                   # Orbital phase in [-0.5, 0.5)
    flux: np.ndarray                    # Normalized flux sorted by phase
    flux_err: np.ndarray                # Uncertainty array
    epoch_indices: np.ndarray           # Integer transit epoch identifier per cadence
    period: float                       # Orbital period in days
    t0: float                           # Transit epoch (BKJD/BTJD)

    def __post_init__(self) -> None:
        phase_arr = np.asarray(self.phase, dtype=np.float64)
        flux_arr = np.asarray(self.flux, dtype=np.float64)
        flux_err_arr = np.asarray(self.flux_err, dtype=np.float64)
        epochs_arr = np.asarray(self.epoch_indices, dtype=np.int32)

        if not (len(phase_arr) == len(flux_arr) == len(flux_err_arr) == len(epochs_arr)):
            raise ValueError(
                f"Length mismatch in FoldedTransit: phase={len(phase_arr)}, flux={len(flux_arr)}, "
                f"flux_err={len(flux_err_arr)}, epoch_indices={len(epochs_arr)}"
            )

        object.__setattr__(self, "phase", phase_arr)
        object.__setattr__(self, "flux", flux_arr)
        object.__setattr__(self, "flux_err", flux_err_arr)
        object.__setattr__(self, "epoch_indices", epochs_arr)

    @property
    def n_points(self) -> int:
        return len(self.phase)


@dataclass(frozen=True)
class DustTailDetectionResult:
    """Detection output contract for Disintegrating Exoplanet & Dust Tail Hunter."""
    target_id: str
    period: float
    t0: float
    is_asymmetric_dust_tail: bool       # True if Delta-BIC >= 10 and LRT p < 1e-5
    delta_bic: float                    # BIC(symmetric) - BIC(dust_tail)
    lrt_p_value: float                  # Likelihood ratio test p-value
    asymmetry_parameter: float          # alpha = (t_egress - t_ingress) / t_total
    peak_depth: float                   # Peak transit extinction
    tail_decay_length: float            # lambda_tail (phase units)
    forward_scattering_amp: float       # f_scat amplitude
    depth_variance: float               # Variance of transit depths across epochs
    best_fit_model: np.ndarray          # Model flux array evaluated at phase

    def __post_init__(self) -> None:
        object.__setattr__(self, "best_fit_model", np.asarray(self.best_fit_model, dtype=np.float64))


@dataclass(frozen=True)
class ExomoonPerturbationResult:
    """Detection output contract for Exomoon & Trojan World Perturbation Detector."""
    target_id: str
    period: float
    ttv_amplitudes: np.ndarray          # O-C timing residual per epoch (minutes)
    tdv_amplitudes: np.ndarray          # Transit duration variation per epoch (minutes)
    has_exomoon_candidate: bool         # True if TTV SNR >= 3.0 and pi/2 phase invariant holds
    ttv_snr: float                      # Signal-to-noise ratio of TTV oscillation
    orthogonal_phase_diff_deg: float    # Phase difference (degrees), nominal = 90.0
    has_secondary_shoulder: bool        # Ingress/egress anomaly detected
    shoulder_snr: float                 # Anomaly significance
    has_trojan_candidate: bool          # L4/L5 co-orbital dip detected (+/- 60 deg)
    trojan_lag_depth: float             # Depth of L4/L5 dip
    p_moon_posterior: float             # Bayesian posterior probability of satellite

    def __post_init__(self) -> None:
        object.__setattr__(self, "ttv_amplitudes", np.asarray(self.ttv_amplitudes, dtype=np.float64))
        object.__setattr__(self, "tdv_amplitudes", np.asarray(self.tdv_amplitudes, dtype=np.float64))


@dataclass(frozen=True)
class SpectrumData:
    """Input contract for JWST Transmission Spectrophotometry."""
    target_id: str                      # e.g., "WASP-39b"
    instrument: str                     # e.g., "NIRSpec_PRISM"
    wavelength: np.ndarray              # Wavelength array in microns (0.6 - 5.3 um)
    transit_depth: np.ndarray           # Observed transit depth (Rp/R*)^2 or ppm
    uncertainty: np.ndarray             # 1-sigma uncertainty array

    def __post_init__(self) -> None:
        wl = np.asarray(self.wavelength, dtype=np.float64)
        depth = np.asarray(self.transit_depth, dtype=np.float64)
        err = np.asarray(self.uncertainty, dtype=np.float64)

        if not (len(wl) == len(depth) == len(err)):
            raise ValueError(
                f"Length mismatch in SpectrumData: wavelength={len(wl)}, "
                f"transit_depth={len(depth)}, uncertainty={len(err)}"
            )

        object.__setattr__(self, "wavelength", wl)
        object.__setattr__(self, "transit_depth", depth)
        object.__setattr__(self, "uncertainty", err)

    @property
    def n_channels(self) -> int:
        return len(self.wavelength)


@dataclass(frozen=True)
class AtmosphericInversionResult:
    """Output contract for JWST Rapid Atmospheric Chemistry Inversion."""
    target_id: str
    medians: Dict[str, float]           # Median posterior values
    err_lower: Dict[str, float]         # 1-sigma lower bounds (16th percentile)
    err_upper: Dict[str, float]         # 1-sigma upper bounds (84th percentile)
    posterior_samples: np.ndarray       # Shape (N_samples, 7)
    reconstructed_spectrum: np.ndarray  # Best-fit transit depth at instrument wavelengths
    chi2: float                         # Goodness of fit
    inference_time_seconds: float       # Elapsed runtime (< 0.1s)

    def __post_init__(self) -> None:
        object.__setattr__(self, "posterior_samples", np.asarray(self.posterior_samples, dtype=np.float64))
        object.__setattr__(self, "reconstructed_spectrum", np.asarray(self.reconstructed_spectrum, dtype=np.float64))

    @property
    def param_medians(self) -> Dict[str, float]:
        """Alias for medians for backward compatibility with benchmark tests."""
        return self.medians


@dataclass(frozen=True)
class BenchmarkSystem:
    """Metadata catalog entry for curated benchmark astronomical systems."""
    target_id: str                      # Primary name, e.g. "KIC 12557548"
    common_name: str                    # e.g. "Kepler-1520b"
    category: str                       # "disintegrating", "exomoon_ttv", "jwst_atmospheric"
    mission: str                        # "Kepler", "K2", "TESS", "JWST"
    ra: float                           # Celestial RA (degrees)
    dec: float                          # Celestial Dec (degrees)
    period_days: Optional[float] = None
    t0_bkjd_or_btjd: Optional[float] = None
    depth_ppm: Optional[float] = None
    duration_hours: Optional[float] = None
    host_star_teff: Optional[float] = None
    host_star_radius: Optional[float] = None
    host_star_mass: Optional[float] = None
    key_features: List[str] = field(default_factory=list)
    reference: str = ""
    local_filename: str = ""
