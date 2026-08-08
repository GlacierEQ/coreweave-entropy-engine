"""Calibrated entropy-drift detection for infrastructure telemetry.

This private GlacierEQ R&D prototype measures changes in metric-distribution
entropy relative to an explicit calibration baseline. It emits drift signals,
not failure predictions. No novelty priority, production deployment, failure
forecast accuracy, or downtime reduction is claimed.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class MetricWindow:
    metric_name: str
    values: list[float]
    timestamps: list[float]

    @property
    def entropy(self) -> float:
        if len(self.values) < 2:
            return 0.0
        minimum = min(self.values)
        maximum = max(self.values)
        span = maximum - minimum
        if span <= 1e-12:
            return 0.0

        bin_count = min(32, max(2, int(math.sqrt(len(self.values)))))
        bins = [0] * bin_count
        for value in self.values:
            index = min(
                int((value - minimum) / span * bin_count),
                bin_count - 1,
            )
            bins[index] += 1

        sample_count = len(self.values)
        return -sum(
            (count / sample_count) * math.log2(count / sample_count)
            for count in bins
            if count
        )


@dataclass(frozen=True, slots=True)
class EntropyBaseline:
    metric_name: str
    entropy: float
    sample_count: int
    calibrated_at: float


@dataclass(frozen=True, slots=True)
class EntropyDriftSignal:
    metric_name: str
    current_entropy: float
    baseline_entropy: float
    absolute_change: float
    relative_change: Optional[float]
    direction: str
    severity: str


class EntropyAnalyzer:
    def __init__(
        self,
        *,
        window_size: int = 100,
        minimum_calibration_samples: int = 30,
        relative_threshold: float = 0.30,
        absolute_threshold: float = 0.50,
    ) -> None:
        if window_size < minimum_calibration_samples:
            raise ValueError("window_size must cover calibration samples")
        if minimum_calibration_samples < 2:
            raise ValueError("minimum_calibration_samples must be at least 2")
        if relative_threshold <= 0 or absolute_threshold <= 0:
            raise ValueError("drift thresholds must be positive")
        self.window_size = window_size
        self.minimum_calibration_samples = minimum_calibration_samples
        self.relative_threshold = relative_threshold
        self.absolute_threshold = absolute_threshold
        self.windows: dict[str, MetricWindow] = {}
        self.baselines: dict[str, EntropyBaseline] = {}

    def ingest(
        self,
        metric_name: str,
        value: float,
        *,
        timestamp: float | None = None,
    ) -> None:
        if not metric_name:
            raise ValueError("metric_name is required")
        observed_at = time.time() if timestamp is None else timestamp
        window = self.windows.setdefault(
            metric_name,
            MetricWindow(metric_name, [], []),
        )
        window.values.append(value)
        window.timestamps.append(observed_at)
        if len(window.values) > self.window_size:
            overflow = len(window.values) - self.window_size
            del window.values[:overflow]
            del window.timestamps[:overflow]

    def calibrate(
        self,
        metric_name: str,
        *,
        calibrated_at: float | None = None,
    ) -> EntropyBaseline:
        window = self.windows.get(metric_name)
        if window is None or len(window.values) < self.minimum_calibration_samples:
            raise ValueError(
                f"{metric_name}: insufficient samples for calibration"
            )
        baseline = EntropyBaseline(
            metric_name=metric_name,
            entropy=window.entropy,
            sample_count=len(window.values),
            calibrated_at=(
                time.time() if calibrated_at is None else calibrated_at
            ),
        )
        self.baselines[metric_name] = baseline
        return baseline

    def compute_system_entropy(self) -> float:
        entropies = [window.entropy for window in self.windows.values()]
        if not entropies:
            return 0.0
        return sum(entropies) / len(entropies)

    def detect_drift(self, metric_name: str) -> Optional[EntropyDriftSignal]:
        window = self.windows.get(metric_name)
        baseline = self.baselines.get(metric_name)
        if window is None or baseline is None:
            return None

        current = window.entropy
        absolute_change = current - baseline.entropy
        if baseline.entropy > 1e-12:
            relative_change: float | None = absolute_change / baseline.entropy
            triggered = abs(relative_change) >= self.relative_threshold
        else:
            relative_change = None
            triggered = abs(absolute_change) >= self.absolute_threshold
        if not triggered:
            return None

        magnitude = (
            abs(relative_change)
            if relative_change is not None
            else abs(absolute_change) / self.absolute_threshold
        )
        severity = "HIGH" if magnitude >= 1.0 else "ELEVATED"
        return EntropyDriftSignal(
            metric_name=metric_name,
            current_entropy=round(current, 6),
            baseline_entropy=round(baseline.entropy, 6),
            absolute_change=round(absolute_change, 6),
            relative_change=(
                round(relative_change, 6)
                if relative_change is not None
                else None
            ),
            direction="increasing" if absolute_change > 0 else "decreasing",
            severity=severity,
        )


class EntropyEngine:
    def __init__(self, analyzer: EntropyAnalyzer | None = None) -> None:
        self.analyzer = analyzer or EntropyAnalyzer()
        self._analysis_history: list[dict[str, object]] = []

    def ingest_metric(
        self,
        metric_name: str,
        value: float,
        *,
        timestamp: float | None = None,
    ) -> None:
        self.analyzer.ingest(metric_name, value, timestamp=timestamp)

    def calibrate_all(self, *, calibrated_at: float | None = None) -> None:
        for metric_name in sorted(self.analyzer.windows):
            self.analyzer.calibrate(
                metric_name,
                calibrated_at=calibrated_at,
            )

    def analyze(self) -> dict[str, object]:
        signals = [
            signal
            for metric_name in sorted(self.analyzer.windows)
            if (signal := self.analyzer.detect_drift(metric_name)) is not None
        ]
        result: dict[str, object] = {
            "system_entropy": round(
                self.analyzer.compute_system_entropy(),
                6,
            ),
            "signals": [
                {
                    "metric_name": signal.metric_name,
                    "current_entropy": signal.current_entropy,
                    "baseline_entropy": signal.baseline_entropy,
                    "absolute_change": signal.absolute_change,
                    "relative_change": signal.relative_change,
                    "direction": signal.direction,
                    "severity": signal.severity,
                }
                for signal in signals
            ],
            "metrics_tracked": len(self.analyzer.windows),
            "baselines_set": len(self.analyzer.baselines),
            "claim_boundary": "entropy_drift_signal_not_failure_prediction",
        }
        self._analysis_history.append(result)
        if len(self._analysis_history) > 200:
            self._analysis_history = self._analysis_history[-100:]
        return result

    def get_engine_status(self) -> dict[str, object]:
        return {
            "system_entropy": round(
                self.analyzer.compute_system_entropy(),
                6,
            ),
            "metrics_tracked": len(self.analyzer.windows),
            "baselines_set": len(self.analyzer.baselines),
            "total_analyses": len(self._analysis_history),
            "claim_boundary": "entropy_drift_signal_not_failure_prediction",
        }


if __name__ == "__main__":
    engine = EntropyEngine()
    demo_time = 1_000_000.0
    for index in range(40):
        engine.ingest_metric(
            "gpu_temperature",
            70.0 + (index % 3 - 1) * 0.1,
            timestamp=demo_time + index,
        )
    engine.calibrate_all(calibrated_at=demo_time + 40)
    for index in range(40, 100):
        engine.ingest_metric(
            "gpu_temperature",
            60.0 + float((index * 17) % 23),
            timestamp=demo_time + index,
        )
    print(json.dumps(engine.analyze(), indent=2))
