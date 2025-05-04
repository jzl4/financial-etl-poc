import sys
import os

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# /home/ubuntu/financial-etl-poc/dags
current_folder = os.path.dirname(__file__)
# /home/ubuntu/financial-etl-poc/
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)

from scripts.ingest_yfinance import main as ingest_yfinance_main

def log_failure(context):
    with open("/opt/airflow/logs/failure_alerts.log", "a") as f:
        f.write(f"[{datetime.now()}] DAG {context['dag'].dag_id} failed on task {context['task_instance'].task_id}\n")

default_args = {
    "owner": "airflow",
    "on_failure_callback": log_failure,
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(seconds = 30)
}

with DAG(
    dag_id = "ingest_yfinance_daily",
    default_args = default_args,
    description = "Extracts daily closing prices from yahoo finance API and inserts into tbl_api_payloads_yfinance_daily",
    schedule_interval = "0 18 * * 1-5",
    start_date = datetime(2024, 4, 28),
    catchup = False,
    tags = ["yfinance", "ETL"]
) as dag:
    
    run_ingest_yfinance = PythonOperator(
        task_id = "run_ingest_yfinance",
        python_callable = ingest_yfinance_main
    )

    run_ingest_yfinance
