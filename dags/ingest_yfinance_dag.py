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

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["Joe.Zhou.Lu@gmail.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes = 5)
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
