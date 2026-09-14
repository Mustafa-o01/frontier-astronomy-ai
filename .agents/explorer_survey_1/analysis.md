# Scientific Models, Physics Formulations, and Detection Mathematics
## Frontier Astronomy AI Discovery Suite — Exploration Report
**Author:** `explorer_survey_1` (Scientific Models Explorer)  
**Date:** 2026-09-14  
**Project Root:** `G:\frontier_astronomy_ai`  

---

## Executive Summary

This report establishes the rigorous mathematical formulations, astrophysical mechanisms, and statistical detection criteria underpinning the three core discovery pillars of the **Frontier Astronomy AI Discovery Suite**:
1. **Catastrophic Disintegrating Exoplanet & Exocomet Dust Tail Hunter**: Analytical cometary extinction profiles, Mie forward-scattering brightening, stochastic sublimation dynamics, and $\Delta\text{BIC}$ asymmetric transit hypothesis testing.
2. **Exomoon & Trojan World Gravitational Perturbation Detector**: Photodynamic three-body perturbation theory, Transit Timing Variations (TTV) & Transit Duration Variations (TDV), the pathognomonic $\pi/2$ orthogonal TTV-TDV phase signature, $L_4/L_5$ Trojan co-orbital secondary dips, and Gaussian Process stellar noise decoupling.
3. **Rapid Atmospheric Chemistry Inversion for NASA JWST Transmission Spectra**: Analytical and numerical transmission spectroscopy radiative transfer ($H = k_B T / \mu g$, molecular opacities $\text{H}_2\text{O}, \text{CO}_2, \text{CH}_4, \text{CO}$, collision-induced absorption, cloud decks, and haze slopes), coupled with PyTorch-native Neural Posterior Estimation (NPE) via Conditional Normalizing Flows for sub-second ($< 0.1\text{ s}$) Bayesian retrieval reproducing benchmark solutions within $1\sigma$.

All formulations are engineered to execute using available libraries (`numpy`, `scipy`, `torch`, `pandas`, `sklearn`, `matplotlib`), requiring zero external compiled C-extensions (such as `batman`), guaranteeing 100% portability, speed, and numerical stability.

---

## 1. Catastrophic Disintegrating Exoplanet & Exocomet Dust Tail Hunter

### 1.1 Astrophysical Mechanism & Phenomenology
Ultra-short-period (USP) rocky exoplanets ($P < 1\text{ d}$, $a \lesssim 0.015\text{ AU}$) orbiting close to their host stars endure stellar irradiances exceeding $10^5\text{ W/m}^2$, driving surface equilibrium temperatures:
$$T_{\rm eq} = T_* \left(\frac{R_*}{2a}\right)^{1/2} \approx 1800 - 2200\text{ K}$$
At these extreme temperatures, rock-forming minerals (primarily enstatite $\text{MgSiO}_3$, forsterite $\text{Mg}_2\text{SiO}_4$, and quartz $\text{SiO}_2$) evaporate directly from the molten magma ocean into a mineral vapor atmosphere with saturation vapor pressures $P_{\rm vap} \sim 10 - 100\text{ Pa}$.

Because the planetary body has low surface gravity ($M_p \lesssim 0.05\,M_\oplus$), the thermal scale height of the vapor exceeds the planetary radius, launching a transonic hydrodynamic Parker wind (Perez-Becker & Chiang 2013). As the gas expands into vacuum and cools adiabatically, mineral vapor nucleates into sub-micron dust grains ($a_{\rm grain} \sim 0.1 - 1\,\mu\text{m}$).

Once released into the interplanetary medium outside the planet's Hill sphere ($R_H = a [M_p / (3 M_*)]^{1/3}$), dust grains experience two competing forces:
1. **Stellar Gravity**: $F_{\rm grav} = \frac{G M_* m_{\rm grain}}{r^2}$
2. **Radiation Pressure**: $F_{\rm rad} = \frac{L_* \pi a_{\rm grain}^2 Q_{\rm pr}}{4 \pi r^2 c}$

The ratio of radiation pressure to gravity is the dimensionless parameter $\beta$:
$$\beta \equiv \frac{F_{\rm rad}}{F_{\rm grav}} = \frac{3 L_* Q_{\rm pr}}{16 \pi G M_* c \rho_{\rm grain} a_{\rm grain}}$$
For typical silicate grains ($\rho_{\rm grain} \approx 3.0\text{ g/cm}^3$, $a_{\rm grain} \approx 0.2 - 0.5\,\mu\text{m}$, $Q_{\rm pr} \approx 1.0$) around solar-type or K-dwarf stars, $\beta \sim 0.02 - 0.10$.

#### Dust Orbital Dynamics & Lag:
The dust particle experiences an effective stellar mass $M_{\rm eff} = M_*(1 - \beta) < M_*$. At the moment of ejection from the planet's orbit (radius $a_p$, orbital velocity $v_p = \sqrt{G M_* / a_p}$), the dust grain enters a Keplerian orbit with:
$$a_{\rm dust} = \frac{a_p}{1 - 2\beta} > a_p, \qquad e_{\rm dust} = \frac{\beta}{1 - \beta}$$
$$P_{\rm dust} = P_p (1 - \beta)^{-3/2} > P_p$$
Because $P_{\rm dust} > P_p$, the dust grains have a lower mean orbital angular velocity than the planet ($\Omega_{\rm dust} < \Omega_p$). Consequently, **the dust grains stream behind the planet along its orbit, generating an extended trailing cometary dust tail**.

