import unittest
from pathlib import Path

from predict import predict_minutes

MODELS = Path(__file__).resolve().parents[1] / "models"


class PredictionTests(unittest.TestCase):
    def test_baseline_batch(self):
        self.assertAlmostEqual(predict_minutes(MODELS / "v1" / "model.pkl", 10_000), 25)

    def test_candidate_batch(self):
        self.assertAlmostEqual(predict_minutes(MODELS / "v2" / "model.pkl", 10_000), 26)

    def test_empty_batch_has_only_startup_cost(self):
        self.assertAlmostEqual(predict_minutes(MODELS / "v1" / "model.pkl", 0), 5)

    def test_negative_record_count_is_rejected(self):
        with self.assertRaises(ValueError):
            predict_minutes(MODELS / "v1" / "model.pkl", -1)
