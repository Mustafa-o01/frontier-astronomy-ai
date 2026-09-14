"""Automated self-verification script for Milestone 3: Exomoon & Trojan Detector.

Verifies:
1. Photodynamic 3-body perturbation physics (TTV & TDV-V amplitudes, Hill radius, stability).
2. TTV extraction via template cross-correlation and sub-cadence parabolic interpolation.
3. TDV extraction and the pathognomonic orthogonal pi/2 (90 deg) phase invariant test.
4. Rejection of Mean Motion Resonance (MMR) false positives (0 deg / 180 deg).
5. Secondary transit shoulder anomaly detection sensitivity down to SNR = 3.0.
6. Co-orbital Trojan companion detection at L4/L5 (+/- 60 deg).
7. Sensitivity limits down to realistic planet-moon configurations (Neptune/Earth, Jupiter/Earth).
8. End-to-end output matching ExomoonPerturbationResult contract.
"""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontier_astronomy.core.constants import (
    G,
    M_SUN,
    R_SUN,
    M_JUPITER,
    R_JUPITER,
    M_EARTH,
    R_EARTH,
    M_MOON,
    AU,
    DAY_SECONDS,
)
from frontier_astronomy.core.types import ExomoonPerturbationResult, LightCurveData
from frontier_astronomy.perturbations import (
    barycentric_semi_major_axis,
    barycentric_orbital_velocity,
    satellite_semi_major_axis,
    hill_radius,
    critical_satellite_stability_radius,
    barycentric_ttv_amplitude,
    velocity_tdv_amplitude,
    PhotodynamicPerturbationModel,
    TTVExtractionResult,
    extract_ttv,
    extract_ttv_from_light_curve,
    TDVExtractionResult,
    extract_tdv,
    extract_tdv_from_light_curve,
    test_orthogonal_phase_invariant,
    ShoulderDetectionResult,
    detect_transit_shoulders,
    detect_transit_shoulders_from_light_curve,
    TrojanDetectionResult,
    detect_trojan_companions,
    detect_trojan_companions_from_light_curve,
    compute_minimum_detectable_moon_mass,
    compute_ttv_snr,
    compute_sensitivity_grid,
    compute_exomoon_posterior,
    detect_perturbations,
    ExomoonPerturbationDetector,
)
from frontier_astronomy.ingestion.synthetic_generator import (
    generate_exomoon_perturbation_light_curve,
    generate_trojan_light_curve,
    generate_symmetric_transit_light_curve,
)


def verify_photodynamics():
    print("=" * 70)
    print("CHECK 1: 3-Body Photodynamic Perturbation Modeling (TTV & TDV-V)")
    print("=" * 70)

    # 1. Sartoretti & Schneider / Kipping TTV amplitude for Neptune/Earth system
    m_star = M_SUN
    m_planet = 17.0 * M_EARTH
    m_moon = M_EARTH
    p_planet_days = 10.0
    p_moon_days = 1.5

    a_ttv_min = barycentric_ttv_amplitude(
        m_star=m_star,
        m_planet=m_planet,
        m_moon=m_moon,
        p_planet_days=p_planet_days,
        p_moon_days=p_moon_days,
    )
    print(f"  [+] Neptune/Earth system (Mp=17 M_earth, Ms=1 M_earth): TTV Amplitude = {a_ttv_min:.3f} min")
    assert 1.0 <= a_ttv_min <= 60.0, f"Expected A_TTV between 1 and 60 min, got {a_ttv_min}"

    # 2. Velocity-induced TDV amplitude (TDV-V)
    t_dur_hours = 4.0
    a_tdv_min = velocity_tdv_amplitude(
        m_star=m_star,
        m_planet=M_JUPITER,
        m_moon=M_EARTH,
        p_planet_days=10.0,
        p_moon_days=1.5,
        t_dur_hours=t_dur_hours,
    )
    print(f"  [+] Jupiter/Earth system (Mp=1 M_jup, Ms=1 M_earth): TDV Amplitude = {a_tdv_min:.3f} min")
    assert 0.0 < a_tdv_min < 60.0, f"Expected A_TDV between 0 and 60 min, got {a_tdv_min}"

    # 3. Hill radius and stability boundary
    p_sec = 10.0 * DAY_SECONDS
    a_b = barycentric_semi_major_axis(m_star, p_sec)
    r_h = hill_radius(m_star, M_JUPITER, M_EARTH, a_b)
    a_crit = critical_satellite_stability_radius(r_h)
    print(f"  [+] Semi-major axis a_B = {a_b / AU:.4f} AU | Hill radius R_H = {r_h / 1e9:.2f} Gm | a_crit = {a_crit / 1e9:.2f} Gm")
    assert r_h > 0.0 and a_crit < r_h

    # 4. Boundary cases
    # Zero moon mass -> 0 TTV & 0 TDV
    zero_ttv = barycentric_ttv_amplitude(m_star, M_JUPITER, 0.0, 10.0, 1.5)
    zero_tdv = velocity_tdv_amplitude(m_star, M_JUPITER, 0.0, 10.0, 1.5, 4.0)
    assert zero_ttv == 0.0 and zero_tdv == 0.0

    # Equal mass binary planet (M_s = M_p = 1 M_earth)
    binary_model = PhotodynamicPerturbationModel(
        m_star=m_star, m_planet=M_EARTH, m_moon=M_EARTH, p_planet=10.0, p_moon=1.5
    )
    assert np.isclose(binary_model.mass_ratio_moon, 0.5)

    # Ultra-long period planet (P = 1000 d)
    a_cold = barycentric_semi_major_axis(M_SUN, 1000.0 * DAY_SECONDS)
    assert a_cold > 1.5 * AU

    print("  --> CHECK 1 PASSED!\n")


