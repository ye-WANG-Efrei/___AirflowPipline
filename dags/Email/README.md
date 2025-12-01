## Airflow DAG
#### 文件目录
```txt
dags/
  email_msg_to_eml_dag.py        # DAG 主文件（你要看最多的）
  Email/
    __init__.py                  # 空文件，标记为包
    config.py                    # S3 bucket / 路径配置
    extract_from_s3.py           # Extract：S3 → /tmp/*.msg
    msg2eml_lib.py               # Transform：.msg → .eml（调用你的库）
    load_to_s3.py                # Load：/tmp/*.eml → S3

```

### 数据传输
1. 不能用xcom_push 传大数据
Airflow 的 XCom 机制：  
- 默认把数据 序列化（pickle）后写入数据库  
- SQLite/Postgres/MySQL 都有限制

- Airflow 自身也限制 XCom 存的东西不应该超过几十 KB

- 超过大小会报错：
ValueError: XCom value too large...

更糟糕的是：
Airflow WebUI 会把 XCom 展示在网页里，你推一个几十 MB 的字节流进去，UI 直接卡死。  
所以：

- ❌不要把 msg 文件内容（bytes）作为 XCom 推送
- ❌ 不要 push 文件的二进制流
- ❌ 不要 push 大的 JSON 或列表
- ❌ 不要 push“需要持久化”的任何实际数据

#### *永远只通过 XCom 传 路径、key、文件名、标识符 ，不要传内容。*


#### DAG 文件 —— 并行的 Extract / Transform / Load（多文件、多节点跑）

支持多文件并行（多“线程”效果）。  
- 用 TaskFlow @dag + @task
- 用 dynamic task mapping 的 .expand() 来并行处理一批 msg 文件
- 每个文件完整走：extract → transform → load
- Airflow 会自动把这些 task 分发到不同 worker / 进程

### DAG 主函数
```python
def msg_to_eml_etl_dag(
    file_keys: List[str] | None = None,
):
```
这是 DAG 的函数体。
Airflow 用它动态创建任务拓扑。  
参数：  
`file_keys`：允许用户在“触发DAG运行”时传一组 key  
例如：     
`file_keys=["a.msg", "b.msg"]`  那 Airflow 会自动批量并行处理。

#### Task 1 — get_file_keys
```python 
@task
def get_file_keys(conf_file_keys: List[str] | None) -> List[str]:
```

#### Task 2 — extract_task
```python 
@task
def extract_task(file_key: str) -> str:
    return extract_msg_from_s3(file_key)

```  
功能：
从 S3 流式下载 .msg → /tmp/xxx.msg
返回本地路径。

#### Task 3 — transform_task
```python 
@task
def extract_task(file_key: str) -> str:
    return extract_msg_from_s3(file_key)

```  
功能：
本地 .msg → .eml。

#### Task 4 — load_task
```python 
@task
def extract_task(file_key: str) -> str:
    return extract_msg_from_s3(file_key)

```  
功能：
上传 .eml 到 S3
并且可能用 original_file_key 决定 prefix 或命名

#### Task 5 — cleanup_task
```python 
@task
def cleanup_task(paths: List[str]) -> None:


```  
功能：
传入路径列表（.msg 和 .eml），删除本地文件，防止 /tmp 堆满。