### 1.2 Mathematical Formulation of the Extinction Profile
The observed normalized flux $F(\phi)$ as a function of orbital phase $\phi \in [-0.5, 0.5]$ (where $\phi = (t - T_0)/P \pmod 1$) is given by:
$$F(\phi) = 1.0 - \Delta F_{\rm ext}(\phi) + F_{\rm scat}(\phi)$$

#### A. Ingress and Trailing Dust Cloud Extinction $\Delta F_{\rm ext}(\phi)$
Following the empirical and analytical dust dispersion frameworks of Rappaport et al. (2012, 2014), Brogi et al. (2012), and Sanchis-Ojeda et al. (2015):
- The leading edge of the dust cloud (at phase $\Delta\phi = \phi - \phi_0$) is sharply bounded near the planet core due to the rapid nucleation boundary and stellar limb geometry.
- The trailing tail decays exponentially in optical depth as dust grains disperse in orbital longitude and undergo thermal sublimation.

We formulate the continuous dust extinction profile as:
$$\Delta F_{\rm ext}(\Delta\phi) = \delta \cdot \mathcal{S}_{\rm ing}(\Delta\phi; \sigma_{\rm ing}) \cdot \mathcal{T}_{\rm tail}(\Delta\phi; \lambda_{\rm tail}, \alpha)$$

1. **Sharp Ingress Transition Function (Sigmoidal / Error Function formulation)**:
   $$\mathcal{S}_{\rm ing}(\Delta\phi; \sigma_{\rm ing}) = \frac{1}{1 + \exp\left( -\frac{\Delta\phi + \phi_{\rm offset}}{\sigma_{\rm ing}} \right)}$$
   where $\sigma_{\rm ing}$ represents the ingress phase duration (governed by the planet/coma transit chord time across the stellar limb, typically $\sigma_{\rm ing} \sim 0.002 - 0.008$ in phase).
2. **Trailing Exponential Decay Function**:
   $$\mathcal{T}_{\rm tail}(\Delta\phi; \lambda_{\rm tail}, \alpha) = \exp\left( - \left[ \frac{\max(0, \Delta\phi + \phi_{\rm offset})}{\lambda_{\rm tail}} \right]^\alpha \right)$$
   where:
   - $\lambda_{\rm tail}$: the characteristic extinction scale length along the orbit ($\lambda_{\rm tail} \approx 0.02 - 0.15$ in phase units).
   - $\alpha$: the shape asymmetry parameter. For pure steady-state diffusion/dispersion, $\alpha = 1.0$ (exponential decay). For rapid sublimation cutoff, $\alpha > 1.0$. For power-law turbulent spreading, $\alpha < 1.0$.
   - $\phi_{\rm offset}$: alignment offset aligning peak extinction with transit center $\Delta\phi = 0$.

#### B. Forward-Scattering Brightening Prior to Ingress $F_{\rm scat}(\phi)$
Because dust grains have size parameters $x = 2\pi a_{\rm grain} / \lambda_{\rm obs} \sim 1 - 5$, Mie scattering is intensely peaked in the forward direction. The Henyey-Greenstein scattering phase function is:
$$p(\theta_{\rm scat}) = \frac{1 - g^2}{4\pi (1 + g^2 - 2g \cos \theta_{\rm scat})^{3/2}}$$
where $g = \langle \cos\theta_{\rm scat} \rangle \approx 0.7 - 0.85$ is the scattering asymmetry parameter.

As the dust cloud approaches primary transit, the scattering angle $\theta_{\rm scat}$ (angle between star-dust vector and observer vector) approaches $0$ (direct forward scattering). Starlight is scattered into the observer's line of sight **before** the dust cloud occults the stellar disk. This produces a characteristic **pre-ingress flux brightening** ($F > 1.0$):
$$F_{\rm scat}(\Delta\phi) = f_{\rm scat} \cdot \exp\left( -\frac{(\Delta\phi - \phi_{\rm scat})^2}{2 \sigma_{\rm scat}^2} \right)$$
where:
- $f_{\rm scat}$: forward scattering peak amplitude ($f_{\rm scat} \approx 0.0002 - 0.0020$, or $200 - 2000\text{ ppm}$).
- $\phi_{\rm scat}$: phase lead of the forward scattering peak ($\phi_{\rm scat} \approx -0.015$ to $-0.035$, occurring immediately prior to ingress).
- $\sigma_{\rm scat}$: width of the forward scattering peak ($\sigma_{\rm scat} \approx 0.005 - 0.012$).

### 1.3 Grain Sublimation Dynamics & Epoch-to-Epoch Depth Variability
Dust grains exposed to stellar radiation reach a thermal sublimation temperature $T_{\rm dust} \sim 1800 - 2100\text{ K}$.
The rate of decrease of grain radius $a_{\rm grain}$ is governed by the Langmuir evaporation equation:
$$\frac{da_{\rm grain}}{dt} = - \frac{\alpha_{\rm sub} P_{\rm vap}(T_{\rm dust})}{\rho_{\rm grain}} \sqrt{\frac{\mu_{\rm grain} m_u}{2\pi k_B T_{\rm dust}}}$$
Integrating over time yields the grain sublimation lifetime:
$$\tau_{\rm sub} = \frac{a_{\rm grain, 0}}{|da_{\rm grain}/dt|} \sim 2 - 15\text{ hours}$$
Because $\tau_{\rm sub}$ is on the same order as the orbital period $P \sim 9 - 22\text{ hours}$, dust grains sublimate completely within one orbit. **This explains why the tail terminates cleanly rather than wrapping continuously around the host star.**

