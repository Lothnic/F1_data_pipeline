from __future__ import annotations
import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator # We'll use BashOperator for simplicity here

with DAG(
    dag_id="hello_airflow_test",
    start_date=pendulum.datetime(2023, 1, 1, tz="UTC"), # This date is in the past to allow immediate testing
    schedule=None, # Set to None for manual triggering only
    catchup=False, # Important: Prevents running for all past missed schedules
    tags=["test"],
    description="A simple test DAG to verify Composer deployment.",
) as dag:
    start_task = BashOperator(
        task_id="start_message",
        bash_command="echo 'Hello from Airflow! The date is $(date)'",
    )

    end_task = BashOperator(
        task_id="end_message",
        bash_command="echo 'Airflow test completed successfully.'",
    )

    start_task >> end_task # Define a simple dependency