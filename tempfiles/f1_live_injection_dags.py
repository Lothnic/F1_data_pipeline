from __future__ import annotations
import pendulum
import os
import sys
from datetime import datetime, timedelta

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator # Use for start/end points
from airflow.decorators import task, dag # Use decorator syntax for dynamic mapping

# Add the scripts directory to Python path so Airflow can find modules inside it
# This is often needed in Composer unless you configure plugins/dags_folder.
# A more robust way in Composer is to upload your 'scripts' folder to the 'data/' folder
# inside your Composer GCS bucket, then configure Airflow to add 'data/' to Python path.
# For now, if you place scripts directly in `dags/` it's simpler, or assume path setup.
# Let's assume you'll place `fastf1_extractor.py` inside `dags/` for this quick test for now.
# Or, if you keep `scripts/` separate, you need to tell Airflow where to find it.
# The common way is Composer Environment Variables -> PYPI_PACKAGE_PATHS or similar mechanism.
# For a simple local test:
# sys.path.append(os.path.join(os.path.dirname(__file__), '..')) # Adds f1_data_pipeline to path

# For Composer, it's typically best to upload your supporting Python files
# to a designated folder within the Composer environment's GCS bucket
# (e.g., `dags/include/` or `dags/utils/`) and Airflow handles imports.
# For this current step, to make it work reliably on Composer, let's keep the extractor
# functions WITHIN this DAG file for now, similar to our last successful run.
# We will modularize it properly on Day 6.

# TEMPORARY: Copy the core extractor functions directly into the DAG file
# for ease of deployment. This is NOT the final modular approach.
# --- START COPIED CODE FROM scripts/fastf1_extractor.py ---
import fastf1
import pandas as pd
import io
from google.cloud import storage
# from rich import print # Rich might not be needed in Airflow logs if standard printing is enough, but keep for now.

# These will be set as Airflow Variables or Composer Environment Variables later
# For initial test, ensure your Composer env has these set, or hardcode if absolutely necessary
# to make the DAG parse. Composer Env Variables: https://cloud.google.com/composer/docs/manage-environments#update-env-variables
_GCP_PROJECT_ID_DAG = os.getenv('GCP_PROJECT_ID') # Will be set in Composer environment vars
_GCS_BUCKET_NAME_DAG = os.getenv('GCS_BUCKET_NAME') # Will be set in Composer environment vars

# Initialize client/bucket at DAG parsing time if variables are present, otherwise delay.
# For robust DAG parsing, avoid heavy ops at global scope unless necessary.
# The actual client initialization happens in the task callable.
_storage_client_dag = None
_bucket_dag = None

if _GCP_PROJECT_ID_DAG and _GCS_BUCKET_NAME_DAG:
    try:
        _storage_client_dag = storage.Client(project=_GCP_PROJECT_ID_DAG)
        _bucket_dag = _storage_client_dag.bucket(_GCS_BUCKET_NAME_DAG)
        print(f"DAG parsing: Connected to GCS bucket: gs://{_GCS_BUCKET_NAME_DAG}")
    except Exception as e:
        print(f"DAG parsing error: Failed to connect to GCS bucket: {e}")
        # Do NOT raise here, as it stops DAG parsing. Handle in task.
else:
    print("DAG parsing: GCP_PROJECT_ID or GCS_BUCKET_NAME not set as environment variables. Client init delayed to task execution.")


# --- COPIED _upload_dataframe_to_gcs_parquet (adjusted to use _bucket_dag) ---
def _upload_dataframe_to_gcs_parquet(df: pd.DataFrame, gcs_path: str):
    if df.empty:
        print(f"DataFrame for {gcs_path} is empty, skipping upload.")
        return False
    df_to_save = df.copy()
    for col in df_to_save.select_dtypes(include=['timedelta64[ns]']).columns:
        df_to_save[col] = df_to_save[col].dt.total_seconds().fillna(-1)
    df_to_save.columns = df_to_save.columns.astype(str)
    parquet_buffer = io.BytesIO()
    df_to_save.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)
    blob = _bucket_dag.blob(gcs_path) # Use the DAG-level initialized bucket
    try:
        blob.upload_from_file(parquet_buffer, content_type='application/octet-stream')
        print(f"Uploaded gs://{_GCS_BUCKET_NAME_DAG}/{gcs_path}.")
        return True
    except Exception as e:
        print(f"Failed to upload gs://{_GCS_BUCKET_NAME_DAG}/{gcs_path}: {e}")
        raise