#### Variable-Depth Multi-Epoch Stochastic Model:
Mass loss from the evaporating core is non-steady, driven by episodic volcanic magma outgassing or convective overturn. The transit depth at epoch $k$ ($k \in \{1, \dots, K\}$) is modeled as:
$$\delta_k = \bar{\delta} \cdot \exp(z_k)$$
where $z_k$ follows a continuous first-order autoregressive process $\text{AR}(1)$ with correlation parameter $\rho_{\rm AR}$ and volatility $\sigma_z$:
$$z_k = \rho_{\rm AR} z_{k-1} + \sqrt{1 - \rho_{\rm AR}^2} \, \epsilon_k, \quad \epsilon_k \sim \mathcal{N}(0, \sigma_z^2)$$
For KIC 12557548 b, observed depths vary from $<0.15\%$ (quiescent phase) up to $1.3\%$ (eruption phase) on timescales of weeks to months ($\sigma_z \approx 0.6 - 0.9$).

### 1.4 Parameterization & Model Summary

| Parameter | Symbol | Typical Range | Physical Meaning |
|---|---|---|---|
| Orbital Period | $P$ | $0.2 - 2.5\text{ days}$ | Planetary orbital period |
| Transit Epoch | $T_0$ | BJD | Center of primary transit |
| Peak Extinction Depth | $\delta$ | $500 - 15000\text{ ppm}$ | Maximum flux extinction |
| Ingress Transition Scale | $\sigma_{\rm ing}$ | $0.002 - 0.010$ (phase) | Sharpness of leading edge |
| Tail Scale Length | $\lambda_{\rm tail}$ | $0.02 - 0.15$ (phase) | Exponential tail length |
| Tail Asymmetry Power | $\alpha$ | $0.6 - 1.8$ | Tail shape curvature |
| Forward Scattering Amplitude | $f_{\rm scat}$ | $0 - 2500\text{ ppm}$ | Pre-ingress Mie scattering peak |
| Forward Scattering Offset | $\phi_{\rm scat}$ | $-0.040 - -0.010$ (phase) | Phase of forward scattering peak |
| Scattering Width | $\sigma_{\rm scat}$ | $0.004 - 0.015$ (phase) | Angular width of scattering peak |
| Quadratic Limb Darkening | $u_1, u_2$ | $0.1 - 0.6$ | Stellar disk intensity profile |

### 1.5 Statistical Detection Criteria & Hypothesis Testing
To distinguish an evaporating dust-tail transit from a standard symmetric exoplanetary transit, we perform formal statistical hypothesis testing:

#### Null Hypothesis $\mathcal{H}_0$ (Symmetric Transit):
Standard symmetric transit model $\mathcal{M}_{\rm sym}(\theta_{\rm sym})$ (Mandel-Agol quadratic limb-darkened model or symmetric trapezoid), with parameters $\theta_{\rm sym} = \{T_0, P, \delta, T_{\rm dur}, \tau_{\rm ing}, u_1, u_2\}$ ($k_{\rm sym} = 5$ free parameters when limb darkening is fixed).

#### Alternative Hypothesis $\mathcal{H}_1$ (Asymmetric Dust Tail):
Asymmetric dust tail model $\mathcal{M}_{\rm tail}(\theta_{\rm tail})$ with parameters $\theta_{\rm tail} = \{T_0, P, \delta, \sigma_{\rm ing}, \lambda_{\rm tail}, \alpha, f_{\rm scat}, \phi_{\rm scat}, \sigma_{\rm scat}\}$ ($k_{\rm tail} = 8$ free parameters).

#### 1. Bayesian Information Criterion (BIC):
$${\rm BIC} = k \ln N - 2 \ln \mathcal{L}_{\rm max} = k \ln N + \sum_{i=1}^N \left(\frac{F_i - F_{\rm model}(t_i)}{\sigma_i}\right)^2$$
$$\Delta {\rm BIC} = {\rm BIC}_{\rm sym} - {\rm BIC}_{\rm tail}$$
- **$\Delta {\rm BIC} < 2$**: Weak / inconclusive evidence.
- **$2 \le \Delta {\rm BIC} < 6$**: Positive evidence favoring dust tail.
- **$6 \le \Delta {\rm BIC} < 10$**: Strong evidence.
- **$\Delta {\rm BIC} \ge 10$**: Decisive statistical detection of dust tail morphology (Kass & Raftery 1995).

#### 2. Likelihood Ratio Test (LRT):
$$\Lambda = -2 \ln \left( \frac{\mathcal{L}_{\rm sym}}{\mathcal{L}_{\rm tail}} \right) = \chi^2_{\rm sym} - \chi^2_{\rm tail}$$
Under the null hypothesis, $\Lambda$ follows a $\chi^2(\Delta k)$ distribution with $\Delta k = k_{\rm tail} - k_{\rm sym} = 3$ degrees of freedom. The $p$-value is:
$$p = 1 - F_{\chi^2}(\Lambda; \Delta k)$$
A detection requires $p < 10^{-5}$ ($> 4.4\sigma$).

#### 3. Morphological Transit Asymmetry Scores:
- **Duration Asymmetry Ratio**:
  $$A_{\rm dur} = \frac{t_{\rm recov} - t_{\rm min}}{t_{\rm min} - t_{\rm start}} \ge 2.5$$
- **Slope Asymmetry Ratio**:
  $$S_{\rm slope} = \frac{\left| (dF/dt)_{\rm ingress} \right|}{\left| (dF/dt)_{\rm egress} \right|} \ge 3.0$$
