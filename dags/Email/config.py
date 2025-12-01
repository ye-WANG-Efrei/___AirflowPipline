S3_BUCKET = "your-bucket"
S3_KEY_PREFIX = "airflow/data"

API_ENDPOINT = "https://dummyjson.com/products/1"

DB_CONN_ID = "my_postgres"   # 在 Airflow UI 创建 Conn

# Email/config.py
import os
from pathlib import Path

# 原始 .msg 文件所在的 S3 bucket / 前缀
#os.getenv()找环境变量，找不到名字为RAW_MSG_BUCKET的话取默认值"your-raw-msg-bucket"
RAW_BUCKET = os.getenv("RAW_MSG_BUCKET", "your-raw-msg-bucket")
RAW_PREFIX = os.getenv("RAW_MSG_PREFIX", "raw_msg/")

# 处理后 .eml 文件的 S3 bucket / 前缀
PROCESSED_BUCKET = os.getenv("PROCESSED_EML_BUCKET", RAW_BUCKET)
PROCESSED_PREFIX = os.getenv("PROCESSED_EML_PREFIX", "processed_eml/")


# 本地临时目录（容器内）
LOCAL_TMP_DIR = Path(os.getenv("LOCAL_TMP_DIR", "/tmp"))
LOCAL_TMP_DIR.mkdir(parents=True, exist_ok=True)
#在 docker-compose.yml 里引用这个 .env
'''
services:
  msg-converter:
    image: your-image-or-build
    env_file:
      - .env
    # 其他配置...
'''
