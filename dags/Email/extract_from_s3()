import boto3
from .config import S3_BUCKET, LOCAL_RAW_MSG_PATH

def extract_from_s3(**context):
    """
    从 S3 下载一封 .msg 邮件，原样保存到本地 raw_email.msg。
    DAG 触发时必须通过 dag_run.conf 传入 file_key。
    """
    # 从 DAG 触发参数中获取 S3 对象 key
    file_key = context["dag_run"].conf.get("file_key")
    if not file_key:
        raise ValueError(
            "file_key not provided. 请在触发 DAG 时通过 conf 传入："
            "{'file_key': 'path/to/email.msg'}"
        )

    print(f"Downloading .msg from s3://{S3_BUCKET}/{file_key}")

    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=S3_BUCKET, Key=file_key)
    body = obj["Body"]

    # ⚠️ 二进制流式下载，不解析、不修改内容
    with open(LOCAL_RAW_MSG_PATH, "wb") as f:
        for chunk in iter(lambda: body.read(1024 * 1024), b""):  # 1MB 一块
            f.write(chunk)

    print(f".msg file saved to {LOCAL_RAW_MSG_PATH}")

    # 把 file_key 推到 XCom，后面 delete_source_data 要用
    context["ti"].xcom_push(key="file_key", value=file_key)