- **Pre-Ingress Flux Excess Significance**:
  $$Z_{\rm scat} = \frac{F_{\rm max,pre} - 1.0}{\sigma_{\rm baseline} / \sqrt{N_{\rm pre}}} \ge 3.5$$
- **Depth Variability Metric across Epochs**:
  $$\chi^2_{\rm depth} = \sum_{k=1}^K \frac{(\delta_k - \bar{\delta})^2}{\sigma_{\delta_k}^2}, \quad p(\chi^2_{\rm depth}; K-1) < 10^{-4}$$

---

## 2. Exomoon & Trojan World Gravitational Perturbation Detector

### 2.1 Physics of Exomoon Orbital Dynamics
Consider a host star of mass $M_*$, orbited by a planet of mass $M_p$, which in turn is orbited by an exomoon of mass $M_s$.
The planet-moon barycenter $B$ follows a Keplerian heliocentric orbit with semi-major axis $a_B$, orbital period $P_B$, and orbital velocity $v_B = \sqrt{G M_* / a_B}$.

The moon orbits the planet-moon barycenter with semi-major axis $a_s$, while the planet orbits the barycenter with semi-major axis $a_p$:
$$a_p = a_{sp} \left( \frac{M_s}{M_p + M_s} \right), \qquad a_s = a_{sp} \left( \frac{M_p}{M_p + M_s} \right)$$
where $a_{sp} = a_p + a_s$ is the planet-moon separation.
The satellite orbital period $P_s$ is given by Kepler's third law:
$$P_s = 2\pi \sqrt{\frac{a_{sp}^3}{G (M_p + M_s)}}$$
The maximum stable orbital separation for a prograde moon is constrained by the planet's Hill sphere (Domingos et al. 2006):
$$R_H = a_B \left( \frac{M_p + M_s}{3 M_*} \right)^{1/3}, \qquad a_{sp} \le a_{\rm crit} \approx 0.36 R_H$$

### 2.2 Transit Timing Variations (TTV) Formulation
During primary transit, the observer measures the transit midpoint of the planet. Because the planet orbits the moving barycenter $B$, its position along the transit chord is displaced by:
$$\vec{r}_p(t) = - a_p \left[ \cos(\Omega_s t + \phi_s) \hat{x} + \sin(\Omega_s t + \phi_s) \hat{y} \right]$$
The physical displacement along the tangential velocity vector $\vec{v}_B = v_B \hat{x}$ translates into a time shift (Sartoretti & Schneider 1999; Kipping 2009a):
$$\delta t_{\rm TTV}(n) = \frac{a_p}{v_B} \sin\left( \varpi_s + n \cdot 2\pi \frac{P_B}{P_s} + \phi_s \right)$$

The peak TTV amplitude is:
$$A_{\rm TTV} = \frac{a_p}{v_B} = \frac{a_{sp}}{a_B} \frac{P_B}{2\pi} \left( \frac{M_s}{M_p + M_s} \right) = \frac{1}{2\pi} \left(\frac{G}{M_*^2}\right)^{1/3} P_B^{1/3} P_s^{2/3} \frac{M_s}{(M_p + M_s)^{1/3}}$$

### 2.3 Transit Duration Variations (TDV) Formulation
Kipping (2009b) proved that an exomoon induces two distinct duration variation effects:

#### 1. Velocity-induced Transit Duration Variation (TDV-V):
The planet's total velocity relative to the star at transit is the vector sum:
$$\vec{v}_p(t) = \vec{v}_B + \vec{v}_{p/B}(t)$$
where $v_{p/B} = \frac{2\pi a_p}{P_s} = \frac{2\pi a_{sp}}{P_s} \left( \frac{M_s}{M_p + M_s} \right)$.
The transit duration depends inversely on the planet's chord crossing velocity:
$$T_{\rm dur}(n) \approx \frac{2 \sqrt{R_*^2 - b^2 R_*^2}}{v_B + v_{p/B} \cos\left( \varpi_s + n \cdot 2\pi \frac{P_B}{P_s} + \phi_s \right)}$$
Expanding to first order in $v_{p/B} / v_B \ll 1$:
$$\delta T_{\rm TDV-V}(n) = - \bar{T}_{\rm dur} \left( \frac{v_{p/B}}{v_B} \right) \cos\left( \varpi_s + n \cdot 2\pi \frac{P_B}{P_s} + \phi_s \right)$$
The peak TDV-V amplitude is:
$$A_{\rm TDV-V} = \bar{T}_{\rm dur} \left( \frac{a_{sp}}{a_B} \right) \left( \frac{P_B}{P_s} \right) \left( \frac{M_s}{M_p + M_s} \right)$$

#### 2. Transit Impact Parameter TDV (TDV-TIP):
If the moon's orbital plane is inclined by $i_s$ relative to the planet's heliocentric orbit, the z-coordinate (impact parameter $b$) is modulated:
$$b(n) = b_B + \frac{a_p}{R_*} \cos i_s \sin(\Omega_s t_n + \phi_s)$$
which contributes an additional duration perturbation depending on $b_B$.

### 2.4 The Pathognomonic $\pi/2$ ($90^\circ$) Orthogonal Phase Invariant
Notice the fundamental mathematical relationship between TTV and TDV-V:
$$\delta t_{\rm TTV}(n) \propto \sin\left( \Psi_n \right)$$
$$\delta T_{\rm TDV-V}(n) \propto - \cos\left( \Psi_n \right) = \sin\left( \Psi_n - \frac{\pi}{2} \right)$$
$$\implies \Phi_{\rm TTV} - \Phi_{\rm TDV} \equiv \frac{\pi}{2} = 90^\circ$$

