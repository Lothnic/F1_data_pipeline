import pandas as pd
import pytest
from f1_pipeline.analysis import evaluate, validate


def sample():
    return pd.DataFrame([dict(round=r, race=f"Race {r}", driver=f"d{d}", constructor=f"t{d//2}", grid=d, position=5-d, points=6-d, status="Finished") for r in range(1, 9) for d in range(1, 5)])


def test_duplicate_results_rejected():
    frame = sample()
    with pytest.raises(ValueError, match="Duplicate"):
        validate(pd.concat([frame, frame.iloc[:1]]))


def test_chronological_holdout_and_baseline():
    metrics, predictions = evaluate(sample())
    assert max(metrics["train_rounds"]) < min(metrics["test_rounds"])
    expected = (predictions.position - predictions.grid).abs().mean()
    assert metrics["grid_baseline_mae"] == expected
    assert len(predictions) == 8


def test_post_race_points_do_not_affect_predictions():
    frame = sample()
    _, before = evaluate(frame)
    frame["points"] = 9999
    _, after = evaluate(frame)
    assert before.prediction.tolist() == after.prediction.tolist()


def test_too_few_rounds_rejected():
    with pytest.raises(ValueError, match="four rounds"):
        evaluate(sample().query("round < 4"))
