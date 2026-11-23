"""Estimate batch runtime using a supplied model file."""
import argparse
import json
import pickle
from pathlib import Path


def predict_minutes(model_path, records):
    if records < 0:
        raise ValueError("records must be nonnegative")
    model = Path(model_path)
    if model.suffix == ".pkl":
        # Pickles execute Python during loading. Use only trusted model artifacts.
        with model.open("rb") as stream:
            estimator = pickle.load(stream)
        return float(estimator.predict([[records]])[0])
    parameters = json.loads(model.read_text(encoding="utf-8"))
    return parameters["startup_minutes"] + parameters["minutes_per_thousand"] * records / 1000


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("records", type=int)
    args = parser.parse_args()
    print(predict_minutes(args.model, args.records))