**Astrophysical Implication:**
In planet-planet gravitational perturbations (e.g. mean motion resonances), TTVs and TDVs are strictly **in-phase ($0^\circ$) or anti-phase ($180^\circ$)** because the planet is accelerated along its orbital track without an orthogonal velocity component.
An **exact $90^\circ$ phase offset between TTV and TDV is the unequivocal, definitive smoking gun signature of an exomoon.**

Furthermore, taking the ratio of the two measured amplitudes yields the moon's orbital period directly:
$$\frac{A_{\rm TTV}}{A_{\rm TDV-V}} = \frac{P_s}{2\pi \bar{T}_{\rm dur}}$$

### 2.5 Secondary Photometric Transit Anomalies & Mutual Events
If the exomoon transits the stellar disk alongside the planet, the combined flux drop is:
$$F(t) = 1.0 - \Delta F_p(\vec{r}_p(t)) - \Delta F_s(\vec{r}_s(t)) + \Delta F_{\rm mutual}(t)$$
1. **Transit Shoulders**:
   - Leading moon ($x_s < x_p$): Shallow initial ingress dip prior to primary planet ingress ("ingress shoulder").
   - Trailing moon ($x_s > x_p$): Shallow lingering egress dip after primary planet egress ("egress shoulder").
   - Moon transit depth: $\delta_s = (R_s / R_*)^2 = \delta_p (R_s / R_p)^2$.
2. **Mutual Occultation Events**:
   When the moon eclipses the planet or vice-versa while both are transiting the stellar disk, the projected dark area is reduced:
   $$\Delta F_{\rm mutual}(t) = \frac{\text{Area}(\mathcal{D}_p \cap \mathcal{D}_s)}{\pi R_*^2} > 0$$
   producing a distinctive upward flux spike in the transit bottom.

### 2.6 Co-Orbital Trojan Worlds ($L_4 / L_5$)
In the circular restricted three-body problem, the triangular Lagrangian points $L_4$ and $L_5$ are located at $60^\circ$ ahead and behind the primary planet in its orbit:
$$\phi_{L_4} = \phi_p + \frac{1}{6} \approx \phi_p + 0.1667$$
$$\phi_{L_5} = \phi_p - \frac{1}{6} \approx \phi_p - 0.1667$$
Trojan planets librate on stable tadpole orbits around $L_4$ or $L_5$ with libration amplitudes up to $\Delta\phi \sim \pm 20^\circ$.

#### Photometric Signature of Trojans:
- Secondary transit dips occurring at exact phase offsets $\Delta\phi = \pm 1/6$ ($\pm 60^\circ$).
- Transit duration matching the primary planet: $T_{\rm dur, Trojan} \approx T_{\rm dur, p}$.
- Depth: $\delta_{\rm Trojan} = (R_{\rm Trojan} / R_*)^2$.

### 2.7 Multi-Body Photodynamic Perturbation Algorithms & Signal Decoupling
Stellar magnetic activity, starspots, and granulation create correlated low-frequency noise that can mimic or obscure low-amplitude TTV/TDV signals. We decouple stellar variability using Gaussian Process (GP) regression:
$$y(t) = F_{\rm photodynamic}(t; \theta) + f_{\rm GP}(t) + \epsilon(t)$$
with covariance kernel $k(\tau) = k_{\rm Mat\acute{e}rn-3/2}(\tau)$ or $k_{\rm SHO}(\tau)$:
$$k_{\rm M32}(\tau) = \sigma_{\rm GP}^2 \left( 1 + \frac{\sqrt{3}\tau}{\rho} \right) \exp\left( -\frac{\sqrt{3}\tau}{\rho} \right)$$
where $\sigma_{\rm GP}$ is the stellar variability amplitude and $\rho$ is the correlation timescale ($> 3 \times T_{\rm dur}$).

#### Signal-to-Noise Ratio (SNR) Sensitivity Thresholds:
For phase-folded transits across $N_{\rm tr}$ epochs:
$${\rm SNR}_{\rm moon} = \frac{\delta_s}{\sigma_{\rm phot}} \sqrt{N_{\rm tr} \cdot \frac{T_{\rm dur}}{\Delta t_{\rm cad}}}$$
- **Jupiter / Earth system**: $M_p = 318\,M_\oplus$, $M_s = 1\,M_\oplus$, $\delta_s \approx 84\text{ ppm}$. In Kepler data ($\sigma_{\rm phot} \approx 30\text{ ppm}$, $N_{\rm tr} = 16$, $T_{\rm dur} = 10\text{ h}$), ${\rm SNR} \approx 45$ (easily detectable).
- **Neptune / Earth system**: $M_p = 17\,M_\oplus$, $M_s = 1\,M_\oplus$, $A_{\rm TTV} \sim 15 - 40\text{ minutes}$! TTV is massive and detectable even if the moon does not transit!
- Minimum detectable moon mass via TTV:
  $$M_{s, \min} \approx 3 \sigma_{\rm TTV} \cdot \frac{v_B (M_p)}{a_{sp}}$$

---

## 3. Rapid Atmospheric Chemistry Inversion for NASA JWST Transmission Spectra

### 3.1 Physics of Transmission Spectroscopy
During primary transit, stellar light traverses the annular limb of the exoplanet's atmosphere. The wavelength-dependent transit depth is:
$$\mathcal{D}(\lambda) \equiv \left( \frac{R_p(\lambda)}{R_*} \right)^2 = \frac{R_0^2 + 2 \int_{R_0}^{R_{\rm top}} r [1 - e^{-\tau(r, \lambda)}] \, dr}{R_*^2}$$
where $R_0$ is the reference base radius at pressure $P_0 = 10\text{ bar}$.

