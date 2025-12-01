# Email/transform_msg2eml.py
import logging
from pathlib import Path
from Email.msg2eml_lib import load

logger = logging.getLogger(__name__)

def convert_to_eml(msg_path: str) -> str:
    """
    把本地 .msg 文件转换为 .eml 返回 .eml 本地路径。
    """

    msg_file = Path(msg_path)
    if not msg_file.exists():
        raise FileNotFoundError(f"MSG file does not exist: {msg_file}")

    eml_file = msg_file.with_suffix(".eml")

    logger.info("Start converting MSG to EML: %s → %s", msg_file, eml_file)

    with open(msg_file, "rb") as f:         # ← 二进制打开
        msg = load(f)
    with open(eml_file, "wb") as f: # 存入eml格式
         f.write(msg.as_bytes())

    logger.info("Finished converting MSG to EML: %s", eml_file)
    return str(eml_file)
