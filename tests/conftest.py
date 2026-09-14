"""Shared pytest fixtures, synthetic data generators, and test helpers for Frontier Astronomy AI.

This module provides deterministic, hermetic synthetic astronomical fixtures for:
1. Kepler/TESS time-series photometric light curves (flat, symmetric transit, cometary dust tail,
   multi-body TTV/TDV oscillations, secondary transit shoulders, co-orbital Trojan dips).
2. NASA FITS binary table file mock bytes and disk fixtures.
3. JWST transmission spectrophotometry (WASP-39b NIRSpec PRISM, WASP-96b NIRISS SOSS).
4. Interface contract dataclass factories adhering strictly to PROJECT.md specifications.
"""

from __future__ import annotations

import os
import struct
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

from frontier_astronomy.core.constants import (
    AU,
    BJD_REF_KEPLER,
    BJD_REF_TESS,
    BKJD_TO_BTJD_OFFSET,
    G,
    K_B,
    M_EARTH,
    M_JUPITER,
    M_MOON,
    M_SUN,
    M_U,
    MU_H2_HE,
    R_EARTH,
    R_JUPITER,
    R_MOON,
    R_SUN,
)
from frontier_astronomy.core.types import (
    AtmosphericInversionResult,
    BenchmarkSystem,
    DustTailDetectionResult,
    ExomoonPerturbationResult,
    FoldedTransit,
    LightCurveData,
    SpectrumData,
)


# ==============================================================================
# Deterministic Synthetic Generators
# ==============================================================================