#### Atmospheric Scale Height:
The vertical density structure follows hydrostatic equilibrium with scale height:
$$H = \frac{k_B T_{\rm eq}}{\mu g} = \frac{k_B T_{\rm eq} R_0^2}{\mu G M_p}$$
where:
- $k_B$: Boltzmann constant ($1.380649 \times 10^{-23}\text{ J/K}$)
- $T_{\rm eq}$: Atmospheric equilibrium temperature ($400 - 2500\text{ K}$)
- $\mu$: Mean molecular weight ($\approx 2.3\text{ amu}$ for $\text{H}_2/\text{He}$ dominated gas giants, up to $18-44\text{ amu}$ for secondary water/$\text{CO}_2$ atmospheres)
- $g$: Surface gravity ($G M_p / R_0^2$)

#### Effective Transit Radius Formula (Lecavelier des Etangs et al. 2008; de Wit & Seager 2013):
In an isothermal atmosphere with uniform mixing ratios, the effective transit radius is:
$$R_p(\lambda) = R_0 + H \left[ \gamma + \ln\left( \frac{P_0 \kappa(\lambda, T)}{\mu g} \sqrt{\frac{2\pi R_0}{H}} \right) \right]$$
where $\gamma \approx 0.577215$ is the Euler-Mascheroni constant, and $\kappa(\lambda, T)$ is the extinction cross-section per unit mass ($\text{cm}^2/\text{g}$).
The transit depth is therefore:
$$\mathcal{D}(\lambda) \approx \frac{R_0^2}{R_*^2} + \frac{2 R_0 H}{R_*^2} \left[ \gamma + \ln\left( \frac{P_0 \kappa(\lambda, T)}{\mu g} \sqrt{\frac{2\pi R_0}{H}} \right) \right]$$
The characteristic spectral feature amplitude per atmospheric scale height is:
$$\Delta \mathcal{D}_{\rm scale} = \frac{2 R_0 H}{R_*^2} \approx 150 - 300\text{ ppm}$$

### 3.2 Atmospheric Opacity Formulation
The total extinction cross section $\sigma_{\rm tot}(\lambda, P, T)$ is composed of four distinct components:
$$\sigma_{\rm tot}(\lambda, P, T) = \sum_{i} \chi_i \sigma_i(\lambda, P, T) + \sigma_{\rm CIA}(\lambda, T) + \sigma_{\rm haze}(\lambda) + \sigma_{\rm cloud}(\lambda, P)$$

#### 1. Molecular Absorption:
For volume mixing ratios (VMR) $\chi_i = n_i / n_{\rm tot}$, the key molecular species in the JWST NIRSpec/NIRISS bandpass ($0.6 - 5.3\,\mu\text{m}$) are:
- **$\text{H}_2\text{O}$**: Strong absorption bands at $0.94\,\mu\text{m}, 1.15\,\mu\text{m}, 1.4\,\mu\text{m}, 1.85\,\mu\text{m}, 2.7\,\mu\text{m}$.
- **$\text{CO}_2$**: Prominent signature doublet at $4.3\,\mu\text{m}$ (the benchmark WASP-39b discovery feature) and $2.7\,\mu\text{m}$.
- **$\text{CH}_4$**: Fundamental $\nu_3$ and $\nu_4$ bands at $1.65\,\mu\text{m}, 2.3\,\mu\text{m}, 3.3\,\mu\text{m}$.
- **$\text{CO}$**: Characteristic bandhead at $2.35\,\mu\text{m}$ and fundamental band at $4.67\,\mu\text{m}$.
- **$\text{NH}_3$**: Inversion and stretching features at $1.5\,\mu\text{m}, 2.0\,\mu\text{m}, 3.0\,\mu\text{m}$.
- **$\text{SO}_2$**: Photochemical feature at $4.05\,\mu\text{m}$.

#### 2. Collision-Induced Absorption (CIA):
Pairs of $\text{H}_2-\text{H}_2$ and $\text{H}_2-\text{He}$ molecules interacting during collisions create an infrared absorption floor scaling as $P^2$:
$$\kappa_{\rm CIA}(\lambda, T, P) = \left[ \chi_{\text{H}_2}^2 \alpha_{\text{H}_2-\text{H}_2}(\lambda, T) + \chi_{\text{H}_2}\chi_{\text{He}} \alpha_{\text{H}_2-\text{He}}(\lambda, T) \right] \left(\frac{P}{k_B T}\right)^2 \frac{1}{\rho}$$

#### 3. Rayleigh Scattering & Photochemical Hazes:
$$\sigma_{\rm haze}(\lambda) = a_{\rm haze} \cdot \sigma_0 \left( \frac{\lambda}{\lambda_0} \right)^{-\gamma_{\rm haze}}$$
where:
- $\sigma_0 = 5.31 \times 10^{-27}\text{ cm}^2$ at $\lambda_0 = 0.35\,\mu\text{m}$.
- $a_{\rm haze}$: Haze enhancement factor relative to molecular hydrogen ($1 - 10^4$).
- $\gamma_{\rm haze}$: Haze spectral scattering index ($\gamma = 4$ for pure Rayleigh, $\gamma < 4$ for grey/large particle hazes, $\gamma > 4$ for photochemical tholins).

