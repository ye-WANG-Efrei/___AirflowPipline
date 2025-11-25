# transform_msg2eml.py
import os
from .config import LOCAL_RAW_MSG_PATH, LOCAL_EML_OUTPUT_PATH
from . import msg2eml_lib   # ← 这是你那份超大脚本，被我放成一个模块
import io

def transform_msg_to_eml(**context):
    """
    把 .msg 转成 .eml
    使用 msg2eml_lib.load() 处理 MAPI 格式，并输出标准 MIME .eml。
    """

    print(f"[transform] loading .msg from {LOCAL_RAW_MSG_PATH}")

    # 1) 以二进制读入 .msg 文件
    with open(LOCAL_RAW_MSG_PATH, "rb") as f:
        msg_binary = f.read()

    # 2) 重要：转换库 load() 需要一个可以 seek()/tell() 的二进制流
    bio = io.BytesIO(msg_binary)

    # 3) 调用 msg2eml 脚本（核心转换函数）
    mime_msg = msg2eml_lib.load(bio)

    # 4) 得到 MIME 对象后，写出 EML 文件
    print(f"[transform] writing .eml to {LOCAL_EML_OUTPUT_PATH}")
    with open(LOCAL_EML_OUTPUT_PATH, "wb") as f:
        f.write(mime_msg.as_bytes())

    print(f"[transform] .eml successfully created → {LOCAL_EML_OUTPUT_PATH}")

    # 5) 推送 XCom（其它 task 可以读取）
    context["ti"].xcom_push(key="eml_path", value=LOCAL_EML_OUTPUT_PATH)