def generate_synthetic_light_curve(
    target_id: str = "SYNTH_001",
    mission: str = "Kepler",
    duration_days: float = 30.0,
    cadence_minutes: float = 29.4244,
    noise_sigma: float = 1e-4,
    seed: int = 42,
    transit_type: str = "flat",
    period: float = 3.5,
    t0: float = 1.2,
    depth: float = 0.01,
    duration_hours: float = 3.0,
    # Dust tail parameters
    sigma_ing: float = 0.005,
    lambda_tail: float = 0.04,
    alpha_tail: float = 1.0,
    f_scat: float = 0.0005,
    phi_scat: float = -0.02,
    sigma_scat: float = 0.008,
    depth_var_sigma: float = 0.2,
    # Exomoon / Perturbation parameters
    ttv_amp_minutes: float = 15.0,
    tdv_amp_minutes: float = 5.0,
    p_moon_days: float = 0.8,
    moon_depth: float = 0.001,
    has_shoulder: bool = False,
    # Trojan parameters
    has_trojan: bool = False,
    trojan_lagrange: str = "L4",
    trojan_depth: float = 0.002,
) -> LightCurveData:
    """Generate a deterministic synthetic photometric time-series.

    Supports flat baseline, symmetric transit, cometary dust tail, exomoon
    perturbations (with orthogonal TTV/TDV), and co-orbital Trojan dips.
    """
    rng = np.random.default_rng(seed)
    n_points = int(duration_days * 1440.0 / cadence_minutes)
    t_start = 120.0 if mission == "Kepler" else 1500.0
    time = np.linspace(t_start, t_start + duration_days, n_points, dtype=np.float64)

    flux = np.ones(n_points, dtype=np.float64)
    flux_err = np.full(n_points, noise_sigma, dtype=np.float64)
    quality = np.zeros(n_points, dtype=np.int32)

    # Gaussian photometric noise
    if noise_sigma > 0:
        flux += rng.normal(0.0, noise_sigma, n_points)

    if transit_type == "flat":
        pass  # Already flat baseline + noise

    elif transit_type == "symmetric":
        # Simple symmetric trapezoid/box transit
        dur_days = duration_hours / 24.0
        phase = ((time - t0) / period) % 1.0
        phase = np.where(phase > 0.5, phase - 1.0, phase)
        half_dur_phase = (dur_days / 2.0) / period

        in_transit = np.abs(phase) < half_dur_phase
        flux[in_transit] -= depth

    elif transit_type == "dust_tail":
        # Rappaport/Brogi cometary extinction profile with forward scattering
        phase = ((time - t0) / period) % 1.0
        phase = np.where(phase > 0.5, phase - 1.0, phase)
        epochs = np.floor((time - t0) / period).astype(int)

        # Multi-epoch stochastic depth
        unique_epochs = np.unique(epochs)
        epoch_depth_mult = {
            ep: float(np.exp(rng.normal(0.0, depth_var_sigma))) for ep in unique_epochs
        }

        for i in range(n_points):
            ph = phase[i]
            ep = epochs[i]
            d_ep = depth * epoch_depth_mult.get(ep, 1.0)

            # Ingress sharp transition with offset so peak aligns with phase=0
            phi_off = 3.0 * sigma_ing
            s_ing = 1.0 / (1.0 + np.exp(-(ph + phi_off) / sigma_ing))
            # Exponential egress tail
            arg = np.maximum(0.0, ph + phi_off) / lambda_tail
            t_tail = np.exp(-(arg ** alpha_tail))

            extinction = d_ep * s_ing * t_tail

            # Forward scattering pre-ingress bump
            scat = f_scat * np.exp(-((ph - phi_scat) ** 2) / (2.0 * (sigma_scat ** 2)))

            flux[i] = flux[i] - extinction + scat

    elif transit_type == "exomoon":
        # Primary planet transit modulated by TTV and TDV with 90 deg phase offset
        dur_days = duration_hours / 24.0
        epochs = np.round((time - t0) / period)
        unique_epochs = np.unique(epochs)

        # Satellite phase angle per epoch: psi_n = 2*pi * (P_b / P_s) * n
        psi = 2.0 * np.pi * (period / p_moon_days) * unique_epochs
        ttv_days = (ttv_amp_minutes / 1440.0) * np.sin(psi)
        # TDV-V is -cos(psi) = sin(psi - pi/2) -> exactly 90 deg out of phase
        tdv_days = (tdv_amp_minutes / 1440.0) * (-np.cos(psi))

        ttv_map = dict(zip(unique_epochs, ttv_days))
        tdv_map = dict(zip(unique_epochs, tdv_days))

        for i in range(n_points):
            ep = epochs[i]
            dt = ttv_map.get(ep, 0.0)
            dur_mod = dur_days + tdv_map.get(ep, 0.0)
            half_dur_p = dur_mod / 2.0

            t_mid = t0 + ep * period + dt
            if np.abs(time[i] - t_mid) < half_dur_p:
                flux[i] -= depth

            # Optional secondary moon transit shoulder
            if has_shoulder:
                # Moon displaced by separation
                t_moon_mid = t_mid + (p_moon_days / 4.0) * np.cos(psi[int(ep % len(psi))])
                if np.abs(time[i] - t_moon_mid) < (dur_days * 0.4):
                    flux[i] -= moon_depth

    elif transit_type == "trojan":
        # Primary transit plus secondary dip at L4 (+60 deg / +0.1667 phase) or L5 (-60 deg)
        dur_days = duration_hours / 24.0
        phase = ((time - t0) / period) % 1.0
        phase = np.where(phase > 0.5, phase - 1.0, phase)
        half_dur_phase = (dur_days / 2.0) / period

        # Primary transit
        in_transit = np.abs(phase) < half_dur_phase
        flux[in_transit] -= depth

        # Trojan dip
        trojan_phase_offset = (1.0 / 6.0) if trojan_lagrange.upper() == "L4" else (-1.0 / 6.0)
        trojan_phase = phase - trojan_phase_offset
        in_trojan = np.abs(trojan_phase) < half_dur_phase
        flux[in_trojan] -= trojan_depth

    return LightCurveData(
        target_id=target_id,
        mission=mission,
        time=time,
        flux=flux,
        flux_err=flux_err,
        quality=quality,
        ra=290.9662,
        dec=51.5047,
        metadata={"period": period, "t0": t0, "transit_type": transit_type},
    )


