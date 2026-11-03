import pandas as pd
import pytest
from f1_pipeline.analysis import evaluate, validate


def sample():
    return pd.DataFrame([dict(season=2024, round=r, race=f"Race {r}", driver=f"d{d}", constructor=f"t{d//2}", grid=d, position=5-d, points=6-d, status="Finished") for r in range(1, 9) for d in range(1, 5)])


def test_duplicate_results_rejected():
    frame = sample()
    with pytest.raises(ValueError, match="Duplicate"):
        validate(pd.concat([frame, frame.iloc[:1]]))


def test_chronological_holdout_and_baseline():
    metrics, predictions = evaluate(sample())
    assert max(metrics["train_events"]) < min(metrics["test_events"])
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


def test_round_numbers_can_repeat_across_seasons():
    frame = sample()
    other = sample().assign(season=2025)
    combined = pd.concat([frame, other], ignore_index=True)
    validate(combined)
    metrics, predictions = evaluate(combined)
    assert max(metrics["train_events"]) < min(metrics["test_events"])
    assert set(predictions.season) == {2025}


def test_shared_historical_drives_are_preserved():
    frame = sample()
    shared = frame.iloc[[0]].assign(position=9)
    validate(pd.concat([frame, shared], ignore_index=True))


def test_cached_pagination_preserves_season_identity(tmp_path):
    import json
    from f1_pipeline.analysis import fetch_season
    race = {"season": "1950", "round": "1", "raceName": "British GP", "Results": [
        {"Driver": {"driverId": "farina"}, "Constructor": {"constructorId": "alfa"},
         "grid": "1", "position": "1", "points": "9", "status": "Finished"}]}
    (tmp_path / "1950-results-0.json").write_text(json.dumps({"MRData": {
        "limit": "100", "total": "1", "RaceTable": {"Races": [race]}}}))
    result = fetch_season(1950, tmp_path)
    assert result.season.tolist() == [1950]
    assert result.driver.tolist() == ["farina"]


def test_latest_season_refreshed(monkeypatch, tmp_path):
    from f1_pipeline import analysis
    calls = []

    def fake_fetch(year, cache, refresh=False):
        calls.append((year, refresh))
        return sample().assign(season=year)

    monkeypatch.setattr(analysis, "fetch_season", fake_fetch)
    result = analysis.fetch_history_api(2024, 2026, tmp_path)
    assert sorted(calls) == [(2024, False), (2025, False), (2026, True)]
    assert result.season.nunique() == 3
