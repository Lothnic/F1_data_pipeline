"""Extract a FastF1 session into the raw Google Cloud Storage zone."""

from __future__ import annotations

import argparse
import io
import os
from pathlib import Path

import fastf1
import pandas as pd
from google.cloud import storage

RAW_PREFIX = "raw/fastf1"


def _parquet_buffer(df: pd.DataFrame) -> io.BytesIO:
    """Serialize a frame with timedeltas represented as seconds."""
    frame = df.copy()
    for column in frame.select_dtypes(include=["timedelta"]).columns:
        frame[column] = frame[column].dt.total_seconds()
    frame.columns = frame.columns.astype(str)
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    buffer.seek(0)
    return buffer


def _upload_dataframe_to_gcs_parquet(df: pd.DataFrame, bucket, path: str) -> bool:
    if df.empty:
        return False
    bucket.blob(path).upload_from_file(_parquet_buffer(df), content_type="application/octet-stream")
    return True


def extract_and_save_f1_session_data(year: int, round_num: int, session_type: str, output_dir: str | None = None):
    """Load a session and upload available laps, results and weather data.

    Existing objects at the same paths are overwritten on a repeat run.
    """
    project = os.getenv("GCP_PROJECT_ID")
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not output_dir and (not project or not bucket_name):
        raise ValueError("Set GCP_PROJECT_ID and GCS_BUCKET_NAME before running extraction.")
    cache = Path(os.getenv("FASTF1_CACHE_DIR", "f1_cache"))
    cache.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    bucket = None if output_dir else storage.Client(project=project).bucket(bucket_name)
    session = fastf1.get_session(year, round_num, session_type)
    session.load(laps=True, telemetry=False, weather=True, messages=False)
    prefix = f"{RAW_PREFIX}/year={year}/round={round_num}/session_type={session_type}"
    uploaded = []
    for name in ("laps", "results", "weather_data"):
        try:
            frame = getattr(session, name, None)
        except fastf1.core.DataNotLoadedError:
            print(f"{name} was not loaded; skipping.")
            continue
        if not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        path = f"{prefix}/{name}.parquet"
        if output_dir:
            destination = Path(output_dir) / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(_parquet_buffer(frame).getvalue())
        else:
            _upload_dataframe_to_gcs_parquet(frame, bucket, path)
        uploaded.append(name)
    if not uploaded:
        raise ValueError("The session did not contain any nonempty dataframes to upload.")
    destination = output_dir if output_dir else f"gs://{bucket_name}"
    print(f"Saved {', '.join(uploaded)} under {destination}/{prefix}/")
    return uploaded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("year", type=int)
    parser.add_argument("round", type=int, help="Championship round number")
    parser.add_argument("session", help="FastF1 session identifier, e.g. R or Q")
    parser.add_argument("--output-dir", help="Write Parquet locally instead of uploading to GCS")
    args = parser.parse_args()
    extract_and_save_f1_session_data(args.year, args.round, args.session, args.output_dir)


if __name__ == "__main__":
    main()
