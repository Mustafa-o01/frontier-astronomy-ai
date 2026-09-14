"""High-fidelity analytic and deterministic synthetic signal generators.

Generates realistic photometric time-series and transmission spectra for:
1. Disintegrating rocky exoplanets with cometary dust tails, forward-scattering bumps, and variable depth.
2. Standard symmetric planetary transits (Mandel-Agol / trapezoidal null baseline).
3. Exomoon systems with TTVs, TDVs, orthogonal pi/2 phase invariant, and secondary shoulder dips.
4. Co-orbital Trojan worlds at L4/L5 Lagrange points.
5. JWST spectrophotometric transmission spectra with molecular absorption bands and haze slopes.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union
import numpy as np

from frontier_astronomy.core.types import LightCurveData, SpectrumData
from frontier_astronomy.core.constants import DAY_SECONDS, KEPLER_LONG_CADENCE_MIN


def generate_disintegrating_dust_tail_light_curve(
    target_id: str = "SYNTH_KIC1255",
    period: float = 0.6535538,
    t0: float = 120.5683,
    depth: float = 0.010,                # 1.0% mean peak transit depth
    duration_days: float = 60.0,
    cadence_minutes: float = KEPLER_LONG_CADENCE_MIN,
    noise_ppm: float = 250.0,
    tail_scale: float = 0.055,           # lambda_tail in orbital phase units
    asymmetry_alpha: float = 1.0,        # Exponential decay curvature
    ingress_scale: float = 0.005,        # Ingress phase duration
    forward_scat_amp: float = 0.0012,    # Pre-ingress forward scattering peak (1200 ppm)
    forward_scat_lead: float = 0.022,    # Phase lead of forward scattering
    forward_scat_width: float = 0.007,   # Phase width of forward scattering
    depth_var_amp: float = 0.35,         # Orbit-to-orbit depth fractional volatility
    ra: float = 290.966,
    dec: float = 51.505,
    seed: Optional[int] = 42,
) -> LightCurveData:
    """Generate synthetic time-series of a catastrophic disintegrating exoplanet.

    Simulates:
    - Steep ingress occultation by dense dust coma
    - Exponentially decaying egress tail (Rappaport et al. 2012 / Brogi et al. 2012)
    - Mie forward-scattering starlight brightening prior to ingress
    - Stochastic multi-epoch transit depth fluctuations (AR(1) volatility)
    - Realistic Gaussian photometric noise and Kepler-like cadences
    """
    rng = np.random.default_rng(seed)

    cadence_days = cadence_minutes / (24.0 * 60.0)
    time = np.arange(t0 - 2.0, t0 + duration_days, cadence_days, dtype=np.float64)
    n_pts = len(time)

    # Compute orbital phase [-0.5, 0.5) and epoch indices
    phase = ((time - t0) / period + 0.5) % 1.0 - 0.5
    epochs = np.round((time - t0) / period).astype(np.int32)
    unique_epochs = np.unique(epochs)

    # Stochastic depth per epoch (AR(1) process)
    rho_ar = 0.7
    epoch_depth_factor = {}
    z_curr = 0.0
    for ep in unique_epochs:
        z_curr = rho_ar * z_curr + np.sqrt(1.0 - rho_ar ** 2) * rng.normal(0.0, depth_var_amp)
        # Bounded log-normal depth factor
        factor = float(np.exp(np.clip(z_curr, -1.2, 1.2)))
        epoch_depth_factor[ep] = factor

    # Evaluate dust tail model at each cadence
    flux_clean = np.ones(n_pts, dtype=np.float64)

    phi_offset = 0.003  # Centers peak extinction near phase 0
    shifted_phase = phase + phi_offset

    # Ingress sigmoid transition
    s_ing = 1.0 / (1.0 + np.exp(-shifted_phase / ingress_scale))

    # Egress exponential tail decay
    tail_arg = np.maximum(0.0, shifted_phase) / tail_scale
    t_tail = np.exp(-(tail_arg ** asymmetry_alpha))

    # Combined cometary extinction profile
    extinction_base = s_ing * t_tail

    # Forward-scattering pre-ingress bump
    scat_arg = (phase - (-forward_scat_lead)) / forward_scat_width
    scat_bump = forward_scat_amp * np.exp(-0.5 * (scat_arg ** 2))

    # Apply epoch-varying depth
    for ep in unique_epochs:
        in_ep = (epochs == ep)
        ep_depth = depth * epoch_depth_factor[ep]
        flux_clean[in_ep] = 1.0 - ep_depth * extinction_base[in_ep] + scat_bump[in_ep]

    # Add Gaussian white noise
    noise_sigma = noise_ppm * 1e-6
    noise = rng.normal(0.0, noise_sigma, size=n_pts)
    flux_obs = flux_clean + noise
    flux_err = np.full(n_pts, noise_sigma, dtype=np.float64)
    quality = np.zeros(n_pts, dtype=np.int32)

    metadata = {
        "is_synthetic": True,
        "model_type": "disintegrating_dust_tail",
        "period_days": period,
        "t0_days": t0,
        "mean_depth": depth,
        "tail_scale": tail_scale,
        "forward_scat_amp": forward_scat_amp,
        "noise_ppm": noise_ppm,
    }

    return LightCurveData(
        target_id=target_id,
        mission="Kepler",
        time=time,
        flux=flux_obs,
        flux_err=flux_err,
        quality=quality,
        ra=ra,
        dec=dec,
        metadata=metadata,
    )


def generate_symmetric_transit_light_curve(
    target_id: str = "SYNTH_SYMMETRIC",
    mission: str = "Kepler",
    period: float = 3.524,
    t0: float = 100.0,
    depth: float = 0.010,                # 1.0% transit depth
    duration_hours: float = 3.0,
    cadence_minutes: float = KEPLER_LONG_CADENCE_MIN,
    duration_days: float = 60.0,
    noise_ppm: float = 250.0,
    ingress_ratio: float = 0.2,
    ra: float = 290.0,
    dec: float = 40.0,
    seed: Optional[int] = 42,
) -> LightCurveData:
    """Generate synthetic time-series of an ordinary symmetric exoplanet transit."""
    rng = np.random.default_rng(seed)

    cadence_days = cadence_minutes / (24.0 * 60.0)
    time = np.arange(t0 - 2.0, t0 + duration_days, cadence_days, dtype=np.float64)
    n_pts = len(time)

    phase = ((time - t0) / period + 0.5) % 1.0 - 0.5
    dur_phase = (duration_hours / 24.0) / period

    from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit
    transit_model = symmetric_trapezoid_transit(
        phase=phase,
        period=period,
        depth=depth,
        duration_phase=dur_phase,
        ingress_ratio=ingress_ratio,
    )

    noise_sigma = noise_ppm * 1e-6
    flux_obs = transit_model + rng.normal(0.0, noise_sigma, size=n_pts)
    flux_err = np.full(n_pts, noise_sigma, dtype=np.float64)
    quality = np.zeros(n_pts, dtype=np.int32)

    metadata = {
        "is_synthetic": True,
        "model_type": "symmetric_transit",
        "period_days": period,
        "t0_days": t0,
        "depth": depth,
        "duration_hours": duration_hours,
        "noise_ppm": noise_ppm,
    }

    return LightCurveData(
        target_id=target_id,
        mission=mission,
        time=time,
        flux=flux_obs,
        flux_err=flux_err,
        quality=quality,
        ra=ra,
        dec=dec,
        metadata=metadata,
    )


def generate_exomoon_perturbation_light_curve(
    target_id: str = "SYNTH_KEPLER1625B",
    period_planet: float = 287.3789,
    t0_planet: float = 169.825,
    depth_planet: float = 0.012,          # ~1.2% planetary depth
    duration_hours_planet: float = 19.0,
    period_moon: float = 15.0,            # Moon orbital period around planet (days)
    ttv_amp_minutes: float = 65.0,        # ~65 minute TTV oscillation amplitude
    tdv_amp_minutes: float = 25.0,        # ~25 minute TDV variation
    secondary_shoulder_depth: float = 0.0006, # 600 ppm auxiliary dip
    secondary_shoulder_delay_hours: float = 4.2, # Hours post-planet transit
    duration_days: float = 1200.0,        # Multi-year baseline
    cadence_minutes: float = KEPLER_LONG_CADENCE_MIN,
    noise_ppm: float = 150.0,
    ra: float = 295.429,
    dec: float = 39.887,
    seed: Optional[int] = 42,
    period: Optional[float] = None,
    t0: Optional[float] = None,
    has_shoulder: bool = True,
    **kwargs,
) -> LightCurveData:
    """Generate synthetic time-series of an exoplanet harboring a massive exomoon candidate.

    Simulates:
    - Primary planetary transits
    - Transit Timing Variations (TTVs) driven by satellite reflex motion
    - Transit Duration Variations (TDVs) in pi/2 phase quadrature with TTVs
    - Secondary auxiliary transit dip (satellite eclipse of stellar disk)
    """
    if period is not None:
        period_planet = period
    if t0 is not None:
        t0_planet = t0
    rng = np.random.default_rng(seed)

    cadence_days = cadence_minutes / (24.0 * 60.0)
    time = np.arange(t0_planet - 5.0, t0_planet + duration_days, cadence_days, dtype=np.float64)
    n_pts = len(time)

    flux_clean = np.ones(n_pts, dtype=np.float64)

    # Estimate epochs
    epochs = np.round((time - t0_planet) / period_planet).astype(np.int32)
    unique_epochs = np.unique(epochs)

    omega_moon = 2.0 * np.pi / period_moon
    dur_days_planet = duration_hours_planet / 24.0

    from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit

    for ep in unique_epochs:
        # Keplerian linear transit time
        linear_t0 = t0_planet + ep * period_planet

        # Orthogonal TTV and TDV: TTV ~ sin(phi_m), TDV ~ cos(phi_m) (pi/2 invariant)
        moon_phase = ep * (2.0 * np.pi * (period_planet / period_moon))
        ttv_days = (ttv_amp_minutes / 1440.0) * np.sin(moon_phase)
        tdv_days = (tdv_amp_minutes / 1440.0) * np.cos(moon_phase)

        actual_t0 = linear_t0 + ttv_days
        actual_dur_days = max(0.05, dur_days_planet + tdv_days)

        # Cutout window around this transit
        window_mask = np.abs(time - actual_t0) < (actual_dur_days * 1.5)
        if not np.any(window_mask):
            continue

        t_win = time[window_mask]

        # 1. Primary planet transit
        dt_planet = t_win - actual_t0
        phi_planet = dt_planet / period_planet
        dur_phase = actual_dur_days / period_planet
        tr_planet = symmetric_trapezoid_transit(
            phase=phi_planet,
            period=period_planet,
            depth=depth_planet,
            duration_phase=dur_phase,
            ingress_ratio=0.15,
        )

        # 2. Secondary moon transit dip
        t_moon_mid = actual_t0 + (secondary_shoulder_delay_hours / 24.0)
        dt_moon = t_win - t_moon_mid
        phi_moon = dt_moon / period_planet
        dur_moon_phase = (4.5 / 24.0) / period_planet
        tr_moon = symmetric_trapezoid_transit(
            phase=phi_moon,
            period=period_planet,
            depth=secondary_shoulder_depth,
            duration_phase=dur_moon_phase,
            ingress_ratio=0.25,
        )

        # Superposition of planet + moon occultation
        combined_dip = (1.0 - tr_planet) + (1.0 - tr_moon)
        flux_clean[window_mask] = 1.0 - combined_dip

    noise_sigma = noise_ppm * 1e-6
    flux_obs = flux_clean + rng.normal(0.0, noise_sigma, size=n_pts)
    flux_err = np.full(n_pts, noise_sigma, dtype=np.float64)
    quality = np.zeros(n_pts, dtype=np.int32)

    metadata = {
        "is_synthetic": True,
        "model_type": "exomoon_perturbation",
        "period_planet": period_planet,
        "t0_planet": t0_planet,
        "ttv_amp_minutes": ttv_amp_minutes,
        "tdv_amp_minutes": tdv_amp_minutes,
        "secondary_shoulder_depth": secondary_shoulder_depth,
    }

    return LightCurveData(
        target_id=target_id,
        mission="Kepler",
        time=time,
        flux=flux_obs,
        flux_err=flux_err,
        quality=quality,
        ra=ra,
        dec=dec,
        metadata=metadata,
    )


def generate_trojan_light_curve(
    target_id: str = "SYNTH_TROJAN",
    period: float = 12.0,
    t0: float = 50.0,
    depth_planet: float = 0.015,
    duration_hours_planet: float = 4.0,
    trojan_lag_fraction: float = 1.0 / 6.0, # L4 point (+60 deg orbital phase)
    trojan_depth: float = 0.0012,           # 1200 ppm Trojan companion dip
    trojan_duration_hours: float = 2.5,
    duration_days: float = 120.0,
    cadence_minutes: float = KEPLER_LONG_CADENCE_MIN,
    noise_ppm: float = 200.0,
    ra: float = 290.0,
    dec: float = 45.0,
    seed: Optional[int] = 42,
) -> LightCurveData:
    """Generate synthetic time-series of a planet with a co-orbital Trojan companion at L4/L5."""
    rng = np.random.default_rng(seed)

    cadence_days = cadence_minutes / (24.0 * 60.0)
    time = np.arange(t0 - 2.0, t0 + duration_days, cadence_days, dtype=np.float64)
    n_pts = len(time)

    phase_planet = ((time - t0) / period + 0.5) % 1.0 - 0.5
    dur_phase_planet = (duration_hours_planet / 24.0) / period

    from frontier_astronomy.core.math_utils import symmetric_trapezoid_transit
    tr_planet = symmetric_trapezoid_transit(
        phase=phase_planet,
        period=period,
        depth=depth_planet,
        duration_phase=dur_phase_planet,
        ingress_ratio=0.2,
    )

    # Trojan at L4 (+1/6 phase) or L5 (-1/6 phase)
    phase_trojan = ((time - (t0 + trojan_lag_fraction * period)) / period + 0.5) % 1.0 - 0.5
    dur_phase_trojan = (trojan_duration_hours / 24.0) / period
    tr_trojan = symmetric_trapezoid_transit(
        phase=phase_trojan,
        period=period,
        depth=trojan_depth,
        duration_phase=dur_phase_trojan,
        ingress_ratio=0.25,
    )

    flux_clean = 1.0 - ((1.0 - tr_planet) + (1.0 - tr_trojan))

    noise_sigma = noise_ppm * 1e-6
    flux_obs = flux_clean + rng.normal(0.0, noise_sigma, size=n_pts)
    flux_err = np.full(n_pts, noise_sigma, dtype=np.float64)
    quality = np.zeros(n_pts, dtype=np.int32)

    metadata = {
        "is_synthetic": True,
        "model_type": "trojan_co_orbital",
        "period": period,
        "t0": t0,
        "trojan_lag_fraction": trojan_lag_fraction,
        "trojan_depth": trojan_depth,
    }

    return LightCurveData(
        target_id=target_id,
        mission="Kepler",
        time=time,
        flux=flux_obs,
        flux_err=flux_err,
        quality=quality,
        ra=ra,
        dec=dec,
        metadata=metadata,
    )


def generate_jwst_transmission_spectrum(
    target_id: str = "WASP-39b",
    instrument: str = "NIRSpec_PRISM",
    n_channels: int = 100,
    wavelength_min: float = 0.6,
    wavelength_max: float = 5.3,
    baseline_depth: float = 0.0210,        # ~2.10% baseline transit depth (Rp/R*)^2
    log_h2o: float = -3.5,                 # log10(X_H2O)
    log_co2: float = -3.8,                 # log10(X_CO2)
    log_ch4: float = -5.5,                 # log10(X_CH4)
    haze_slope: float = -2.5,              # Rayleigh/Mie optical scattering slope
    noise_level: float = 4.5e-5,           # 45 ppm spectrophotometric uncertainty
    seed: Optional[int] = 42,
) -> SpectrumData:
    """Generate high-fidelity synthetic transmission spectrum matching NASA JWST observations.

    Models:
    - CO2 rovibrational band at 4.3 um (Delta delta ~ 1700 ppm peak)
    - H2O absorption bands at 1.4 um, 1.8 um, 2.7 um
    - CH4 band at 3.3 um
    - Optical haze scattering slope below 1.5 um
    - Realistic wavelength binning and 1-sigma uncertainties
    """
    rng = np.random.default_rng(seed)

    wavelengths = np.linspace(wavelength_min, wavelength_max, n_channels, dtype=np.float64)

    # Base transmission depth
    depth_model = np.full(n_channels, baseline_depth, dtype=np.float64)

    # Scale factor from abundances
    h2o_scale = 10.0 ** (log_h2o + 4.0) * 0.00035
    co2_scale = 10.0 ** (log_co2 + 4.0) * 0.00075
    ch4_scale = 10.0 ** (log_ch4 + 5.0) * 0.00020

    # 1. CO2 4.3 um band and 2.7 um secondary band
    depth_model += co2_scale * np.exp(-0.5 * ((wavelengths - 4.32) / 0.18) ** 2)
    depth_model += 0.35 * co2_scale * np.exp(-0.5 * ((wavelengths - 2.70) / 0.12) ** 2)

    # 2. H2O bands at 1.4, 1.85, 2.75 um
    depth_model += h2o_scale * np.exp(-0.5 * ((wavelengths - 1.40) / 0.10) ** 2)
    depth_model += 1.2 * h2o_scale * np.exp(-0.5 * ((wavelengths - 1.85) / 0.14) ** 2)
    depth_model += 1.5 * h2o_scale * np.exp(-0.5 * ((wavelengths - 2.75) / 0.22) ** 2)

    # 3. CH4 3.3 um band
    depth_model += ch4_scale * np.exp(-0.5 * ((wavelengths - 3.31) / 0.15) ** 2)

    # 4. Rayleigh / Mie haze slope at blue wavelengths (< 1.5 um)
    blue_mask = wavelengths < 1.8
    depth_model[blue_mask] += 0.00025 * ((wavelengths[blue_mask] / 1.0) ** haze_slope)

    # Add observational noise
    unc = np.full(n_channels, noise_level, dtype=np.float64)
    observed_depth = depth_model + rng.normal(0.0, noise_level, size=n_channels)

    return SpectrumData(
        target_id=target_id,
        instrument=instrument,
        wavelength=wavelengths,
        transit_depth=observed_depth,
        uncertainty=unc,
    )


# Function aliases for backward compatibility across dashboard and test suites
generate_exomoon_system_light_curve = generate_exomoon_perturbation_light_curve
generate_synthetic_transmission_spectrum = generate_jwst_transmission_spectrum


def generate_synthetic_light_curve(
    target_id: str = "SYNTH_001",
    transit_type: str = "dust_tail",
    noise_sigma: float = 0.0005,
    period: float = 0.6535,
    t0: float = 120.0,
    duration_days: float = 10.0,
    depth: float = 0.010,
    seed: int = 42,
    **kwargs
) -> LightCurveData:
    """Convenience dispatcher to generate synthetic light curves across transit types."""
    if transit_type in ("flat", "none"):
        return generate_symmetric_transit_light_curve(
            target_id=target_id,
            period=period,
            t0=t0,
            duration_days=duration_days,
            depth=0.0,
            noise_ppm=noise_sigma * 1e6,
            seed=seed,
        )
    elif transit_type == "symmetric":
        return generate_symmetric_transit_light_curve(
            target_id=target_id,
            period=period,
            t0=t0,
            duration_days=duration_days,
            depth=depth,
            noise_ppm=noise_sigma * 1e6,
            seed=seed,
        )
    elif transit_type == "exomoon":
        return generate_exomoon_perturbation_light_curve(
            target_id=target_id,
            period=period,
            t0=t0,
            duration_days=duration_days,
            depth=depth,
            noise_ppm=noise_sigma * 1e6,
            seed=seed,
            **kwargs
        )
    else:  # dust_tail
        return generate_disintegrating_dust_tail_light_curve(
            target_id=target_id,
            period=period,
            t0=t0,
            duration_days=duration_days,
            depth=depth,
            noise_ppm=noise_sigma * 1e6,
            seed=seed,
        )

