import io
from unittest.mock import MagicMock

import pandas as pd
import pytest

from scripts import fastf1_extractor as extractor


def test_parquet_upload_preserves_missing_timedeltas():
    bucket = MagicMock()
    captured = {}
    bucket.blob.return_value.upload_from_file.side_effect = lambda f, **kw: captured.update(data=f.read())
    frame = pd.DataFrame({"LapTime": pd.to_timedelta([1.5, None], unit="s")})
    assert extractor._upload_dataframe_to_gcs_parquet(frame, bucket, "laps.parquet")
    result = pd.read_parquet(io.BytesIO(captured["data"]))
    assert result.loc[0, "LapTime"] == 1.5
    assert pd.isna(result.loc[1, "LapTime"])
    bucket.blob.assert_called_once_with("laps.parquet")


def test_empty_frame_is_not_uploaded():
    bucket = MagicMock()
    assert not extractor._upload_dataframe_to_gcs_parquet(pd.DataFrame(), bucket, "empty.parquet")
    bucket.blob.assert_not_called()


def test_extraction_requires_configuration(monkeypatch):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        extractor.extract_and_save_f1_session_data(2024, 1, "R")


def test_extraction_uploads_available_frames(monkeypatch, tmp_path):
    monkeypatch.setenv("GCP_PROJECT_ID", "project")
    monkeypatch.setenv("GCS_BUCKET_NAME", "bucket")
    monkeypatch.setenv("FASTF1_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(extractor.fastf1.Cache, "enable_cache", lambda path: None)
    session = MagicMock(laps=pd.DataFrame({"lap": [1]}), results=pd.DataFrame(), weather_data=None)
    monkeypatch.setattr(extractor.fastf1, "get_session", lambda *args: session)
    bucket = MagicMock()
    monkeypatch.setattr(extractor.storage, "Client", lambda **kw: MagicMock(bucket=lambda name: bucket))
    assert extractor.extract_and_save_f1_session_data(2024, 1, "R") == ["laps"]
    bucket.blob.assert_called_once_with("raw/fastf1/year=2024/round=1/session_type=R/laps.parquet")
    session.load.assert_called_once_with(laps=True, telemetry=False, weather=True, messages=False)


def test_local_extraction_skips_unloaded_data(monkeypatch, tmp_path):
    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    monkeypatch.delenv("GCS_BUCKET_NAME", raising=False)
    monkeypatch.setenv("FASTF1_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(extractor.fastf1.Cache, "enable_cache", lambda path: None)

    class Session:
        results = pd.DataFrame({"DriverNumber": ["1"]})
        weather_data = pd.DataFrame()

        def load(self, **kwargs):
            pass

        @property
        def laps(self):
            raise extractor.fastf1.core.DataNotLoadedError("not loaded")

    monkeypatch.setattr(extractor.fastf1, "get_session", lambda *args: Session())
    assert extractor.extract_and_save_f1_session_data(2024, 1, "R", str(tmp_path)) == ["results"]
    path = tmp_path / "raw/fastf1/year=2024/round=1/session_type=R/results.parquet"
    assert pd.read_parquet(path)["DriverNumber"].tolist() == ["1"]
