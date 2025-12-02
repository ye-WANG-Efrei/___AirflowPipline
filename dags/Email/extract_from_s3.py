# Email/extract_from_s3.py
import logging
from pathlib import Path

import boto3
from airflow.operators.python import get_current_context


from Email.config import RAW_BUCKET, LOCAL_TMP_DIR

#创建一个日志记录器，名字是当前模块名（Email.extract_from_s3）。
#后面 logger.info(...) 就用这个对象打印日志，Airflow 日志里能看到。
logger = logging.getLogger(__name__)

#创建一个 S3 客户端。
#之后用 s3.download_fileobj(...) 通过这个客户端从 S3 拉文件。
#所有 AWS 访问权限，靠容器里的环境变量 / IAM 角色来决定。
s3 = boto3.client("s3")


def extract_from_s3(file_key: str) -> str:
    """
    从 S3 流式下载 .msg 到本地 /tmp，返回本地路径。
    只下载，不解析、不修改内容。
    """
    #从 Airflow 拿当前运行的上下文（dict）
    context = get_current_context()



    #从 context["params"] 里找 bucket 这个参数：
    #如果 DAG/Task 运行时在 params={"bucket": "xxx"} 里指定了，就用这个 bucket。
    #如果没指定，就 fallback 到默认的 RAW_BUCKET（配置文件里的环境变量 / 默认值）。
    bucket = context["params"].get("bucket", RAW_BUCKET)



    #把 S3 的 key 按 / 分割，取最后一段当文件名。
    """
    举例：
    file_key = "raw_msg/2025/11/mail_001.msg"
    file_key.split("/") = ["raw_msg", "2025", "11", "mail_001.msg"]
    取 [-1] → "mail_001.msg"
    """
    local_filename = file_key.split("/")[-1]



    #/ 运算符在 Path 里就是拼路径：结果是 Path("/tmp/mail_001.msg")
    local_path = LOCAL_TMP_DIR / local_filename


    logger.info("Start downloading from S3: bucket=%s, key=%s → %s", bucket, file_key, local_path)

    #wb二进制写
    """
    关键一步：从 S3 下载文件，流式写入本地文件。
    Bucket=bucket:S3 bucket 名。
    Key=file_key:S3 对象 key(路径)。
    Fileobj=f:把下载的内容写进这个打开的文件句柄，而不是先塞在内存里。
    重点：
    download_fileobj 是 流式下载 ，避免一次性把整个文件读进内存。
    """
    with open(local_path, "wb") as f:
        s3.download_fileobj(
            Bucket=bucket,
            Key=file_key,
            Fileobj=f,
        )

    logger.info("Finished downloading: %s", local_path)
    return str(local_path)
