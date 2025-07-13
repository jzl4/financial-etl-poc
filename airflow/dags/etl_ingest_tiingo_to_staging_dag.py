import os
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator

from datetime import datetime, timedelta
import pendulum
local_timezone = pendulum.timezone("America/New_York")

# I need to go up two layers to reach the base level of the repo, because this current dag is inside of financial-etl-poc/airflow/dags folder
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, "../.."))
sys.path.append(project_root_folder)

from etl_drivers.etl_ingest_tiingo_to_staging import main_airflow as ingest_tiingo_to_staging_main_airflow

def log_failure(context):
    now = datetime.now()
    dag_id = context["dag"].dag_id
    task_id = context["task_instance"].task_id
    with open("/opt/airflow/logs/failure_alerts.log", "a") as f:
        f.write(f"{now} - DAG {dag_id} failed on task {task_id}\n")

default_args = {
    "owner": "joe_lu",
    "on_failure_callback": log_failure,
    "depends_on_past":False,
    "retries": 1,
    "retry_delay": timedelta(seconds = 30)
}

with DAG(
    dag_id = "dag_etl_ingest_tiingo_to_staging",
    default_args = default_args,
    description = "Extracts daily closing prices and volumes from Tiingo API and inserts into tbl_tiingo_daily_staging",
    schedule_interval = "0 22 * * 1-5",
    start_date = datetime(2025, 7, 14, tzinfo = local_timezone),
    catchup = False,
    tags = ["Tiingo", "ETL"]
) as dag:
    
    run_etl_ingest_tiingo_to_staging = PythonOperator(
        task_id = "task_etl_ingest_tiingo_to_staging",
        python_callable = ingest_tiingo_to_staging_main_airflow
    )

    run_etl_ingest_tiingo_to_staging