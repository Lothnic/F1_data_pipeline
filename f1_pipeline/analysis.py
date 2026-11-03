"""Acquire, validate and evaluate race results without using post-race predictors."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


def fetch_season(year: int, cache: Path) -> pd.DataFrame:
    """Cache source responses; explicit refresh is achieved by removing the cache."""
    cache.mkdir(parents=True, exist_ok=True)
    races = []
    offset = 0
    while True:
        path = cache / f"{year}-results-{offset}.json"
        if path.exists():
            payload = json.loads(path.read_text())
        else:
            response = requests.get(
                f"https://api.jolpi.ca/ergast/f1/{year}/results/",
                params={"limit": 100, "offset": offset}, timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            path.write_text(json.dumps(payload, indent=2))
        data = payload["MRData"]
        races.extend(data["RaceTable"]["Races"])
        offset += int(data["limit"])
        if offset >= int(data["total"]):
            break
    rows = []
    for race in races:
        for result in race["Results"]:
            rows.append({"round": int(race["round"]), "race": race["raceName"],
                         "driver": result["Driver"]["driverId"],
                         "constructor": result["Constructor"]["constructorId"],
                         "grid": int(result["grid"]), "position": int(result["position"]),
                         "points": float(result["points"]), "status": result["status"]})
    return pd.DataFrame(rows)


def validate(frame: pd.DataFrame) -> None:
    required = {"round", "race", "driver", "constructor", "grid", "position", "points", "status"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if frame.empty or frame[list(required)].isna().any().any():
        raise ValueError("Results must be nonempty and contain no missing required values")
    if frame.duplicated(["round", "driver"]).any():
        raise ValueError("Duplicate driver results within a round")
    for column in ("round", "grid", "position", "points"):
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise ValueError(f"{column} must be numeric")
    if (frame["round"] < 1).any() or (frame["grid"] < 0).any() or (frame["position"] < 1).any() or (frame["points"] < 0).any():
        raise ValueError("Invalid negative or zero values in race results")


def evaluate(frame: pd.DataFrame):
    """Hold out the last quarter of rounds, never randomly split race entries."""
    validate(frame)
    rounds = sorted(frame["round"].unique())
    if len(rounds) < 4:
        raise ValueError("At least four rounds are needed for a chronological holdout")
    cutoff = rounds[max(1, int(len(rounds) * .75))]
    train = frame[frame["round"] < cutoff].copy()
    test = frame[frame["round"] >= cutoff].copy()
    # Grid zero denotes no normal grid slot; map it to the end of the field.
    # The value is fitted only from training data.
    back = int(train["position"].max())
    for part in (train, test):
        part.loc[part["grid"] == 0, "grid"] = back
    features = ["grid", "driver", "constructor"]
    preprocessing = ColumnTransformer([
        ("grid", StandardScaler(), ["grid"]),
        ("identity", OneHotEncoder(handle_unknown="ignore"), ["driver", "constructor"]),
    ])
    model = make_pipeline(preprocessing, Ridge(alpha=10, solver="lsqr"))
    model.fit(train[features], train["position"])
    predictions = model.predict(test[features]).clip(1, back)
    output = test.copy()
    output["prediction"] = predictions
    output["grid_baseline"] = test["grid"]
    metrics = {"train_rounds": sorted(map(int, train["round"].unique())),
               "test_rounds": sorted(map(int, test["round"].unique())),
               "train_rows": len(train), "test_rows": len(test),
               "ridge_mae": mean_absolute_error(test["position"], predictions),
               "grid_baseline_mae": mean_absolute_error(test["position"], test["grid"])}
    return metrics, output


def run(frame: pd.DataFrame, output: Path):
    metrics, predictions = evaluate(frame)
    output.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output / "results.parquet", index=False)
    predictions.to_csv(output / "holdout_predictions.csv", index=False)
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2))
    summary = frame.groupby("driver").agg(points=("points", "sum"), mean_finish=("position", "mean"), races=("round", "nunique")).sort_values("points", ascending=False)
    summary.to_csv(output / "driver_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    summary.head(10)["points"].sort_values().plot.barh(ax=axes[0], color="#2563eb")
    axes[0].set(title="Race points — top 10 drivers", xlabel="Points (sprints excluded)", ylabel="")
    axes[1].scatter(predictions["position"], predictions["prediction"], alpha=.4)
    axes[1].plot([1, 20], [1, 20], "k--", linewidth=1)
    axes[1].set(title="Later-race holdout predictions", xlabel="Actual classified position", ylabel="Predicted position")
    fig.tight_layout()
    fig.savefig(output / "analysis.png", dpi=160)
    plt.close(fig)
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--input", type=Path, help="Use a results CSV instead of the API")
    parser.add_argument("--cache", type=Path, default=Path("data/source"))
    parser.add_argument("--output", type=Path, default=Path("data/analysis"))
    args = parser.parse_args()
    frame = pd.read_csv(args.input) if args.input else fetch_season(args.year, args.cache)
    print(json.dumps(run(frame, args.output), indent=2))


if __name__ == "__main__":
    main()