def generate_synthetic_transmission_spectrum(
    target_id: str = "WASP-39b",
    instrument: str = "NIRSpec_PRISM",
    n_channels: int = 100,
    wl_min: float = 0.6,
    wl_max: float = 5.3,
    log_h2o: float = -3.2,
    log_co2: float = -3.7,
    log_ch4: float = -6.0,
    log_co: float = -3.5,
    t_eq: float = 1120.0,
    log_pc: float = -1.8,
    haze_slope: float = 4.0,
    noise_ppm: float = 50.0,
    seed: int = 101,
) -> SpectrumData:
    """Generate a realistic synthetic JWST transmission spectrum."""
    rng = np.random.default_rng(seed)
    wavelength = np.linspace(wl_min, wl_max, n_channels, dtype=np.float64)

    # Reference baseline transit depth (Rp/R*)^2 ~ 0.0210 (21,000 ppm)
    base_depth = 0.0210

    # Atmospheric scale height parameter ~ 200 ppm = 0.00020
    scale_height = 0.00020 * (t_eq / 1000.0)

    # Molecular absorption profiles
    # H2O features at 0.94, 1.15, 1.4, 1.85, 2.7 um
    h2o_profile = (
        0.5 * np.exp(-((wavelength - 0.94) ** 2) / 0.02)
        + 0.7 * np.exp(-((wavelength - 1.15) ** 2) / 0.03)
        + 1.0 * np.exp(-((wavelength - 1.40) ** 2) / 0.04)
        + 1.2 * np.exp(-((wavelength - 1.85) ** 2) / 0.05)
        + 1.5 * np.exp(-((wavelength - 2.70) ** 2) / 0.08)
    )
    h2o_amp = np.clip(10.0 ** (log_h2o + 4.0), 0.0, 5.0)

    # CO2 prominent 4.3 um peak and secondary 2.7 um
    co2_profile = (
        2.5 * np.exp(-((wavelength - 4.30) ** 2) / 0.06)
        + 0.8 * np.exp(-((wavelength - 2.70) ** 2) / 0.04)
    )
    co2_amp = np.clip(10.0 ** (log_co2 + 4.0), 0.0, 5.0)

    # CH4 bands at 1.65, 2.3, 3.3 um
    ch4_profile = (
        0.6 * np.exp(-((wavelength - 1.65) ** 2) / 0.03)
        + 0.9 * np.exp(-((wavelength - 2.30) ** 2) / 0.04)
        + 1.3 * np.exp(-((wavelength - 3.30) ** 2) / 0.06)
    )
    ch4_amp = np.clip(10.0 ** (log_ch4 + 4.0), 0.0, 5.0)

    # Rayleigh haze slope (blueward rise)
    haze_profile = 0.0003 * ((wavelength / 1.0) ** (-haze_slope * 0.25))

    # Total absorption depth
    absorption = scale_height * (
        h2o_amp * h2o_profile + co2_amp * co2_profile + ch4_amp * ch4_profile
    ) + haze_profile

    # Cloud deck truncation
    # At high cloud pressure (log_pc >= 0.0), clouds are deep below the transmission limb
    # At low cloud pressure (log_pc < -2.5), clouds are high -> flat floor
    if log_pc < -2.5:
        max_absorption = scale_height * max(0.5, 4.0 + log_pc)
        absorption = np.minimum(absorption, max_absorption)

    transit_depth = base_depth + absorption

    # Observational uncertainty and noise
    err_frac = noise_ppm * 1e-6
    uncertainty = np.full(n_channels, err_frac, dtype=np.float64)
    transit_depth += rng.normal(0.0, err_frac, n_channels)

    return SpectrumData(
        target_id=target_id,
        instrument=instrument,
        wavelength=wavelength,
        transit_depth=transit_depth,
        uncertainty=uncertainty,
    )


