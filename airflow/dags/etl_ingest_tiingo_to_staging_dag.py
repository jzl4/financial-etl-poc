import os
import sys

from airflow import DAG

from datetime import datetime, timedelta

current_folder = os.path.dirname(__file__)
# TODO: Check if I need to go up two layers to reach the base level of the repo, because this current dag is inside of financial-etl-poc/airflow/dags folder
project_root_folder = os.path.abspath(os.path.join(current_folder, "../.."))
sys.path.append(project_root_folder)

from etl_drivers.etl_ingest_tiingo_to_staging import main_airflow as ingest_tiingo_to_staging_main_airflow

def log_failure(context):
    

default_args = {
    "owner": "joe_lu",
    "on_failure_callback": log_failure,
    "depends_on_past":False,
    "retries": 1,
    "retry_delay": timedelta(seconds = 30)
}