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

###  DAG 拓扑（最核心）
```python
keys = get_file_keys(file_keys)
```


① 拿到最终的 S3 key 列表，例如：  
```python
["a.msg", "b.msg", "c.msg"]
msg_paths = extract_task.expand(file_key=keys)
```

② 并行运行 Extract  
expand() = 动态任务映射    
等于生成多个任务：
- extract(a.msg)

- extract(b.msg)

- extract(c.msg)

返回值是：
["/tmp/a.msg", "/tmp/b.msg", "/tmp/c.msg"]

eml_paths = transform_task.expand(msg_local_path=msg_paths)


③ 并行 msg → eml
每个 msg_path 对应一个 transform 任务。

返回：
["/tmp/a.eml", "/tmp/b.eml", "/tmp/c.eml"]

uploaded_keys = load_task.expand(
    eml_local_path=eml_paths,
    original_file_key=keys,
)


④ 并行上传 eml
每个 eml_path + file_key 配对生成一个 upload task。

cleanup_task(msg_paths + eml_paths) >> uploaded_keys


⑤ 清理临时文件：
删除所有 /tmp/*.msg 和 /tmp/*.eml

>> uploaded_keys 表示：
cleanup 要 等 upload 全部完成之后 才能执行。

🔥 10. Airflow 需要实例化 DAG
dag = msg_to_eml_etl_dag()


没有这句 DAG 不会出现在 Airflow UI