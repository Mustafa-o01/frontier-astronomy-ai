"""Amortized Training Pipeline for Neural Posterior Estimation (NPE) Flow.

Generates synthetic training grids of exoplanet transmission spectra from the forward
radiative transfer model across the 7D atmospheric parameter space and trains
the Conditional RealNVP normalizing flow via negative log-likelihood minimization.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from frontier_astronomy.atmospheric.forward_model import (
    ATMOSPHERIC_PARAMETER_NAMES,
    AtmosphericForwardModel,
)
from frontier_astronomy.atmospheric.normalizing_flow import (
    DEFAULT_PARAM_BOUNDS,
    RealNVPConditionalFlow,
)


def generate_atmospheric_grid(
    forward_model: Optional[AtmosphericForwardModel] = None,
    n_samples: int = 1500,
    noise_ppm: float = 40.0,
    param_bounds: Optional[Dict[str, Tuple[float, float]]] = None,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate a synthetic training grid of (parameter_vector, standardized_spectral_excess) pairs.

    Standardizes spectra into baseline-subtracted relative transit depth channels:
    delta_D(lambda) * 1000.0, matching the invariant representation expected by RealNVPConditionalFlow.
    """
    rng = np.random.default_rng(seed)
    model = forward_model if forward_model is not None else AtmosphericForwardModel()
    bounds = param_bounds or DEFAULT_PARAM_BOUNDS

    n_params = len(ATMOSPHERIC_PARAMETER_NAMES)
    thetas = np.zeros((n_samples, n_params), dtype=np.float64)

    # 50% detectable regime, 50% depleted regime for molecular gases
    for i in range(n_samples):
        # log_H2O
        if rng.random() < 0.5:
            thetas[i, 0] = rng.uniform(-5.0, -2.0)
        else:
            thetas[i, 0] = rng.uniform(-12.0, -5.0)

        # log_CO2
        if rng.random() < 0.5:
            thetas[i, 1] = rng.uniform(-5.0, -2.0)
        else:
            thetas[i, 1] = rng.uniform(-12.0, -5.0)

        # log_CH4
        if rng.random() < 0.3:
            thetas[i, 2] = rng.uniform(-5.0, -2.0)
        else:
            thetas[i, 2] = rng.uniform(-12.0, -5.0)

        # log_CO
        if rng.random() < 0.5:
            thetas[i, 3] = rng.uniform(-5.0, -2.0)
        else:
            thetas[i, 3] = rng.uniform(-12.0, -5.0)

        # T_eq
        thetas[i, 4] = rng.uniform(bounds["T_eq"][0], bounds["T_eq"][1])

        # log_Pc
        thetas[i, 5] = rng.uniform(bounds["log_Pc"][0], bounds["log_Pc"][1])

        # haze_slope
        thetas[i, 6] = rng.uniform(bounds["haze_slope"][0], bounds["haze_slope"][1])

    # Compute spectra through forward model
    spectra = np.zeros((n_samples, model.n_channels), dtype=np.float64)
    noise_frac = noise_ppm * 1e-6

    for i in range(n_samples):
        spec = model.compute_transmission_spectrum(thetas[i])
        if noise_ppm > 0:
            spec = spec + rng.normal(0.0, noise_frac, model.n_channels)

        # Invariant baseline subtraction and scaling
        base_depth = float(np.median(spec))
        delta_depth = (spec - base_depth) * 1000.0

        # Simulate instrument cutoff (e.g. NIRISS cutoff at 2.8 um) for 30% of samples
        if rng.random() < 0.30:
            niriss_mask = model.wavelengths > 2.8
            delta_depth[niriss_mask] = 0.0

        spectra[i] = delta_depth

    return thetas, spectra


