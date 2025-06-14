# scripts/fastf1_extractor.py

from __future__ import annotations # Good practice for type hints
import fastf1
import pandas as pd
import io
import os
from google.cloud import storage
from rich import print

# --- fastf1 Setup ---
# Cache enabled locally on the Airflow worker. It's transient.
fastf1.Cache.enable_cache('f1_cache')

# --- Global GCS Client and Bucket (Initialized at runtime by _initialize_gcs_client_for_task) ---
_storage_client: storage.Client | None = None
_bucket: storage.Bucket | None = None
_GCP_PROJECT_ID: str | None = None
_GCS_BUCKET_NAME: str | None = None
RAW_PREFIX = 'raw/fastf1/'

def _initialize_gcs_client_for_task():
    """
    Initializes the GCS client and bucket instance for the current task.
    This runs at task execution time within the Airflow worker.
    """
    global _storage_client, _bucket, _GCP_PROJECT_ID, _GCS_BUCKET_NAME

    # In Composer, these env vars are typically set at the environment level,
    # or you can use Airflow Connections.
    _GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
    _GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')

    if not _GCP_PROJECT_ID or not _GCS_BUCKET_NAME:
        raise ValueError(
            "GCP_PROJECT_ID or GCS_BUCKET_NAME environment variables are not set "
            "in the Airflow environment. Please configure them in Composer."
        )

    try:
        _storage_client = storage.Client(project=_GCP_PROJECT_ID)
        _bucket = _storage_client.bucket(_GCS_BUCKET_NAME)
        print(f"[bold green]Task execution: GCS bucket connected: gs://{_GCS_BUCKET_NAME}[/bold green]")
    except Exception as e:
        raise Exception(f"Failed to initialize GCS client or connect to bucket: {e}")


def _upload_dataframe_to_gcs_parquet(df: pd.DataFrame, gcs_path: str):
    """
    Uploads a Pandas DataFrame to Google Cloud Storage as a Parquet file.
    Assumes _bucket is already initialized.
    """
    if df.empty:
        print(f"[yellow]DataFrame for {gcs_path} is empty, skipping upload.[/yellow]")
        return False

    df_to_save = df.copy()
    for col in df_to_save.select_dtypes(include=['timedelta64[ns]']).columns:
        df_to_save[col] = df_to_save[col].dt.total_seconds().fillna(-1)

    df_to_save.columns = df_to_save.columns.astype(str)

    parquet_buffer = io.BytesIO()
    df_to_save.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)

    blob = _bucket.blob(gcs_path)
    try:
        blob.upload_from_file(parquet_buffer, content_type='application/octet-stream')
        print(f"[bold green]Uploaded gs://{_GCS_BUCKET_NAME}/{gcs_path}.[/bold green]")
        return True
    except Exception as e:
        print(f"[red]Failed to upload gs://{_GCS_BUCKET_NAME}/{gcs_path}: {e}[/red]")
        raise


def extract_and_save_f1_session_data(year: int, round_num: int, session_type: str):
    """
    Extracts all main dataframes for a given F1 session and saves them to GCS raw zone.
    This function is designed to be called by an Airflow PythonOperator.
    """
    # Initialize GCS client when the task function is called
    _initialize_gcs_client_for_task()

    base_gcs_path = f"{RAW_PREFIX}year={year}/round={round_num}/session_type={session_type}/"

    try:
        session = fastf1.get_session(year, round_num, session_type)
        print(f"[bold blue]Loading session data for {year} Round {round_num} ({session_type}): {session.event['EventName']}[/bold blue]")

        session.load(laps=True, results=True, weather=True, messages=False,
                     full_team_info=False, full_race_results=False,
                     telemetry=False, car_data=False)

        dataframes_to_save = {}
        session_dfs = [
            'laps', 'results', 'drivers', 'constructors', 'weather_data',
        ]
        for df_attr in session_dfs:
            if hasattr(session, df_attr) and isinstance(getattr(session, df_attr), pd.DataFrame):
                dataframes_to_save[df_attr] = getattr(session, df_attr)
            elif hasattr(session, df_attr) and getattr(session, df_attr) is None:
                print(f"[yellow]Session attribute '{df_attr}' is None for {year} R{round_num} {session_type}, skipping.[/yellow]")
            else:
                 print(f"[yellow]Session attribute '{df_attr}' not a DataFrame or missing for {year} R{round_num} {session_type}, skipping.[/yellow]")

        if not dataframes_to_save:
            raise ValueError(f"No valid dataframes found to save for {year} R{round_num} {session_type}.")

        all_uploaded = True
        for df_name, df_obj in dataframes_to_save.items():
            success = _upload_dataframe_to_gcs_parquet(df_obj, f"{base_gcs_path}{df_name}.parquet")
            if not success:
                all_uploaded = False

        if not all_uploaded:
            raise ValueError(f"Not all dataframes uploaded successfully for {year} R{round_num} {session_type}")

        print(f"[bold green]Finished extracting and saving to raw GCS for {year} R{round_num} {session_type}.[/bold green]")
        return True
    except Exception as e:
        print(f"[bold red]Critical error in F1 data extraction task for {year} R{round_num} {session_type}: {e}[/bold red]")
        raise