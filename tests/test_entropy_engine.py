from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from entropy_engine import EntropyAnalyzer, EntropyEngine  # noqa: E402

NOW = 1_000_000.0


class EntropyEngineTests(unittest.TestCase):
    def test_constant_window_has_zero_entropy(self) -> None:
        analyzer = EntropyAnalyzer()
        for index in range(30):
            analyzer.ingest("temperature", 70.0, timestamp=NOW + index)

        self.assertEqual(analyzer.windows["temperature"].entropy, 0.0)

    def test_calibration_requires_minimum_samples(self) -> None:
        analyzer = EntropyAnalyzer(minimum_calibration_samples=30)
        for index in range(29):
            analyzer.ingest("temperature", 70.0, timestamp=NOW + index)

        with self.assertRaises(ValueError):
            analyzer.calibrate("temperature", calibrated_at=NOW + 30)

    def test_no_failure_claim_or_signal_before_calibration(self) -> None:
        engine = EntropyEngine()
        for index in range(40):
            engine.ingest_metric(
                "temperature",
                70.0 + (index % 3 - 1) * 0.1,
                timestamp=NOW + index,
            )

        result = engine.analyze()

        self.assertEqual(result["signals"], [])
        self.assertEqual(
            result["claim_boundary"],
            "entropy_drift_signal_not_failure_prediction",
        )

    def test_entropy_change_after_calibration_emits_drift_signal(self) -> None:
        engine = EntropyEngine()
        for index in range(40):
            engine.ingest_metric("temperature", 70.0, timestamp=NOW + index)
        engine.calibrate_all(calibrated_at=NOW + 40)
        for index in range(40, 100):
            engine.ingest_metric(
                "temperature",
                60.0 + float((index * 17) % 23),
                timestamp=NOW + index,
            )

        result = engine.analyze()

        self.assertEqual(len(result["signals"]), 1)
        signal = result["signals"][0]
        self.assertEqual(signal["metric_name"], "temperature")
        self.assertEqual(signal["direction"], "increasing")
        self.assertIsNone(signal["relative_change"])
        self.assertGreater(signal["absolute_change"], 0.5)

    def test_status_exposes_calibration_not_prediction_accuracy(self) -> None:
        engine = EntropyEngine()
        status = engine.get_engine_status()

        self.assertEqual(status["baselines_set"], 0)
        self.assertEqual(
            status["claim_boundary"],
            "entropy_drift_signal_not_failure_prediction",
        )
        self.assertNotIn("prediction_accuracy", status)
        self.assertNotIn("time_horizon_s", status)


if __name__ == "__main__":
    unittest.main()
