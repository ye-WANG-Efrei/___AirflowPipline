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
