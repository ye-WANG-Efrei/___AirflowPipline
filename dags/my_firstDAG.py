from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

def hello():
    print("Airflow is working!")

with DAG(
    dag_id="first_dag",
    description="My first Airflow DAG",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["test"],
) as dag:

    task_hello = PythonOperator(
        task_id="say_hello",
        python_callable=hello,
    )