class AmortizedFlowTrainer:
    """Trainer for Conditional RealNVP Normalizing Flow on atmospheric grids."""

    def __init__(
        self,
        flow_model: RealNVPConditionalFlow,
        lr: float = 1e-3,
        weight_decay: float = 1e-5,
    ) -> None:
        """Initialize flow trainer.

        Args:
            flow_model: RealNVPConditionalFlow network instance.
            lr: Learning rate for Adam optimizer.
            weight_decay: L2 regularization coefficient.
        """
        self.model = flow_model
        self.lr = lr
        self.weight_decay = weight_decay

        if HAS_TORCH and isinstance(flow_model, nn.Module):
            self.optimizer = torch.optim.AdamW(
                flow_model.parameters(), lr=lr, weight_decay=weight_decay
            )
        else:
            self.optimizer = None

    def fit(
        self,
        thetas: np.ndarray,
        spectra: np.ndarray,
        n_epochs: int = 5,
        batch_size: int = 64,
        validation_split: float = 0.1,
    ) -> Dict[str, List[float]]:
        """Train the RealNVP normalizing flow on the synthetic atmospheric grid.

        Args:
            thetas: Array of atmospheric parameters (N, 7).
            spectra: Array of observed spectra (N, M).
            n_epochs: Training epochs.
            batch_size: Mini-batch size.
            validation_split: Fraction of samples reserved for validation.

        Returns:
            Dictionary with 'train_loss' and 'val_loss' histories.
        """
        if not HAS_TORCH or self.optimizer is None:
            # Fallback when PyTorch is absent
            return {"train_loss": [0.0] * n_epochs, "val_loss": [0.0] * n_epochs}

        n_samples = len(thetas)
        n_val = max(1, int(n_samples * validation_split))
        n_train = n_samples - n_val

        # Shuffle indices
        indices = np.random.permutation(n_samples)
        train_idx, val_idx = indices[:n_train], indices[n_train:]

        train_thetas = torch.from_numpy(thetas[train_idx].astype(np.float32))
        train_spectra = torch.from_numpy(spectra[train_idx].astype(np.float32))
        val_thetas = torch.from_numpy(thetas[val_idx].astype(np.float32))
        val_spectra = torch.from_numpy(spectra[val_idx].astype(np.float32))

        train_dataset = TensorDataset(train_thetas, train_spectra)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

        history: Dict[str, List[float]] = {"train_loss": [], "val_loss": []}

        for epoch in range(n_epochs):
            self.model.train()
            total_train_loss = 0.0
            total_batches = 0

            for theta_b, spec_b in train_loader:
                self.optimizer.zero_grad()
                log_p = self.model.log_prob(theta_b, spec_b)
                loss = -torch.mean(log_p)

                if torch.isfinite(loss):
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
                    self.optimizer.step()
                    total_train_loss += float(loss.item())
                    total_batches += 1

            train_loss = total_train_loss / max(1, total_batches)
            history["train_loss"].append(train_loss)

            # Validation loss
            self.model.eval()
            with torch.no_grad():
                val_log_p = self.model.log_prob(val_thetas, val_spectra)
                val_loss = float(-torch.mean(val_log_p).item())
                history["val_loss"].append(val_loss)

        return history

    def save_checkpoint(self, path: Union[str, Path]) -> None:
        """Save model state dictionary to disk."""
        if HAS_TORCH and isinstance(self.model, nn.Module):
            torch.save(self.model.state_dict(), str(path))

    def load_checkpoint(self, path: Union[str, Path]) -> None:
        """Load model state dictionary from disk."""
        if HAS_TORCH and isinstance(self.model, nn.Module):
            self.model.load_state_dict(torch.load(str(path), map_location="cpu"))


def train_amortized_retrieval_model(
    n_samples: int = 500,
    n_epochs: int = 5,
    lr: float = 1e-3,
    noise_ppm: float = 50.0,
    seed: int = 42,
) -> RealNVPConditionalFlow:
    """Convenience helper to generate training grid and fit a RealNVP flow network."""
    forward_model = AtmosphericForwardModel()
    thetas, spectra = generate_atmospheric_grid(
        forward_model=forward_model,
        n_samples=n_samples,
        noise_ppm=noise_ppm,
        seed=seed,
    )
    flow = RealNVPConditionalFlow(
        n_features=forward_model.n_channels,
        n_params=7,
        hidden_dim=128,
        n_layers=4,
    )
    trainer = AmortizedFlowTrainer(flow_model=flow, lr=lr)
    trainer.fit(thetas, spectra, n_epochs=n_epochs)
    return flow


def train_and_save_pretrained_flow(
    output_path: Optional[Union[str, Path]] = None,
    n_samples: int = 1500,
    n_epochs: int = 20,
    lr: float = 1e-3,
    noise_ppm: float = 40.0,
    seed: int = 42,
) -> Optional[RealNVPConditionalFlow]:
    """Train RealNVP normalizing flow on synthetic forward model grid and save weights checkpoint."""
    if not HAS_TORCH:
        return None

    if output_path is None:
        output_path = Path(__file__).resolve().parent / "models" / "pretrained_flow.pt"
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    forward_model = AtmosphericForwardModel()
    thetas, spectra = generate_atmospheric_grid(
        forward_model=forward_model,
        n_samples=n_samples,
        noise_ppm=noise_ppm,
        seed=seed,
    )

    flow = RealNVPConditionalFlow(
        n_features=forward_model.n_channels,
        n_params=7,
        hidden_dim=128,
        n_layers=4,
    )

    trainer = AmortizedFlowTrainer(flow_model=flow, lr=lr)
    trainer.fit(thetas, spectra, n_epochs=n_epochs, batch_size=64)

    flow.save_weights(out_file)
    return flow