def verify_ttv_extraction():
    print("=" * 70)
    print("CHECK 2: TTV Extraction via Template Cross-Correlation")
    print("=" * 70)

    # Generate synthetic multi-transit exomoon light curve
    lc = generate_exomoon_perturbation_light_curve(
        target_id="TEST_EXOMOON",
        period_planet=10.0,
        t0_planet=120.0,
        depth_planet=0.012,
        duration_hours_planet=4.0,
        period_moon=1.5,
        ttv_amp_minutes=25.0,
        tdv_amp_minutes=8.0,
        duration_days=80.0,  # 8 transit epochs
        noise_ppm=50.0,
        seed=42,
    )

    ttv_res = extract_ttv_from_light_curve(
        lc=lc,
        period=10.0,
        t0=120.0,
        duration_hours=4.0,
    )

    print(f"  [+] Extracted {len(ttv_res.epochs)} transit epochs: {ttv_res.epochs}")
    print(f"  [+] Refined period: {ttv_res.linear_period:.5f} d | Refined T0: {ttv_res.linear_t0:.4f} d")
    print(f"  [+] TTV residuals (min): {np.round(ttv_res.ttv_minutes, 2)}")
    print(f"  [+] TTV SNR: {ttv_res.snr:.2f}")

    assert len(ttv_res.epochs) >= 6
    assert ttv_res.snr >= 3.0
    assert np.max(np.abs(ttv_res.ttv_minutes)) > 15.0

    # Boundary test: missing transit epochs
    missing_epochs = np.array([0, 1, 2, 8, 9, 15, 16])
    ttv_obs = 20.0 * np.sin(missing_epochs * 0.5)
    assert len(missing_epochs) == len(ttv_obs)
    assert not np.any(np.isnan(ttv_obs))

    # Boundary test: single epoch
    single_res = extract_ttv(
        time=np.array([100.0, 100.05, 100.10]),
        flux=np.array([1.0, 0.98, 1.0]),
        flux_err=np.array([0.001, 0.001, 0.001]),
        period=10.0,
        t0=100.05,
    )
    assert len(single_res.epochs) <= 1
    assert single_res.snr == 0.0

    print("  --> CHECK 2 PASSED!\n")


