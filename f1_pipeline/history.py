"""Normalize Jolpica's bulk archive and refresh the latest selected season."""
import hashlib
import json
import zipfile
from pathlib import Path

import pandas as pd


def load_archive(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        def table(name):
            return pd.read_csv(archive.open(f"formula_one_{name}.csv"))
        sessions = table("session").query("type == 'R'")[["id", "round_id"]].rename(columns={"id": "session_id"})
        entries = table("sessionentry").merge(sessions, on="session_id", validate="many_to_one")
        entries = entries.loc[entries.position.notna()].copy()
        rounds = table("round")[["id", "season_id", "number", "name"]].rename(columns={"id": "round_id", "number": "round", "name": "race"})
        entries = entries.merge(rounds, on="round_id", validate="many_to_one")
        entries = entries.merge(table("season")[["id", "year"]].rename(columns={"id": "season_id", "year": "season"}), on="season_id", validate="many_to_one")
        cars = table("roundentry")[["id", "team_driver_id"]].rename(columns={"id": "round_entry_id"})
        entries = entries.merge(cars, on="round_entry_id", validate="many_to_one")
        identities = table("teamdriver")[["id", "driver_id", "team_id"]].rename(columns={"id": "team_driver_id"})
        entries = entries.merge(identities, on="team_driver_id", validate="many_to_one")
        entries = entries.merge(table("driver")[["id", "reference"]].rename(columns={"id": "driver_id", "reference": "driver"}), on="driver_id", validate="many_to_one")
        entries = entries.merge(table("team")[["id", "reference"]].rename(columns={"id": "team_id", "reference": "constructor"}), on="team_id", validate="many_to_one")
    entries["grid"] = entries["grid"].fillna(0).astype(int)
    entries["status"] = entries["detail"].fillna("Unknown")
    for column in ("season", "round", "position"):
        entries[column] = entries[column].astype(int)
    return entries[["season", "round", "race", "driver", "constructor", "grid", "position", "points", "status"]]


def fetch_bulk_history(start, end, cache, refresh, get, fetch_season):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / "history.zip"
    if refresh or not path.exists():
        response = get("https://api.jolpi.ca/data/dumps/download/", timeout=30)
        response.raise_for_status()
        metadata = response.json()["delayed_dumps"]["csv"]
        response = get(metadata["download_url"], timeout=90)
        response.raise_for_status()
        if hashlib.sha256(response.content).hexdigest() != metadata["file_hash"]:
            raise ValueError("Bulk archive checksum does not match source metadata")
        path.write_bytes(response.content)
        (cache / "history-source.json").write_text(json.dumps(metadata, indent=2))
    frame = load_archive(path)
    # The public archive is delayed: replace its latest season with fresh API results.
    frame = frame[(frame.season >= start) & (frame.season < end)]
    latest = fetch_season(end, cache, refresh=True)
    return pd.concat([frame, latest], ignore_index=True)
