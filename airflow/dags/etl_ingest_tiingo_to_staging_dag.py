import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator

from datetime import datetime, timedelta

current_folder = os.path.dirname(__file__)
# TODO: Check if I need to go up two layers to reach the base level of the repo, because this current dag is inside of financial-etl-poc/airflow/dags folder
project_root_folder = os.path.abspath(os.path.join(current_folder, "../.."))
sys.path.append(project_root_folder)

from etl_drivers.etl_ingest_tiingo_to_staging import main_airflow as ingest_tiingo_to_staging_main_airflow

def log_failure(context):
    with open("/opt/airflow/logs/failure_alerts.log", "a") as f:
        f.write(f"[{datetime.now()}] DAG {context["dag"].dag_id} failed on task {context["task_instance"].task_id}\n")

default_args = {
    "owner": "joe_lu",
    "on_failure_callback": log_failure,
    "depends_on_past":False,
    "retries": 1,
    "retry_delay": timedelta(seconds = 30)
}

with DAG(
    dag_id = "etl_ingest_tiingo_to_staging_daily",
    default_args = default_args,
    description = "Extracts daily closing prices and volumes from Tiingo API and inserts into tbl_tiingo_daily_staging",
    schedule_interval = "0 18 * * 1-5",
    start_date = datetime(2025, 7, 14),
    catchup = False,
    tags = ["Tiingo", "ETL"]
) as dag:
    
    run_etl_ingest_tiingo_to_staging = PythonOperator(
        task_id = "run_etl_ingest_tiingo_to_staging",
        python_callable = ingest_tiingo_to_staging_main_airflow
    )

    run_etl_ingest_tiingo_to_staging