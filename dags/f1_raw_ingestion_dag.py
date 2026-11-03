"""Manually triggered raw ingestion DAG for Airflow 2.x."""
from datetime import datetime, timedelta, timezone

from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator


def extract(**context):
    # Import only during task execution; the repository must be on worker PYTHONPATH.
    from scripts.fastf1_extractor import extract_and_save_f1_session_data
    params = context["params"]
    return extract_and_save_f1_session_data(params["year"], params["round"], params["session"])


with DAG(
    dag_id="f1_raw_ingestion",
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    params={"year": Param(2024, type="integer", minimum=2018),
            "round": Param(1, type="integer", minimum=1),
            "session": Param("R", enum=["R", "Q", "FP1", "FP2", "FP3", "S", "SQ"])},
    tags=["f1", "raw"],
) as dag:
    PythonOperator(task_id="extract_session", python_callable=extract)
