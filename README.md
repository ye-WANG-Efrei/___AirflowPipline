# ___AirflowPipline

### EC2 上运行：

- 使用 官方 Airflow 镜像（FROM apache/airflow:2.9.3-python3.9
- docker-compose：webserver + scheduler + postgres
- sync_dags.sh：从 GitHub 自动同步 DAG

起一个EC2持续运行airflow，同时在github上更新DATA和DAGs，同步到ec2上的airflow。
确保：
- 首次 EC2 部署无需手动安装任何东西
- 所有依赖、脚本、配置都固化进 Dockerfile
- GitHub actions 可直接触发 ECR 镜像构建
- EC2 启动时只需 docker pull + docker-compose up 即可恢复完整系统 保证HA。

### 结构：

```
aws-airflow-pipeline/
├─ dags/
│  ├─ __init__.py
│  ├─ github_trigger_pipeline.py      # 你的主要 DAG
│  └─ utils/
│     └─ common.py                    # 复用代码
├─ docker/
│  ├─ Dockerfile                      # Airflow 镜像
│  └─ requirements.txt                # 额外 Python 包
├─ docker-compose.yml                 # 在 EC2 上跑 Airflow
├─ scripts/
│  ├─ sync_dags.sh                    # EC2 上同步 S3 DAG
│  └─ init_airflow.sh                 # 初始化用户 / 连接等
├─ .github/
│  └─ workflows/
│     └─ deploy.yml                   # GitHub Actions
├─ README.md

```
**EC2**
```
sudo chown -R ec2-user:ec2-user dags logs plugins
```
**Airflow**
```
sudo chown -R 50000:50000 dags logs plugins
docker compose restart
```
## EC2文件结构
```
/home/ec2-user/airflow/
    ├── dags/
    ├── logs/
    ├── docker-compose.yml
    └── Dockerfile

```
## EC2
安装Docker 
```python
sudo yum update -y
sudo yum install -y docker        # AL2023 使用此命令安装 Docker。:contentReference[oaicite:1]{index=1}
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user  # 将 ec2-user 加入 docker 组，以便可以不 sudo 使用 docker。:contentReference[oaicite:2]{index=2}

```

Git—安装和拉取
```powershell
sudo yum install git -y
cd ~   # 或你希望放项目的目录
git clone https://github.com/ye-WANG-Efrei/___AirflowPipline.git
cd ___AirflowPipline

```

Doker compose-plugin RPM 这一步是为创建相对应的文件夹和授予权限
```Powershell
sudo mkdir -p /usr/libexec/docker/cli-plugins/
sudo curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
     -o /usr/libexec/docker/cli-plugins/docker-compose
sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose

#如果遇到了 docker-compose is not a docker command 是因为docker-compose 和docker compose的语法版本，安装 docker compose plugin
sudo mkdir -p /usr/libexec/docker/cli-plugins/
sudo curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-linux-x86_64 \
  -o /usr/libexec/docker/cli-plugins/docker-compose
sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose

```

第一次启动  
初始化 Airflow 必须的数据库表、权限系统、用户、连接、角色等一次性动作。
不执行它，Airflow 根本启动不了。
```
docker-compose up airflow-init
```

ValueError: Fernet key must be 32 url-safe base64-encoded bytes.  
是因为 Airflow 要加密：
- Connections 的密码
- Variables 中加密字段
- XCom 加密数据（如果启用）  
没有正确的 Fernet Key，Airflow 初始化时无法创建默认连接
```scss
create_default_connections()
```
解决方案：  
生成一个合法的 Fernet Key，并写入 .env 或 docker-compose.yml  
1. 在 EC2 上运行:
```bash
python3 - <<EOF
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
EOF
```
会得到类似这样的值：
```
6ByFhG8p8zjfhcVBtVgO1UZ5JT8F7HZhLPkP47bE5Vw=
```
2. 在.env文见中写进去
```bash
nano .env
```
此时.env文件应该是：
```
AIRFLOW_UID=1000 #但是这里也有可能是50000，因为有些配置如果你不给root（UID=50000）会被拒绝
AIRFLOW_GID=0
FERNET_KEY=6ByFhG8p8zjfhcVBtVgO1UZ5JT8F7HZhLPkP47bE5Vw=
```
保存退出：
Ctrl + O → Enter → Ctrl + X  

3. 更新 docker-compose.yml 让它加载 FERNET_KEY
```yml
environment:
  AIRFLOW__CORE__FERNET_KEY: ${FERNET_KEY}
```

4. 重新初始化 Airflow DB
重新清理容器：
```
docker-compose down -v
```
重新开始：
```
docker-compose up airflow-init
```
如果 init 成功（没有报错）  
正常输出：
```
airflow-init-1 exited with code 0
```
查看容器启动：
```powershell
docker-compose ps
```
显示只有airflowpipline-postgres-1已启动：
```
airflowpipline-postgres-1   Up

```
最后启动所有容器
```powershell
docker-compose up -d
```
再查看状态：
```powershell
docker-compose ps
```
会显示：
```
NAME                                 IMAGE                              COMMAND                  SERVICE             CREATED         STATUS         PORTS
airflowpipline-airflow-scheduler-1   apache/airflow:2.10.2-python3.12   "/usr/bin/dumb-init …"   airflow-scheduler   2 minutes ago   Up 2 minutes   8080/tcp
airflowpipline-airflow-webserver-1   apache/airflow:2.10.2-python3.12   "/usr/bin/dumb-init …"   airflow-webserver   2 minutes ago   Up 2 minutes   0.0.0.0:8080->8080/tcp, :::8080->8080/tcp
airflowpipline-postgres-1            postgres:15                        "docker-entrypoint.s…"   postgres            6 minutes ago   Up 6 minutes   5432/tcp
```
### 实例宕机重启 docker服务 Airflow容器自动启动  
让 Docker 服务随系统启动  
执行下面两条命令即可（只需一次）：  
```powershell
sudo systemctl enable docker
sudo systemctl start docker
```  
验证：  
```
sudo systemctl status docker
```  
看到 `Loaded: enabled` 和 `Active: active (running)` 就表示开机会自动启动。  
Airflow 容器自动启动
在你的 docker-compose.yml 文件里，给每个服务加上：
```
restart: always
```

