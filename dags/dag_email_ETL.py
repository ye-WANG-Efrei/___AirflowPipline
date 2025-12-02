#dag_email_ETL.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from Email.extract_from_s3 import extract_msg_from_s3




with DAG(
    dag_id="extract_from_s3_dag",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
) as dag:

    extract_task = PythonOperator(
        task_id="extract",
        python_callable=extract_from_s3,
    )
