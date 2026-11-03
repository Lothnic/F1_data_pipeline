import zipfile

import pandas as pd

from f1_pipeline.history import load_archive, fetch_bulk_history


def test_archive_joins_only_classified_race_entries(tmp_path):
    tables = {
        "session": [{"id": 1, "type": "R", "round_id": 1}, {"id": 2, "type": "Q", "round_id": 1}],
        "sessionentry": [{"session_id": s, "round_entry_id": 1, "position": p, "grid": None, "points": 0, "detail": "Finished"} for s, p in [(1, 1), (1, None), (2, 1)]],
        "round": [{"id": 1, "season_id": 1, "number": 1, "name": "Race"}],
        "season": [{"id": 1, "year": 1950}],
        "roundentry": [{"id": 1, "team_driver_id": 1}],
        "teamdriver": [{"id": 1, "driver_id": 1, "team_id": 1}],
        "driver": [{"id": 1, "reference": "farina"}],
        "team": [{"id": 1, "reference": "alfa"}],
    }
    archive = tmp_path / "history.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for name, rows in tables.items():
            z.writestr(f"formula_one_{name}.csv", pd.DataFrame(rows).to_csv(index=False))
    frame = load_archive(archive)
    assert len(frame) == 1
    assert frame.iloc[0][["season", "round", "driver", "constructor", "grid"]].tolist() == [1950, 1, "farina", "alfa", 0]


def test_bulk_replaces_latest_season(monkeypatch, tmp_path):
    from f1_pipeline import history
    (tmp_path / "history.zip").touch()
    monkeypatch.setattr(history, "load_archive", lambda path: pd.DataFrame({"season": [2024, 2025], "position": [1, 9]}))
    def latest(year, cache, refresh):
        assert year == 2025 and refresh
        return pd.DataFrame({"season": [2025], "position": [2]})
    result = fetch_bulk_history(2024, 2025, tmp_path, False, None, latest)
    assert result.position.tolist() == [1, 2]