#### 4. Grey Cloud Deck:
An opaque cloud deck is parameterized by its cloud-top pressure $P_c$:
$$\tau_{\rm cloud}(P) = \begin{cases} 0, & P < P_c \\ \infty, & P \ge P_c \end{cases}$$
For pressures greater than $P_c$, transmission is blocked, truncating the absorption line wings and creating a flat continuum floor at large wavelengths.

### 3.3 Amortized Bayesian Parameter Estimation (NPE) Architecture
Traditional Bayesian retrieval uses Markov Chain Monte Carlo (MCMC) or Nested Sampling (e.g. MultiNest, dynesty), requiring $10^5 - 10^6$ forward radiative transfer calculations taking $6 - 48\text{ hours}$ per spectrum.

We adopt **Neural Posterior Estimation (NPE)** (Greenberg et al. 2019; Cranmer et al. 2020), which trains an invertible neural density estimator to approximate the true posterior $p(\theta | x)$ across the entire prior parameter space, enabling **sub-second inference ($< 0.1\text{ s}$)**.

#### Atmospheric Parameter Space $\theta \in \mathbb{R}^7$:
$$\theta = \begin{bmatrix} \log_{10} \chi_{\text{H}_2\text{O}} \\ \log_{10} \chi_{\text{CO}_2} \\ \log_{10} \chi_{\text{CH}_4} \\ \log_{10} \chi_{\text{CO}} \\ T_{\rm eq} \\ \log_{10} P_c \\ \log_{10} a_{\rm haze} \end{bmatrix}, \quad
\begin{aligned}
\log_{10} \chi_i &\sim \mathcal{U}(-12.0, -1.0) \\
T_{\rm eq} &\sim \mathcal{U}(400, 2500)\text{ K} \\
\log_{10} P_c &\sim \mathcal{U}(-5.0, 2.0)\text{ bar} \\
\log_{10} a_{\rm haze} &\sim \mathcal{U}(-2.0, 4.0)
\end{aligned}$$

#### Flow Architecture (Conditional RealNVP / Rational Quadratic Spline Flow):
Let $x \in \mathbb{R}^M$ be the observed transmission spectrum (e.g. $M = 100$ wavelength bins across $0.6 - 5.3\,\mu\text{m}$).
We define an invertible bijective mapping $f_\phi(\cdot; x): \mathbb{R}^D \to \mathbb{R}^D$ that maps a base standard normal variable $u \sim \mathcal{N}(0, \mathbf{I})$ to the parameter space $\theta$:
$$\theta = f_\phi(u; x), \qquad u = f_\phi^{-1}(\theta; x)$$
Using affine coupling layers (RealNVP):
For input $u = [u_{1:d}, u_{d+1:D}]$:
$$v_{1:d} = u_{1:d}$$
$$v_{d+1:D} = u_{d+1:D} \odot \exp(s_\phi(u_{1:d}; x)) + t_\phi(u_{1:d}; x)$$
where $s_\phi$ (scale) and $t_\phi$ (translation) are multi-layer perceptrons (MLP) conditioned on the spectrum embedding $e(x) = \text{MLP}(x)$.

By the change-of-variables theorem, the conditional posterior density is evaluated analytically:
$$q_\phi(\theta | x) = p_u(f_\phi^{-1}(\theta; x)) \cdot \left| \det \left( \frac{\partial f_\phi^{-1}}{\partial \theta} \right) \right|$$
The Jacobian determinant is triangular and computed in $\mathcal{O}(D)$ time:
$$\ln \left| \det \left( \frac{\partial f_\phi^{-1}}{\partial \theta} \right) \right| = - \sum_{j=d+1}^D s_\phi(u_{1:d}; x)_j$$

#### Training Objective:
The network parameters $\phi$ are trained by minimizing the negative log-likelihood on simulated pairs $\{(\theta^{(j)}, x^{(j)})\}_{j=1}^N$:
$$\mathcal{L}(\phi) = - \frac{1}{N} \sum_{j=1}^N \ln q_\phi(\theta^{(j)} | x^{(j)})$$
This unconditionally minimizes the Kullback-Leibler divergence $D_{\rm KL}(p(\theta|x) \,||\, q_\phi(\theta|x))$ averaged over the data distribution.

#### Sub-Second Inference Protocol:
1. Pass observed JWST spectrum $x_{\rm obs}$ into trained network $q_\phi(\theta | x_{\rm obs})$.
2. Sample $S = 5000$ latent vectors $u^{(s)} \sim \mathcal{N}(0, \mathbf{I})$.
3. Compute posterior samples $\theta^{(s)} = f_\phi(u^{(s)}; x_{\rm obs})$ via single vectorized GPU/CPU forward pass (**execution time: $< 30\text{ milliseconds}$**).
4. Compute marginal posteriors:
   - Median (50th percentile)
   - $1\sigma$ credible interval: $[15.865\%, 84.135\%]$
   - $2\sigma$ credible interval: $[2.275\%, 97.725\%]$
   - Instantaneous corner plot covariance contours.

### 3.4 Benchmark Validation Against Published NASA JWST Retrievals

#### 1. WASP-39b (JWST Transiting Exoplanet Community 2023; Rustamkulov et al. 2023; Alderson et al. 2023):
- Planetary System: $M_p = 0.281\,M_J$, $R_p = 1.27\,R_J$, $T_{\rm eq} \approx 1120\text{ K}$, $R_* = 0.932\,R_\odot$.
- Ground Truth Published Retrievals:
  - $\log_{10} \chi_{\text{CO}_2} = -3.70 \pm 0.35$ (clear $> 20\sigma$ detection at $4.3\,\mu\text{m}$)
  - $\log_{10} \chi_{\text{H}_2\text{O}} = -3.20 \pm 0.40$ (multi-band detection)
  - $\log_{10} \chi_{\text{CH}_4} < -5.5$ (depleted / non-detection)
  - $\log_{10} \chi_{\text{CO}} \approx -3.1 \pm 0.6$
  - Cloud deck pressure $\log_{10} P_c \approx -1.8 \pm 0.7\text{ bar}$.
