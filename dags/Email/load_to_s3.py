
# Email/load_to_s3.py
import logging
from pathlib import Path

import boto3
from airflow.decorators import get_current_context

from Email.config import PROCESSED_BUCKET, PROCESSED_PREFIX

logger = logging.getLogger(__name__)
s3 = boto3.client("s3")


def upload_eml_to_s3(eml_path: str, original_file_key: str) -> str:
    """
    把本地 .eml 上传到 S3 processed 路径，返回 S3 key。
    """
    context = get_current_context()
    bucket = context["params"].get("processed_bucket", PROCESSED_BUCKET)

    eml_file = Path(eml_path)
    if not eml_file.exists():
        raise FileNotFoundError(f"EML file does not exist: {eml_file}")

    # 保持和原 msg 文件类似的 key，只是改后缀 & 前缀
    original_name = original_file_key.split("/")[-1]
    eml_name = original_name.rsplit(".", 1)[0] + ".eml"
    s3_key = f"{PROCESSED_PREFIX}{eml_name}"

    logger.info("Uploading EML to S3: %s → s3://%s/%s", eml_file, bucket, s3_key)

    with open(eml_file, "rb") as f:
        s3.upload_fileobj(f, bucket, s3_key)

    logger.info("Finished uploading EML to S3: s3://%s/%s", bucket, s3_key)
    return s3_key
