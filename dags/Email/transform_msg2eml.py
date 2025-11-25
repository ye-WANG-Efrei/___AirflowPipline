import json
import extract_msg  # 需要在 requirements.txt 里安装
from .config import LOCAL_RAW_MSG_PATH, LOCAL_NORMALIZED_PATH

def transform_msg_to_normalized(**context):
    print(f"Parsing .msg file: {LOCAL_RAW_MSG_PATH}")

    msg = extract_msg.Message(LOCAL_RAW_MSG_PATH)

    normalized = {
        "subject": msg.subject,
        "sender": msg.sender,
        "sender_email": msg.sender_email,
        "to": msg.to,
        "cc": msg.cc,
        "date": msg.date,
        "body": msg.body,
        "attachments": [att.longFilename or att.shortFilename for att in msg.attachments],
    }

    print("Normalized email data:", normalized)

    with open(LOCAL_NORMALIZED_PATH, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    context["ti"].xcom_push(key="normalized_email", value=normalized)
