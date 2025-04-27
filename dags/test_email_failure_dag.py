from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "email": ["joe.zhou.lu@gmail.com"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}

def fail_task():
    raise Exception("This task fails intentionally for email alert testing!")

with DAG(
    dag_id="test_email_failure_dag",
    default_args=default_args,
    description="A simple DAG to test email alerts",
    schedule_interval=None,
    start_date=datetime(2024, 4, 27),
    catchup=False,
    tags=["test"],
) as dag:

    task_that_fails = PythonOperator(
        task_id="intentional_failure",
        python_callable=fail_task,
    )
