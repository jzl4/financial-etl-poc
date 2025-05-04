from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def log_failure(context):
    with open("/opt/airflow/logs/failure_alerts.log", "a") as f:
        f.write(f"[{datetime.now()}] DAG {context['dag'].dag_id} failed on task {context['task_instance'].task_id}\n")

default_args = {
    "owner": "airflow",
    "on_failure_callback": log_failure,
    "depends_on_past": False,
    "retries": 0,
}

def fail_task():
    raise Exception("This task fails intentionally to verify that a failed DAG generates a log message")

with DAG(
    dag_id="test_failing_dag_gets_logged",
    default_args=default_args,
    description="A simple DAG to test failure logging to local log file",
    schedule_interval=None,
    start_date=datetime(2024, 4, 27),
    catchup=False,
    tags=["test"],
) as dag:

    task_that_fails = PythonOperator(
        task_id="intentional_failure",
        python_callable=fail_task,
    )