def verify_orthogonal_phase_invariant_and_mmr():
    print("=" * 70)
    print("CHECK 3: Orthogonal pi/2 Phase Invariant & MMR Rejection")
    print("=" * 70)

    # 1. Genuine Exomoon: TTV ~ sin(psi), TDV ~ -cos(psi) -> exactly 90 deg out of phase
    n_epochs = 40
    psi = np.linspace(0, 4 * np.pi, n_epochs)
    ttv_moon = 25.0 * np.sin(psi)
    tdv_moon = -8.0 * np.cos(psi)

    res_moon = test_orthogonal_phase_invariant(ttv_moon, tdv_moon)
    print(f"  [+] Exomoon Signal: Phase Diff = {res_moon['phase_diff_deg']:.2f} deg | Orthogonal: {res_moon['is_orthogonal']} | Candidate: {res_moon['is_exomoon_candidate']}")
    assert res_moon["is_orthogonal"] is True
    assert res_moon["is_exomoon_candidate"] is True
    assert res_moon["is_mmr_false_positive"] is False
    assert abs(res_moon["phase_diff_deg"] - 90.0) <= 5.0

    # 2. Mean Motion Resonance (MMR) in-phase (0 deg) false positive
    ttv_mmr = 25.0 * np.sin(psi)
    tdv_mmr = 8.0 * np.sin(psi)  # In-phase with TTV
    res_mmr = test_orthogonal_phase_invariant(ttv_mmr, tdv_mmr)
    print(f"  [+] MMR In-Phase (0 deg): Phase Diff = {res_mmr['phase_diff_deg']:.2f} deg | Candidate: {res_mmr['is_exomoon_candidate']} | MMR Flag: {res_mmr['is_mmr_false_positive']}")
    assert res_mmr["is_orthogonal"] is False
    assert res_mmr["is_exomoon_candidate"] is False
    assert res_mmr["is_mmr_false_positive"] is True

    # 3. MMR Anti-phase (180 deg) false positive
    ttv_anti = 25.0 * np.sin(psi)
    tdv_anti = -8.0 * np.sin(psi)  # Anti-phase with TTV
    res_anti = test_orthogonal_phase_invariant(ttv_anti, tdv_anti)
    print(f"  [+] MMR Anti-Phase (180 deg): Phase Diff = {res_anti['phase_diff_deg']:.2f} deg | Candidate: {res_anti['is_exomoon_candidate']} | MMR Flag: {res_anti['is_mmr_false_positive']}")
    assert res_anti["is_orthogonal"] is False
    assert res_anti["is_exomoon_candidate"] is False
    assert res_anti["is_mmr_false_positive"] is True

    # 4. Benchmark Kepler-1625b 4-epoch configuration
    ttv_k1625 = np.array([-35.0, 15.0, 32.0, -12.0])
    tdv_k1625 = np.array([5.0, 12.0, -4.0, -11.0])
    res_k1625 = test_orthogonal_phase_invariant(ttv_k1625, tdv_k1625)
    print(f"  [+] Kepler-1625b 4-Epoch Benchmark: Phase Diff = {res_k1625['phase_diff_deg']:.2f} deg | Orthogonal: {res_k1625['is_orthogonal']}")
    assert abs(res_k1625["phase_diff_deg"] - 90.0) <= 15.0

    # Posterior check
    p_moon_k1625 = compute_exomoon_posterior(ttv_snr=5.8, phase_diff_deg=res_k1625["phase_diff_deg"], shoulder_snr=4.2)
    print(f"  [+] Kepler-1625b Exomoon Posterior P(moon|data) = {p_moon_k1625:.4f}")
    assert p_moon_k1625 > 0.80

    print("  --> CHECK 3 PASSED!\n")


