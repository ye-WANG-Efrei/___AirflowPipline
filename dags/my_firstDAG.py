# dags/email_msg_to_eml_dag.py
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

from airflow.decorators import dag, task

from Email.extract_from_s3 import extract_msg_from_s3
from Email.transform_msg2eml import convert_to_eml
from Email.load_to_s3 import upload_eml_to_s3
from Email.config import RAW_BUCKET


@dag(
    dag_id="email_msg_to_eml_etl",
    start_date=datetime(2025, 1, 1),
    schedule=None,          # 手动 / API 触发
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
    concurrency=32,         # 本 DAG 内最多同时 32 个 task
    max_active_runs=8,      # 同时最多 8 个 DAG run
    tags=["email", "msg2eml", "etl"],
)
def msg_to_eml_etl_dag(
    file_keys: List[str] | None = None,
):
    """
    支持批量文件并行处理的 ETL DAG：

    1）从 S3 流式下载 .msg 到 /tmp
    2）msg → eml
    3）上传 .eml 到 S3

    并行由 Airflow Executor 决定，多 worker 时会分布到多节点。
    """

    # 1. 决定要处理哪些 S3 key
    @task
    def get_file_keys(conf_file_keys: List[str] | None) -> List[str]:
        """
        优先从 dag_run.conf["file_keys"] 里取；
        如果没给，就从 params["file_key"] 里取单个；
        也可以在这里实现“自动从某个 prefix 列出最近 N 个文件”的逻辑。
        """
        from airflow.decorators import get_current_context

        context = get_current_context()
        dag_run = context.get("dag_run")

        # 优先：API / UI 触发时传的 conf：{"file_keys": ["a.msg", "b.msg", ...]}
        if dag_run and dag_run.conf and "file_keys" in dag_run.conf:
            return dag_run.conf["file_keys"]

        # 退而求其次：conf 里只有单个 file_key
        if dag_run and dag_run.conf and "file_key" in dag_run.conf:
            return [dag_run.conf["file_key"]]

        # 再退一步：用 params["file_key"]（DAG 参数）
        file_key_param = context["params"].get("file_key")
        if file_keys is not None:
            # 从 dag 函数参数传进来的（例如 future: Airflow UI 参数化）
            return file_keys
        if file_key_param:
            return [file_key_param]

        raise ValueError(
            "No file_keys provided. Use dag_run.conf['file_keys'] or conf['file_key'] or params['file_key']."
        )

    # 2. Extract：S3 → /tmp（对每个 file_key 并行执行）
    @task
    def extract_task(file_key: str) -> str:
        return extract_msg_from_s3(file_key)

    # 3. Transform：/tmp .msg → /tmp .eml
    @task
    def transform_task(msg_local_path: str) -> str:
        return convert_to_eml(msg_local_path)

    # 4. Load：/tmp .eml → S3
    @task
    def load_task(eml_local_path: str, original_file_key: str) -> str:
        return upload_eml_to_s3(eml_local_path, original_file_key)

    # 5. 清理本地文件（可选）
    @task
    def cleanup_task(paths: List[str]) -> None:
        import os
        import logging

        logger = logging.getLogger(__name__)
        for p in paths:
            try:
                os.remove(p)
                logger.info("Removed temp file: %s", p)
            except FileNotFoundError:
                logger.warning("Temp file not found for cleanup: %s", p)
            except Exception as e:
                logger.error("Failed to remove temp file %s: %s", p, e)

    # ======== DAG 拓扑（重点）========

    # 得到要处理的所有 file_keys（list[str]）
    keys = get_file_keys(file_keys)

    # 并行 Extract：每个 file_key 对应一个 task instance
    msg_paths = extract_task.expand(file_key=keys)

    # 并行 Transform：每个 msg_path 转成 eml_path
    eml_paths = transform_task.expand(msg_local_path=msg_paths)

    # 并行 Load：每个 eml_path 上传到 S3
    uploaded_keys = load_task.expand(
        eml_local_path=eml_paths,
        original_file_key=keys,
    )

    # 清理本地 /tmp 文件（把 msg + eml 都清理掉）
    cleanup_task(msg_paths + eml_paths) >> uploaded_keys  # 确保上传完成后再清理


# DAG 实例化（Airflow 需要这一句）
dag = msg_to_eml_etl_dag()