- **Acceptance Criterion**: Our NPE model must reproduce the published medians within their respective $1\sigma$ credible intervals, yielding tight constraints on $\text{CO}_2$ and $\text{H}_2\text{O}$ while correctly inferring an unconstrained upper limit for $\text{CH}_4$.

#### 2. WASP-96b (JWST Early Release Observations 2022):
- Ground Truth Published Retrievals:
  - $\log_{10} \chi_{\text{H}_2\text{O}} = -3.50 \pm 0.45$
  - Moderate haze slope with cloud floor $\log_{10} P_c \approx -1.5\text{ bar}$.
- **Acceptance Criterion**: Reproduction of $\text{H}_2\text{O}$ abundance and cloud top pressure within $1\sigma$.

---

## 4. Software Architecture & Implementation Blueprint

### 4.1 Dependency Strategy & Zero-Brittleness Design
To guarantee that the Discovery Suite runs seamlessly on any environment without failing due to missing compiled C-extensions (such as `batman` or compiled C-orbiters), we implement:
1. **Native Analytical Mandel-Agol Limb Darkening Transit Generator**:
   Using the semi-analytical quadratic limb darkening equations (Mandel & Agol 2002) in pure vectorized NumPy/SciPy:
   $$I(r) = 1 - u_1(1 - \mu) - u_2(1 - \mu)^2, \quad \mu = \sqrt{1 - r^2}$$
2. **Native Radiative Transfer Slant-Geometry Integrator**:
   Pure vectorized NumPy/SciPy optical depth integrator along atmospheric impact chords:
   $$\tau(b, \lambda) = 2 \int_0^{s_{\rm max}} \rho(s) \kappa(\lambda, T, P(s)) \, ds$$
3. **PyTorch-Native Normalizing Flow & Neural Density Estimator**:
   Using `torch.nn` modules with analytical invertibility, exact log-determinant tracking, and Adam optimizer.

### 4.2 Module Interface Contracts

```python
# -------------------------------------------------------------------------
# Module 1: Disintegrating Exoplanet & Dust Tail Hunter
# -------------------------------------------------------------------------
class DustTailModel:
    def __init__(self, P: float, T0: float, delta: float, sigma_ing: float, 
                 lambda_tail: float, alpha: float = 1.0, 
                 f_scat: float = 0.0, phi_scat: float = -0.02, sigma_scat: float = 0.008):
        ...
    def evaluate(self, times: np.ndarray) -> np.ndarray: ...
    def fit(self, times: np.ndarray, fluxes: np.ndarray, errs: np.ndarray) -> dict: ...
    def compute_bic_difference(self, times: np.ndarray, fluxes: np.ndarray, errs: np.ndarray) -> float: ...

# -------------------------------------------------------------------------
# Module 2: Exomoon & Trojan World Perturbation Detector
# -------------------------------------------------------------------------
class PhotodynamicPerturbationModel:
    def __init__(self, M_star: float, M_planet: float, P_planet: float, 
                 M_moon: float = 0.0, a_moon: float = 0.0,
                 trojan_mass: float = 0.0, trojan_lagrange: str = 'L4'):
        ...
    def compute_ttv(self, epoch_indices: np.ndarray) -> np.ndarray: ...
    def compute_tdv(self, epoch_indices: np.ndarray) -> np.ndarray: ...
    def evaluate_transit_lightcurve(self, times: np.ndarray) -> np.ndarray: ...
    def detect_exomoon_signature(self, measured_ttvs: np.ndarray, measured_tdvs: np.ndarray) -> dict: ...

# -------------------------------------------------------------------------
# Module 3: Rapid Atmospheric Chemistry Inversion (JWST)
# -------------------------------------------------------------------------
class AtmosphericForwardModel:
    def __init__(self, wavelengths: np.ndarray, R_star: float, M_planet: float, R_planet: float):
        ...
    def compute_transmission_spectrum(self, params: dict) -> np.ndarray: ...

class NeuralPosteriorEstimator(nn.Module):
    def __init__(self, n_features: int, n_params: int = 7, n_flows: int = 4):
        ...
    def forward(self, theta: torch.Tensor, x: torch.Tensor) -> torch.Tensor: ...
    def sample_posterior(self, x_obs: torch.Tensor, n_samples: int = 5000) -> np.ndarray: ...
    def compute_credible_intervals(self, samples: np.ndarray) -> dict: ...
```

---

## 5. Summary and Next Steps

This analysis provides the rigorous physics, mathematical equations, statistical thresholds, and algorithmic designs required to implement the Frontier Astronomy AI Discovery Suite.

- **For Track A (Testing Track)**: Use the analytical models and SNR thresholds defined above to build the synthetic injection-recovery benchmark suite, verifying detection of asymmetric dust tails ($\Delta\text{BIC} \ge 10$), exomoon $\pi/2$ orthogonal TTV-TDV signatures down to Earth/Jupiter configurations, and $1\sigma$ benchmark retrieval on WASP-39b / WASP-96b.
- **For Track B (Implementation Track)**: Implement the native classes adhering to the interface contracts defined above.