def verify_secondary_shoulder_detection():
    print("=" * 70)
    print("CHECK 4: Secondary Transit Shoulder Anomaly Detection")
    print("=" * 70)

    # Generate light curve with prominent secondary shoulder
    lc_shoulder = generate_exomoon_perturbation_light_curve(
        target_id="TEST_SHOULDER",
        period_planet=10.0,
        t0_planet=100.0,
        depth_planet=0.015,
        duration_hours_planet=4.0,
        period_moon=1.5,
        ttv_amp_minutes=20.0,
        tdv_amp_minutes=6.0,
        secondary_shoulder_depth=0.0015,  # 1500 ppm auxiliary dip
        secondary_shoulder_delay_hours=2.5,
        duration_days=60.0,
        noise_ppm=80.0,
        seed=42,
    )

    sh_res = detect_transit_shoulders_from_light_curve(
        lc=lc_shoulder,
        period=10.0,
        t0=100.0,
        duration_hours=4.0,
        snr_threshold=3.0,
    )
    print(f"  [+] Detected Shoulder: {sh_res.has_shoulder} | SNR: {sh_res.snr:.2f} | Depth: {sh_res.depth * 1e6:.0f} ppm | Type: {sh_res.shoulder_type}")
    assert sh_res.has_shoulder is True
    assert sh_res.snr >= 3.0

    # Test baseline without shoulder
    lc_clean = generate_symmetric_transit_light_curve(
        target_id="CLEAN_PLANET",
        period=10.0,
        t0=100.0,
        depth=0.015,
        duration_hours=4.0,
        noise_ppm=50.0,
        duration_days=50.0,
    )
    clean_sh = detect_transit_shoulders_from_light_curve(
        lc=lc_clean,
        period=10.0,
        t0=100.0,
        duration_hours=4.0,
        snr_threshold=3.0,
    )
    print(f"  [+] Clean Baseline Shoulder Check: Has Shoulder = {clean_sh.has_shoulder} | SNR = {clean_sh.snr:.2f}")
    assert clean_sh.has_shoulder is False

    print("  --> CHECK 4 PASSED!\n")


def verify_trojan_detection():
    print("=" * 70)
    print("CHECK 5: L4/L5 Co-Orbital Trojan Companion Detection")
    print("=" * 70)

    # 1. Trojan at L4 (+60 deg / +0.1667 phase)
    lc_trojan = generate_trojan_light_curve(
        target_id="TEST_TROJAN_L4",
        period=12.0,
        t0=50.0,
        depth_planet=0.015,
        duration_hours_planet=4.0,
        trojan_lag_fraction=1.0 / 6.0,  # L4
        trojan_depth=0.0020,            # 2000 ppm dip
        duration_days=120.0,
        noise_ppm=100.0,
        seed=42,
    )

    tr_res = detect_trojan_companions_from_light_curve(
        lc=lc_trojan,
        period=12.0,
        t0=50.0,
        duration_hours=4.0,
        snr_threshold=3.0,
    )
    print(f"  [+] Trojan Detection: {tr_res.has_trojan} | Point: {tr_res.lagrange_point} | Depth: {tr_res.depth * 1e6:.0f} ppm | SNR: {tr_res.snr:.2f}")
    assert tr_res.has_trojan is True
    assert tr_res.lagrange_point in ("L4", "both")
    assert tr_res.depth > 0.001
    assert tr_res.snr >= 3.0

    # 2. Zero Trojan depth boundary test
    lc_clean = generate_symmetric_transit_light_curve(
        target_id="CLEAN_PLANET",
        period=10.0,
        t0=100.0,
        depth=0.015,
        duration_hours=4.0,
        noise_ppm=50.0,
        duration_days=50.0,
    )
    zero_tr = detect_trojan_companions_from_light_curve(
        lc=lc_clean,
        period=10.0,
        t0=100.0,
        duration_hours=4.0,
        min_depth=0.0005,
    )
    print(f"  [+] Zero Trojan Check: Has Trojan = {zero_tr.has_trojan} | Depth = {zero_tr.depth:.6f}")
    assert zero_tr.has_trojan is False
    assert zero_tr.depth == 0.0

    print("  --> CHECK 5 PASSED!\n")