举例：
```yml
services:
  airflow-webserver:
    image: apache/airflow:2.10.2-python3.12
    restart: always
    ports:
      - "8080:8080"
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
    depends_on:
      - airflow-scheduler
      - postgres
```
这样，只要 Docker 启动，容器就会：自动启动  
如果崩溃会自动重启
## BUGs 
#### 1. 控件起不来，一直起来就shutdown！
```pgsql
database system is ready to accept connections
LOG: received fast shutdown request
```
缺少依赖，造成如下反应：   
scheduler 比 postgres 启动早  
scheduler 连接失败  
scheduler 挂  
webserver 也挂  
postgres 被 docker 停掉  
整组全部 Exited  
修改 docker-compose.yml  
把 postgres 段替换成：
```yml
postgres:
  image: postgres:15
  restart: always
  environment:
    POSTGRES_USER: airflow
    POSTGRES_PASSWORD: airflow
    POSTGRES_DB: airflow
  volumes:
    - postgres-db-volume:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "airflow"]
    interval: 10s
    retries: 5
    start_period: 10s
``` 
  
并在 scheduler / webserver 都加：
```yml
depends_on:
  postgres:
    condition: service_healthy
```
#### 2. Airflow UI一直转圈，但是服务都起来了
日志一直出现
```less
Worker (pid:113) was sent SIGTERM!
```
这不是正常退出，这是 内核 OOM killer 在杀 worker。  
**原因：🚨 你的 EC2 内存不够 → Gunicorn worker 被 OOM 杀死 → 页面永远加载不出来**
```bash
free -h
```
会看到 `swap` 为0。
由于我是是 2GB 内存的机器：  
Airflow 2.x 组件总共吃：
- Airflow webserver ~ 450MB
- Airflow scheduler ~ 400MB
- Postgres ~ 150MB
- Docker 程序开销 ~ 200MB
- 容器基础 OS overhead ~ 300MB  
合计超过 1.5GB，很容易爆 2GB RAM → OOM killer 直接杀掉 worker → UI 转圈。
所以我们利用SWAP用了一部分*硬盘*来做*内存*，避免内存溢出被OOM

代码：  
1.创建 4GB swap 文件
这个命令会在你的系统根目录 ``` / ``` 下创建一个文件：  
👉 ```/swapfile```大小 =  4096MB（4GB）
```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
```
2. 设置正确的权限 **(swapfile 必须让 只有 root 能访问)**
```bash
sudo chmod 600 /swapfile
```
3. 把这个文件标记为 swap 区域
```bash
sudo mkswap /swapfile
```
mkswap 的作用就是告诉内核：  

👉 “这个 ```/swapfile ```文件现在不是普通文件了，我要把它当 swap 用。”

4. 启用 swap
```bash
sudo swapon /swapfile
```
让内核真正开始使用：

👉 ```/swapfile ```作为虚拟内存

#### 3. docker compose down 之后重启有文件名字冲突
1. ```docker ps -a```发现 ```init``` 和```scheduler```文件还在，但是状态时```create```而不是```up```  

我先查了是不是我yml文件写错了，然后看是不是有多个容器，又看了收不是又多个yml文件，发现都没有问题  

最后发现就是之前OOM这两个服务挂起来了。最后直接强行删除这两个服务，重新```up```解决了
```bash
docker rm -f airflowpipline-airflow-init-1
docker rm -f airflowpipline-airflow-scheduler-1
```
#### 4.Airflow 没有权限写 /opt/airflow/logs 导致Init起不来
docker-compose.yml 完全正确，
Airflow 失败的原因现在只剩 宿主机 logs 残留权限错误。  
错误：
```swift
PermissionError: [Errno 13] Permission denied: '/opt/airflow/logs/scheduler/2025-12-02'
```
因为：
第一次初始化失败的时候:
1. scheduler 尝试写日志失败

2. 容器内部创建了部分目录（root 权限）

3. 导致宿主机 logs 同步成 root-owned

之后：

- 再怎么 chmod logs 都没用（子目录 root-owned）

- Airflow 用户（UID=1000）无权写

- init 永远失败

只有清空 logs 才能完全修复。
解决方案就是：**删除 logs 目录**  
**这是 Airflow 官方文档也给出的修复方法。**

执行：
```bash
sudo rm -rf logs
mkdir logs
sudo chmod -R 777 logs
```
最终启动步骤：
```bash
docker compose down --volumes
sudo rm -rf logs
mkdir logs
chmod -R 777 logs
docker compose up airflow-init
```
然后你会看到"
```bash
airflow-init ... done
```