# --- COPIED extract_and_save_f1_session_data (adjusted to remove init/globals within callable) ---
def _extract_and_save_f1_session_data_task(year: int, round_num: int, session_type: str):
    """
    Airflow task function to extract and save F1 data for a single session.
    (Adapted from fastf1_extractor.py, now directly in DAG for first deployment)
    """
    fastf1.Cache.enable_cache('f1_cache') # Ensure cache is enabled for the task context
    RAW_PREFIX = 'raw/fastf1/'

    # Re-initialize client if not done globally or if globals somehow reset
    # This is robust but might be slightly less efficient for highly concurrent tasks
    # but safe for a first deploy.
    global _storage_client_dag, _bucket_dag, _GCP_PROJECT_ID_DAG, _GCS_BUCKET_NAME_DAG
    if _storage_client_dag is None or _bucket_dag is None:
         _GCP_PROJECT_ID_DAG = os.getenv('GCP_PROJECT_ID')
         _GCS_BUCKET_NAME_DAG = os.getenv('GCS_BUCKET_NAME')
         _storage_client_dag = storage.Client(project=_GCP_PROJECT_ID_DAG)
         _bucket_dag = _storage_client_dag.bucket(_GCS_BUCKET_NAME_DAG)
         print(f"Task runtime: Re-initialized GCS bucket: gs://{_GCS_BUCKET_NAME_DAG}")

    try:
        session = fastf1.get_session(year, round_num, session_type)
        print(f"Loading session data for {year} Round {round_num} ({session_type}): {session.event['EventName']}")

        # Only load necessary data types. Avoid telemetry/car_data for size/cost initially.
        session.load(laps=True, results=True, weather=True, messages=False,
                     full_team_info=False, full_race_results=False,
                     telemetry=False, car_data=False)

        base_gcs_path = f"{RAW_PREFIX}year={year}/round={round_num}/session_type={session_type}/"

        dataframes_to_save = {}
        session_dfs = ['laps', 'results', 'drivers', 'constructors', 'weather_data']
        for df_attr in session_dfs:
            if hasattr(session, df_attr) and isinstance(getattr(session, df_attr), pd.DataFrame):
                dataframes_to_save[df_attr] = getattr(session, df_attr)
            else:
                print(f"Session attribute '{df_attr}' not a DataFrame or missing for {year} R{round_num} {session_type}, skipping.")

        if not dataframes_to_save:
            raise ValueError(f"No valid dataframes found to save for {year} R{round_num} {session_type}. Check session.load() parameters and data availability.")

        all_uploaded = True
        for df_name, df_obj in dataframes_to_save.items():
            success = _upload_dataframe_to_gcs_parquet(df_obj, f"{base_gcs_path}{df_name}.parquet")
            if not success:
                all_uploaded = False

        if not all_uploaded:
            raise ValueError(f"Not all dataframes uploaded successfully for {year} R{round_num} {session_type}")

        print(f"Finished extracting and saving to raw GCS for {year} R{round_num} {session_type}.")
        return True
    except Exception as e:
        print(f"Critical error in F1 data extraction task for {year} R{round_num} {session_type}: {e}")
        raise # Re-raise to mark task as failed
# --- END COPIED CODE ---

# --- Callable to get event schedule for dynamic mapping ---
@task
def get_f1_session_params(year: int):
    """
    Retrieves the list of race rounds and session types for a given year.
    Returns a list of dicts suitable for expand_kwargs.
    """
    schedule = fastf1.get_event_schedule(year)
    # Only consider 'conventional' and 'sprint' race formats for ingestion
    relevant_rounds = schedule[schedule['EventFormat'].isin(['conventional', 'sprint'])]['RoundNumber'].tolist()

    session_types = ['R', 'Q', 'S', 'FP1', 'FP2', 'FP3']
    # Filter session_types based on EventFormat for sprint weekends
    # For simplicity, we'll iterate through all 6 types, and if a session isn't there,
    # fastf1.get_session will handle it, or we get empty DFs.

    params_list = []
    for round_num in relevant_rounds:
        for session_type in session_types:
            params_list.append({
                "year": year,
                "round_num": round_num,
                "session_type": session_type
            })
    return params_list

# --- DAG Definition ---
@dag(
    dag_id="f1_live_data_ingestion",
    start_date=pendulum.datetime(2025, 6, 1, tz="UTC"), # Start from current year/month
    schedule="@weekly", # Run once a week, ideal for checking for new races
    catchup=False,
    tags=["f1", "live", "gcs", "ingestion"],
    description="Extracts live/recent F1 data from FastF1 weekly and stores it in GCS raw zone.",
)
def f1_live_ingestion_pipeline():
    start = DummyOperator(task_id="start")

    # Task to get the parameters for dynamic mapping
    f1_session_params = get_f1_session_params(year=2025) # Focus on the current year

    # Dynamic Task Mapping for extraction
    # Each item in f1_session_params will create a new instance of this task
    extract_raw_f1_data_task = PythonOperator(
        task_id="extract_raw_f1_data",
        python_callable=_extract_and_save_f1_session_data_task,
        # Using op_kwargs to pass multiple arguments
    ).partial().expand(op_kwargs=f1_session_params)


    end = DummyOperator(task_id="end")

    start >> f1_session_params >> extract_raw_f1_data_task >> end

# Instantiate the DAG
f1_live_ingestion_pipeline()