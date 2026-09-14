"""Time-series preprocessing and robust detrending for space transit photometry.

Implements:
- NASA quality flag bitmask filtering
- Asymmetric MAD-based outlier & stellar flare rejection
- Iterative Savitzky-Golay detrending with transit masking (preserving cometary dust tails)
- Zero-NaN phase folding, epoch splitting, and inverse-variance weighted binning
"""

from __future__ import annotations

from typing import Optional, Tuple, Union
import numpy as np
from scipy.signal import savgol_filter
from scipy.interpolate import interp1d

from frontier_astronomy.core.types import LightCurveData, FoldedTransit
from frontier_astronomy.core.math_utils import median_absolute_deviation, running_median


def clean_quality(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    quality: np.ndarray,
    strict: bool = True,
    bitmask: Optional[int] = None,
) -> np.ndarray:
    """Return a boolean mask of valid cadences based on NASA quality flags and finite values.

    Args:
        time: 1D cadence timestamps
        flux: 1D flux values
        flux_err: 1D 1-sigma uncertainties
        quality: 1D NASA integer quality bitmask
        strict: If True, requires quality == 0 (all flags clear).
        bitmask: Custom bitmask to test with (quality & bitmask) == 0.

    Returns:
        Boolean mask array where True indicates cadences to keep.
    """
    t = np.asarray(time, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    fe = np.asarray(flux_err, dtype=np.float64)
    q = np.asarray(quality, dtype=np.int32)

    finite_mask = (
        np.isfinite(t)
        & np.isfinite(f)
        & np.isfinite(fe)
        & (fe > 0.0)
        & (f > 0.0)
    )

    if strict:
        quality_mask = (q == 0)
    elif bitmask is not None:
        quality_mask = ((q & bitmask) == 0)
    else:
        # Default permissive bitmask excluding severe issues: slews, safe modes, desaturations
        # Bits: 1 (attitude tweak), 2 (safe mode), 4 (coarse point), 8 (earth point),
        # 16 (zero crossing), 32 (desaturation), 128 (manual exclude)
        severe_bitmask = 1 | 2 | 4 | 8 | 16 | 32 | 128
        quality_mask = ((q & severe_bitmask) == 0)

    return finite_mask & quality_mask


def asymmetric_mad_clip(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: Optional[np.ndarray] = None,
    window_length: int = 101,
    sigma_high: float = 3.5,
    sigma_low: float = 6.0,
    mask_consecutive_flares: bool = True,
    transit_mask: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Identify outliers using asymmetric MAD clipping to preserve transit troughs.

    Standard symmetric clipping inadvertently corrupts cometary dust tails and deep transits.
    This filter applies:
    - Tight threshold (sigma_high ~ 3.5) for positive excursions (stellar flares).
    - Conservative threshold (sigma_low ~ 6.0) for negative excursions (protecting transits).
    - Optional Fast-Rise Exponential-Decay (FRED) flare trailing recovery masking.
    - Optional transit_mask to safeguard in-transit cadences from exclusion.

    Args:
        time: 1D cadence timestamps
        flux: 1D flux values
        flux_err: Optional 1D uncertainties
        window_length: Running median window size in cadences (odd integer >= 5)
        sigma_high: Threshold multiplier for positive outliers (flares)
        sigma_low: Threshold multiplier for negative outliers
        mask_consecutive_flares: If True, masks cadences following a flare until flux returns to baseline.
        transit_mask: Optional boolean array where True cadences are guaranteed retention.

    Returns:
        Boolean mask array where True indicates retained cadences.
    """
    f = np.asarray(flux, dtype=np.float64)
    n = len(f)
    if n < 5:
        return np.ones(n, dtype=bool)

    if window_length < 5:
        window_length = 5
    if window_length % 2 == 0:
        window_length += 1
    if window_length > n:
        window_length = n if n % 2 != 0 else n - 1

    smooth_baseline = running_median(f, window_length)
    residuals = f - smooth_baseline
    mad_val = median_absolute_deviation(residuals)

    if mad_val <= 0.0:
        mad_val = float(np.nanstd(residuals))
        if mad_val <= 0.0:
            return np.ones(n, dtype=bool)

    keep_mask = (residuals >= -sigma_low * mad_val) & (residuals <= sigma_high * mad_val)

    if transit_mask is not None:
        tr_m = np.asarray(transit_mask, dtype=bool)
        if len(tr_m) == len(keep_mask):
            keep_mask = keep_mask | tr_m

    if mask_consecutive_flares:
        # If a positive flare occurred, mask subsequent points until flux returns to < 1.0 * mad_val
        flare_indices = np.where(residuals > sigma_high * mad_val)[0]
        for idx in flare_indices:
            curr = idx + 1
            # Search forward up to 48 cadences (e.g., 24 hours in Kepler LC)
            max_search = min(n, idx + 48)
            while curr < max_search:
                if residuals[curr] > 1.0 * mad_val:
                    keep_mask[curr] = False
                    curr += 1
                else:
                    break

    return keep_mask


def iterative_savgol_detrend(
    time: np.ndarray,
    flux: np.ndarray,
    flux_err: Optional[np.ndarray] = None,
    window_days: float = 1.0,
    polyorder: int = 2,
    transit_mask_sigma: float = 2.5,
    max_iter: int = 3,
    period: Optional[float] = None,
    t0: Optional[float] = None,
    duration_days: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Detrend light curve using iterative Savitzky-Golay filtering with transit masking.

    To avoid clipping or distorting cometary dust tails and deep transits, this routine
    iteratively detects in-transit cadences, masks them, replaces them via linear interpolation
    across out-of-transit boundaries, and fits the smooth stellar continuum exclusively
    on unocculted starlight.

    Args:
        time: 1D array of timestamps (days)
        flux: 1D array of calibrated flux
        flux_err: Optional 1D array of uncertainties
        window_days: SG window duration in days (typically 3x to 5x transit duration)
        polyorder: Polynomial order for Savitzky-Golay filter (usually 2)
        transit_mask_sigma: Negative residual threshold to flag in-transit points
        max_iter: Maximum number of iterative masking passes
        period: Known orbital period in days (optional, for prior masking)
        t0: Known reference transit center (optional)
        duration_days: Known transit duration in days (optional)

    Returns:
        Tuple of (normalized_flux, continuum_flux).
        Normalized flux has median out-of-transit level of 1.0 with zero NaNs.
    """
    t = np.asarray(time, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    n = len(t)

    if n < polyorder + 3:
        # Array too short for filtering; return flat normalization
        med = float(np.nanmedian(f)) if n > 0 else 1.0
        med = 1.0 if med <= 0 else med
        return f / med, np.full_like(f, med)

    # Estimate cadence spacing in days
    diffs = np.diff(t)
    positive_diffs = diffs[diffs > 0]
    cadence_dt = float(np.median(positive_diffs)) if len(positive_diffs) > 0 else 0.0204  # ~29.4 min default

    # Window length in points
    w_pts = int(np.round(window_days / cadence_dt))
    if w_pts <= polyorder:
        w_pts = polyorder + 3
    if w_pts % 2 == 0:
        w_pts += 1
    if w_pts > n:
        w_pts = n if n % 2 != 0 else n - 1
        if w_pts <= polyorder:
            w_pts = polyorder + 1 if (polyorder + 1) % 2 != 0 else polyorder + 2

    # Initial transit mask
    in_transit_mask = np.zeros(n, dtype=bool)
    if period is not None and t0 is not None and duration_days is not None:
        phase = ((t - t0) / period + 0.5) % 1.0 - 0.5
        phase_dur = (duration_days / period) * 1.5  # Mask 1.5x duration to be safe
        in_transit_mask = np.abs(phase) < phase_dur

    f_clean = f.copy()
    continuum = np.ones(n, dtype=np.float64)

    for iteration in range(max_iter):
        # In-transit points are interpolated from surrounding out-of-transit data
        if np.any(in_transit_mask) and not np.all(in_transit_mask):
            unmasked_indices = np.where(~in_transit_mask)[0]
            masked_indices = np.where(in_transit_mask)[0]
            f_clean[masked_indices] = np.interp(
                t[masked_indices],
                t[unmasked_indices],
                f_clean[unmasked_indices],
            )

        # Apply Savitzky-Golay filter
        continuum = savgol_filter(f_clean, window_length=w_pts, polyorder=polyorder, mode="interp")

        # Prevent division by zero or negative continuum
        continuum = np.where(continuum <= 0.0, np.nanmedian(f), continuum)

        # Compute residuals relative to continuum
        residuals = f / continuum
        mad_res = median_absolute_deviation(residuals - 1.0)
        if mad_res <= 0:
            mad_res = float(np.nanstd(residuals))
            if mad_res <= 0:
                break

        # Flag significant negative dips as transit/dust tail
        new_transit_mask = residuals < (1.0 - transit_mask_sigma * mad_res)

        # If ephemeris was provided, combine with prior mask
        if period is not None:
            new_transit_mask = new_transit_mask | in_transit_mask

        # If mask converged or all points are masked, stop
        if np.all(new_transit_mask) or np.array_equal(new_transit_mask, in_transit_mask):
            in_transit_mask = new_transit_mask
            break

        in_transit_mask = new_transit_mask

    # Final normalization
    normalized_flux = f / continuum

    # Clean any accidental non-finite values
    bad_idx = ~np.isfinite(normalized_flux)
    if np.any(bad_idx):
        normalized_flux[bad_idx] = 1.0

    return normalized_flux, continuum


def phase_fold(
    time: np.ndarray,
    period: float,
    t0: float,
) -> np.ndarray:
    """Fold timestamps into orbital phase [-0.5, 0.5).

    Phase phi = 0 corresponds to transit center t0.

    Args:
        time: 1D array of timestamps
        period: Orbital period in same time units as timestamps
        t0: Mid-transit epoch in same time units

    Returns:
        1D array of orbital phases strictly in [-0.5, 0.5).
    """
    if period <= 0:
        raise ValueError(f"Orbital period must be strictly positive, got {period}")
    t = np.asarray(time, dtype=np.float64)
    phase = ((t - t0) / period + 0.5) % 1.0 - 0.5
    return phase


def epoch_split(
    time: np.ndarray,
    period: float,
    t0: float,
) -> np.ndarray:
    """Compute integer transit epoch index for each cadence timestamp.

    Epoch 0 corresponds to the transit closest to t0.

    Args:
        time: 1D array of timestamps
        period: Orbital period
        t0: Reference transit epoch

    Returns:
        1D array of integer transit epoch numbers (int32).
    """
    if period <= 0:
        raise ValueError(f"Orbital period must be strictly positive, got {period}")
    t = np.asarray(time, dtype=np.float64)
    epochs = np.round((t - t0) / period).astype(np.int32)
    return epochs


def fold_light_curve(
    lc: LightCurveData,
    period: float,
    t0: float,
    sort: bool = True,
) -> FoldedTransit:
    """Fold a LightCurveData object into a FoldedTransit container.

    Args:
        lc: Input LightCurveData
        period: Orbital period in days
        t0: Transit epoch
        sort: If True, sorts records monotonically by orbital phase.

    Returns:
        FoldedTransit dataclass.
    """
    phase = phase_fold(lc.time, period, t0)
    epochs = epoch_split(lc.time, period, t0)
    flux = lc.flux.copy()
    flux_err = lc.flux_err.copy()

    if sort:
        sort_order = np.argsort(phase)
        phase = phase[sort_order]
        flux = flux[sort_order]
        flux_err = flux_err[sort_order]
        epochs = epochs[sort_order]

    return FoldedTransit(
        phase=phase,
        flux=flux,
        flux_err=flux_err,
        epoch_indices=epochs,
        period=float(period),
        t0=float(t0),
    )


def inverse_variance_bin(
    phase: np.ndarray,
    flux: np.ndarray,
    flux_err: np.ndarray,
    n_bins: int = 300,
    phase_min: float = -0.5,
    phase_max: float = 0.5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Perform inverse-variance weighted binning of phase-folded photometry.

    Weights: w_i = 1 / sigma_i^2
    Binned flux: F_bar = sum(w_i * F_i) / sum(w_i)
    Binned uncertainty: sigma_bar = max( 1 / sqrt(sum(w_i)), std(F_i) / sqrt(N_bin) )

    Empty bins are omitted, guaranteeing zero NaNs in returned arrays.

    Args:
        phase: 1D array of orbital phases
        flux: 1D array of normalized flux
        flux_err: 1D array of 1-sigma uncertainties
        n_bins: Number of uniform phase bins across [phase_min, phase_max]
        phase_min: Lower bound of phase range (default -0.5)
        phase_max: Upper bound of phase range (default 0.5)

    Returns:
        Tuple of (bin_centers, binned_flux, binned_err, bin_counts).
    """
    p = np.asarray(phase, dtype=np.float64)
    f = np.asarray(flux, dtype=np.float64)
    fe = np.asarray(flux_err, dtype=np.float64)

    valid = np.isfinite(p) & np.isfinite(f) & np.isfinite(fe) & (fe > 0)
    p = p[valid]
    f = f[valid]
    fe = fe[valid]

    if len(p) == 0:
        empty = np.array([], dtype=np.float64)
        return empty, empty, empty, np.array([], dtype=np.int32)

    bin_edges = np.linspace(phase_min, phase_max, n_bins + 1)
    bin_idx = np.digitize(p, bin_edges) - 1

    centers_list = []
    flux_list = []
    err_list = []
    count_list = []

    weights = 1.0 / (fe ** 2)

    for k in range(n_bins):
        in_bin = (bin_idx == k)
        n_pts = int(np.sum(in_bin))
        if n_pts == 0:
            continue

        p_k = p[in_bin]
        f_k = f[in_bin]
        w_k = weights[in_bin]

        sum_w = np.sum(w_k)
        if sum_w <= 0:
            continue

        bin_center = 0.5 * (bin_edges[k] + bin_edges[k + 1])
        weighted_flux = float(np.sum(w_k * f_k) / sum_w)

        # Theoretical propagated photon noise
        sigma_poisson = float(1.0 / np.sqrt(sum_w))

        # Empirical scatter in bin (accounts for red noise)
        if n_pts > 1:
            sigma_empirical = float(np.std(f_k, ddof=1) / np.sqrt(n_pts))
        else:
            sigma_empirical = sigma_poisson

        final_err = max(sigma_poisson, sigma_empirical)

        centers_list.append(bin_center)
        flux_list.append(weighted_flux)
        err_list.append(final_err)
        count_list.append(n_pts)

    return (
        np.array(centers_list, dtype=np.float64),
        np.array(flux_list, dtype=np.float64),
        np.array(err_list, dtype=np.float64),
        np.array(count_list, dtype=np.int32),
    )


def preprocess_light_curve(
    lc: LightCurveData,
    strict_quality: bool = True,
    clip_outliers: bool = True,
    detrend: bool = True,
    window_days: float = 1.0,
    polyorder: int = 2,
    period: Optional[float] = None,
    t0: Optional[float] = None,
    duration_days: Optional[float] = None,
    transit_mask: Optional[np.ndarray] = None,
) -> LightCurveData:
    """End-to-end preprocessing pipeline for a LightCurveData object.

    Applies:
    1. Quality bitmask filtering (QUALITY == 0)
    2. Asymmetric MAD flare and outlier rejection (with transit safeguarding)
    3. Iterative Savitzky-Golay detrending with transit masking

    Returns:
        Cleaned, normalized LightCurveData with baseline flux ~ 1.0.
    """
    # 1. Quality mask
    qual_mask = clean_quality(lc.time, lc.flux, lc.flux_err, lc.quality, strict=strict_quality)
    t = lc.time[qual_mask]
    f = lc.flux[qual_mask]
    fe = lc.flux_err[qual_mask]
    q = lc.quality[qual_mask]

    if len(t) == 0:
        return lc.copy_with(time=t, flux=f, flux_err=fe, quality=q)

    # 2. Outlier clip
    if clip_outliers:
        tr_m = transit_mask
        if tr_m is None and period is not None and t0 is not None and duration_days is not None:
            ph = phase_fold(t, period, t0)
            dur_ph = duration_days / period
            tr_m = (np.abs(ph) < dur_ph * 1.5)
        outlier_mask = asymmetric_mad_clip(t, f, fe, window_length=101, transit_mask=tr_m)
        t = t[outlier_mask]
        f = f[outlier_mask]
        fe = fe[outlier_mask]
        q = q[outlier_mask]

    if len(t) == 0:
        return lc.copy_with(time=t, flux=f, flux_err=fe, quality=q)

    # 3. Detrending
    if detrend:
        f_norm, continuum = iterative_savgol_detrend(
            time=t,
            flux=f,
            flux_err=fe,
            window_days=window_days,
            polyorder=polyorder,
            period=period,
            t0=t0,
            duration_days=duration_days,
        )
        fe_norm = fe / continuum
    else:
        f_norm = f
        fe_norm = fe

    meta = dict(lc.metadata)
    meta["preprocessed"] = True
    meta["strict_quality"] = strict_quality
    meta["window_days"] = window_days

    return LightCurveData(
        target_id=lc.target_id,
        mission=lc.mission,
        time=t,
        flux=f_norm,
        flux_err=fe_norm,
        quality=q,
        ra=lc.ra,
        dec=lc.dec,
        metadata=meta,
    )