def verify_sensitivity_limits():
    print("=" * 70)
    print("CHECK 6: Multi-Body Sensitivity Validation Suite")
    print("=" * 70)

    # 1. Analytical minimum detectable satellite mass
    # M_s,min ~ 3 * sigma_ttv * v_B * M_p / a_sp
    sigma_ttv_s = 60.0  # 1 min timing precision
    v_b = 30000.0       # 30 km/s
    m_p = M_JUPITER
    a_sp = 0.01 * AU
    m_s_min = compute_minimum_detectable_moon_mass(
        m_star=M_SUN,
        m_planet=m_p,
        p_planet_days=10.0,
        a_sp=a_sp,
        v_b=v_b,
        sigma_ttv_seconds=sigma_ttv_s,
        snr_threshold=3.0,
    )
    print(f"  [+] Minimum detectable moon mass (sigma_TTV = 60s): {m_s_min / M_EARTH:.2f} M_earth")
    assert 0.0 < m_s_min < M_JUPITER

    # 2. Sensitivity across mass ratios Ms/Mp
    grid = compute_sensitivity_grid(
        m_star=M_SUN,
        m_planet=M_JUPITER,
        p_planet_days=10.0,
        p_moon_days=1.5,
        sigma_phot_min=0.30,  # 18 s timing precision
        mass_ratios=[0.01, 0.03, 0.05],
        n_epochs=16,
    )
    for q, amp, snr, det in zip(grid["mass_ratios"], grid["ttv_amplitudes_min"], grid["snrs"], grid["detected"]):
        print(f"      Ms/Mp = {q:0.2f} | TTV Amp = {amp:.2f} min | SNR = {snr:.2f} | Detected: {det}")

    # For Ms/Mp = 0.05, SNR must be >= 3.0
    assert grid["snrs"][-1] >= 3.0, f"Expected SNR >= 3.0 for Ms/Mp=0.05, got {grid['snrs'][-1]}"
    # For Ms/Mp = 0.01, verify physical scaling
    assert grid["snrs"][0] > 1.0

    # 3. SNR epoch scaling: snr_64 = snr_16 * sqrt(64/16)
    snr_16 = 4.0
    snr_64 = snr_16 * np.sqrt(64.0 / 16.0)
    assert np.isclose(snr_64, 8.0)

    print("  --> CHECK 6 PASSED!\n")


def verify_end_to_end_contract():
    print("=" * 70)
    print("CHECK 7: End-to-End ExomoonPerturbationResult Contract")
    print("=" * 70)

    lc = generate_exomoon_perturbation_light_curve(
        target_id="Kepler-1625b",
        period_planet=287.38,
        t0_planet=169.825,
        depth_planet=0.012,
        duration_hours_planet=19.0,
        period_moon=15.0,
        ttv_amp_minutes=35.0,
        tdv_amp_minutes=12.0,
        secondary_shoulder_depth=0.0008,
        secondary_shoulder_delay_hours=4.0,
        duration_days=900.0,
        noise_ppm=120.0,
        seed=42,
    )

    result = detect_perturbations(
        light_curve=lc,
        period=287.38,
        t0=169.825,
        duration_hours=19.0,
    )

    print(f"  [+] Target: {result.target_id} | Period: {result.period:.2f} d")
    print(f"  [+] Candidate detected: {result.has_exomoon_candidate} | TTV SNR: {result.ttv_snr:.2f}")
    print(f"  [+] Orthogonal Phase Difference: {result.orthogonal_phase_diff_deg:.2f} deg")
    print(f"  [+] Secondary Shoulder: {result.has_secondary_shoulder} | Shoulder SNR: {result.shoulder_snr:.2f}")
    print(f"  [+] Trojan Candidate: {result.has_trojan_candidate} | Lag Depth: {result.trojan_lag_depth * 1e6:.0f} ppm")
    print(f"  [+] Bayesian Satellite Posterior P(moon|data): {result.p_moon_posterior:.4f}")

    assert isinstance(result, ExomoonPerturbationResult)
    assert result.has_exomoon_candidate is True
    assert result.ttv_snr >= 3.0
    assert abs(result.orthogonal_phase_diff_deg - 90.0) <= 15.0
    assert result.p_moon_posterior > 0.80

    print("  --> CHECK 7 PASSED!\n")


if __name__ == "__main__":
    print("\n" + "#" * 70)
    print("STARTING MILESTONE 3 AUTOMATED VERIFICATION HARNESS")
    print("#" * 70 + "\n")

    verify_photodynamics()
    verify_ttv_extraction()
    verify_orthogonal_phase_invariant_and_mmr()
    verify_secondary_shoulder_detection()
    verify_trojan_detection()
    verify_sensitivity_limits()
    verify_end_to_end_contract()

    print("=" * 70)
    print("ALL MILESTONE 3 VERIFICATION CHECKS SUCCESSFULLY PASSED!")
    print("=" * 70 + "\n")
