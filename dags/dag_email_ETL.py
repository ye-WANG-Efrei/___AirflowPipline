from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from datetime import datetime, timedelta
from Email.extract_from_s3 import extract_from_s3
import logging



logger =logging.getLogger(__name__)

BUCKET = "airflow-dags-bucket-20251121"
PREFIX = "dags/"   # 你监听的目录

def log_task_state(taks_name:str, state :str):
    logger.info("=====Task [%s] Status: %s ====", taks_name, state)


def process_file(file_key: str):
    """ETL 主流程（file_key 自动从 Sensor 得到）"""
    log_task_state("run_etl", "START")

    logger.info("Downloading file from S3: %s", file_key)
    try:
        local_path = extract_from_s3(file_key)
        logger.info("File downloaded to tmp path: %s", local_path)
    except Exception as e:
        logger.info("File downloaded Failed: %s", e)

    log_task_state("run_etl", "END")
    return local_path

def test_s3_login():
    """测试s3是否能正常访问"""
    try:
        s3=  boto.client("s3")
        s3.list_buckets()
        logger.info("S3 login SUCCESS.")
    except Exception as e:
        logger.error("S3 login FAILED: %s", str(e))
        raise

with DAG(
    dag_id="email_s3_auto_etl",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@once",   # 也可以改成定时
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=3)
    }
) as dag:

    # Step 1: 监听某个 S3 prefix（自动发现新文件）
    wait_for_file = S3KeySensor(
        task_id="wait_for_s3_file",
        bucket_name=BUCKET,
        bucket_key=f"{PREFIX}*.msg",  # 改成匹配 .msg 文件
        wildcard_match=True,
        poke_interval=60,
        timeout=300,  # 
    )
    # wait_for_file = S3KeySensor(
    #     task_id="wait_for_s3_file",
    #     bucket_name=BUCKET,
    #     bucket_key=f"{PREFIX}*",
    #     wildcard_match=True,
    #     poke_interval=60,
    #     timeout=5,
    # )

    # Step 2: 获取 sensor 发现的文件 key
    def pick_file_key(**context):
        """从 S3PrefixSensor 提供的 keys 列表里取一个最新文件"""
        log_task_state("pick_file", "START")

        files = context["ti"].xcom_pull(task_ids="wait_for_s3_file")
        logger.info("Files detected by S3KeySensor: %s", files)
        if not files:
            raise ValueError("No files detected in prefix!")

        file_key = files[0]  # 取第一个
        logger.info("Selected file: %s", file_key)
        log_task_state("pick_file", "END")
        return file_key

    choose_file = PythonOperator(
        task_id="choose_file",
        python_callable=pick_file_key,
        provide_context=True,
    )

    # Step 3: ETL — 你的 extract_from_s3 就能用了
    run_etl = PythonOperator(
        task_id="run_etl",
        python_callable=lambda file_key: process_file(file_key),
        op_kwargs={
            "file_key": "{{ ti.xcom_pull(task_ids='choose_file') }}"
        },
    )

    wait_for_file >> choose_file >> run_etl