def generate_mock_fits_bytes(
    n_cadences: int = 50,
    target_name: str = "KIC 12557548",
    kepler_id: int = 12557548,
    mission: str = "Kepler",
    bad_quality_count: int = 5,
) -> bytes:
    """Generate byte-exact synthetic NASA FITS file bytes with a binary table extension."""
    def pad_card(c: str) -> str:
        return c[:80].ljust(80)

    # Primary Header (2880 bytes padded)
    p_cards = [
        pad_card("SIMPLE  =                    T / conforms to FITS standard"),
        pad_card("BITPIX  =                    8 / array data type"),
        pad_card("NAXIS   =                    0 / number of array dimensions"),
        pad_card("EXTEND  =                    T / FITS dataset may contain extensions"),
        pad_card("TELESCOP= 'Kepler  '           / telescope"),
        pad_card(f"OBJECT  = '{target_name:<18}' / object name"),
        pad_card(f"KEPLERID=             {kepler_id:<8} / unique Kepler target identifier"),
        pad_card("RA_OBJ  =           290.966220 / right ascension"),
        pad_card("DEC_OBJ =            51.504720 / declination"),
        pad_card("END"),
    ]
    p_header_str = "".join(p_cards)
    p_header_padded = p_header_str.ljust((len(p_header_str) + 2879) // 2880 * 2880)
    primary_bytes = p_header_padded.encode("ascii")

    # Extension Binary Table: 4 columns
    # Col 1: TIME (1D, >f8, 8 bytes)
    # Col 2: SAP_FLUX (1E, >f4, 4 bytes)
    # Col 3: PDCSAP_FLUX (1E, >f4, 4 bytes)
    # Col 4: QUALITY (1J, >i4, 4 bytes)
    row_bytes = 8 + 4 + 4 + 4  # 20 bytes per row
    table_data_size = n_cadences * row_bytes

    b_cards = [
        pad_card("XTENSION= 'BINTABLE'           / binary table extension"),
        pad_card("BITPIX  =                    8 / 8-bit bytes"),
        pad_card("NAXIS   =                    2 / 2-dimensional binary table"),
        pad_card(f"NAXIS1  =                   {row_bytes} / width of table in bytes"),
        pad_card(f"NAXIS2  =                 {n_cadences} / number of rows in table"),
        pad_card("PCOUNT  =                    0 / size of special data area"),
        pad_card("GCOUNT  =                    1 / one data group"),
        pad_card("TFIELDS =                    4 / number of fields in each row"),
        pad_card("TTYPE1  = 'TIME    '           / column title: TIME"),
        pad_card("TFORM1  = '1D      '           / data format of field: 8-byte DOUBLE"),
        pad_card("TTYPE2  = 'SAP_FLUX'           / column title: SAP_FLUX"),
        pad_card("TFORM2  = '1E      '           / data format of field: 4-byte REAL"),
        pad_card("TTYPE3  = 'PDCSAP_FLUX'        / column title: PDCSAP_FLUX"),
        pad_card("TFORM3  = '1E      '           / data format of field: 4-byte REAL"),
        pad_card("TTYPE4  = 'QUALITY '           / column title: QUALITY"),
        pad_card("TFORM4  = '1J      '           / data format of field: 4-byte INTEGER"),
        pad_card("EXTNAME = 'LIGHTCURVE'         / name of this binary table extension"),
        pad_card("END"),
    ]
    b_header_str = "".join(b_cards)
    b_header_padded = b_header_str.ljust((len(b_header_str) + 2879) // 2880 * 2880)
    ext_header_bytes = b_header_padded.encode("ascii")

    # Table data buffer (big-endian)
    data_buffer = bytearray()
    t_start = 120.0
    for i in range(n_cadences):
        t_val = t_start + i * (29.4244 / 1440.0)
        sap_val = 1000.0 + (i % 5)
        pdcsap_val = 1.000 + 0.001 * np.sin(i * 0.1)
        # inject bad quality on designated cadences
        qual_val = 128 if i < bad_quality_count else 0

        # Big-endian packing: >d (8 bytes), >f (4 bytes), >f (4 bytes), >i (4 bytes)
        row = struct.pack(">dffi", t_val, sap_val, pdcsap_val, qual_val)
        data_buffer.extend(row)

    # Pad data to multiple of 2880 bytes
    table_padded_len = (len(data_buffer) + 2879) // 2880 * 2880
    data_padded = bytes(data_buffer).ljust(table_padded_len, b"\x00")

    return primary_bytes + ext_header_bytes + data_padded


# ==============================================================================
# Pytest Fixtures
# ==============================================================================

@pytest.fixture
def flat_light_curve() -> LightCurveData:
    """Fixture providing a flat photometric light curve."""
    return generate_synthetic_light_curve(transit_type="flat", noise_sigma=1e-4)


@pytest.fixture
def symmetric_transit_light_curve() -> LightCurveData:
    """Fixture providing a symmetric planetary transit light curve."""
    return generate_synthetic_light_curve(
        transit_type="symmetric", period=3.5, t0=1.2, depth=0.01, duration_hours=3.0
    )


@pytest.fixture
def dust_tail_light_curve() -> LightCurveData:
    """Fixture providing a cometary dust tail light curve with forward scattering."""
    return generate_synthetic_light_curve(
        transit_type="dust_tail",
        period=0.65355,
        t0=120.568,
        depth=0.008,
        sigma_ing=0.004,
        lambda_tail=0.05,
        f_scat=0.001,
        depth_var_sigma=0.3,
    )


@pytest.fixture
def exomoon_light_curve() -> LightCurveData:
    """Fixture providing an exomoon-perturbed transit light curve with orthogonal TTV/TDV."""
    return generate_synthetic_light_curve(
        transit_type="exomoon",
        period=10.0,
        t0=125.0,
        depth=0.015,
        ttv_amp_minutes=20.0,
        tdv_amp_minutes=6.0,
        p_moon_days=1.2,
        has_shoulder=True,
    )


@pytest.fixture
def trojan_light_curve() -> LightCurveData:
    """Fixture providing a co-orbital Trojan companion light curve."""
    return generate_synthetic_light_curve(
        transit_type="trojan",
        period=8.0,
        t0=130.0,
        depth=0.02,
        trojan_lagrange="L4",
        trojan_depth=0.003,
    )


@pytest.fixture
def wasp39b_spectrum() -> SpectrumData:
    """Fixture providing synthetic WASP-39b NIRSpec PRISM transmission spectrum."""
    return generate_synthetic_transmission_spectrum(
        target_id="WASP-39b",
        instrument="NIRSpec_PRISM",
        log_h2o=-3.20,
        log_co2=-3.70,
        log_ch4=-6.50,
        log_co=-3.30,
        t_eq=1120.0,
        log_pc=-1.8,
    )


@pytest.fixture
def wasp96b_spectrum() -> SpectrumData:
    """Fixture providing synthetic WASP-96b NIRISS transmission spectrum."""
    return generate_synthetic_transmission_spectrum(
        target_id="WASP-96b",
        instrument="NIRISS_SOSS",
        log_h2o=-3.50,
        log_co2=-5.0,
        log_ch4=-6.0,
        log_co=-4.0,
        t_eq=1280.0,
        log_pc=-1.5,
    )


@pytest.fixture
def mock_fits_bytes() -> bytes:
    """Fixture providing raw binary bytes of a valid Kepler FITS light curve."""
    return generate_mock_fits_bytes(n_cadences=100, bad_quality_count=10)


@pytest.fixture
def temp_fits_file(tmp_path) -> str:
    """Fixture providing an on-disk temporary FITS file."""
    fpath = tmp_path / "test_kepler_lc.fits"
    content = generate_mock_fits_bytes(n_cadences=80, bad_quality_count=8)
    fpath.write_bytes(content)
    return str(fpath)


@pytest.fixture
def sample_folded_transit() -> FoldedTransit:
    """Fixture providing a folded transit dataclass instance."""
    n = 200
    phase = np.linspace(-0.5, 0.5, n, endpoint=False, dtype=np.float64)
    flux = np.ones(n, dtype=np.float64)
    in_transit = np.abs(phase) < 0.05
    flux[in_transit] -= 0.01
    flux_err = np.full(n, 0.0001, dtype=np.float64)
    epoch_indices = np.zeros(n, dtype=np.int32)
    return FoldedTransit(
        phase=phase,
        flux=flux,
        flux_err=flux_err,
        epoch_indices=epoch_indices,
        period=3.5,
        t0=120.0,
    )


@pytest.fixture
def sample_dust_tail_result(dust_tail_light_curve: LightCurveData) -> DustTailDetectionResult:
    """Fixture providing a dynamically computed DustTailDetectionResult instance.

    Invokes genuine production detection pipeline on authentic cometary dust tail light curve.
    """
    from frontier_astronomy.dust_tail.detector import detect_dust_tail
    period = float(dust_tail_light_curve.metadata.get("period", 0.65355))
    t0 = float(dust_tail_light_curve.metadata.get("t0", 120.568))
    return detect_dust_tail(dust_tail_light_curve, period=period, t0=t0)


@pytest.fixture
def sample_perturbation_result(exomoon_light_curve: LightCurveData) -> ExomoonPerturbationResult:
    """Fixture providing a dynamically computed ExomoonPerturbationResult instance.

    Invokes genuine production photodynamic perturbation detector on authentic exomoon light curve.
    """
    from frontier_astronomy.perturbations import detect_perturbations
    period = float(exomoon_light_curve.metadata.get("period", 10.0))
    t0 = float(exomoon_light_curve.metadata.get("t0", 125.0))
    return detect_perturbations(exomoon_light_curve, period=period, t0=t0)


@pytest.fixture
def sample_inversion_result(wasp39b_spectrum: SpectrumData) -> AtmosphericInversionResult:
    """Fixture providing a dynamically computed AtmosphericInversionResult instance.

    Invokes genuine production atmospheric inversion engine on authentic WASP-39b transmission spectrum.
    """
    from frontier_astronomy.atmospheric.inversion import invert_spectrum
    return invert_spectrum(wasp39b_spectrum, n_samples=1500, seed=42)
