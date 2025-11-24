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

### 部署方式：

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

## 目录结构

```
pass
```

## 现有代码可以做到什么？

- **容器化环境**：`docker-compose.yml` 已经定义了 `webserver`、`scheduler`、`postgres`，并且默认挂载 `./dags`、`./logs`、`./plugins` 到容器中，适合在 EC2 上直接 `docker compose up` 启动 Airflow。
- **自定义镜像基础**：`docker/Dockerfile` 以官方 Airflow 2.9.3 Python 3.9 镜像为基础，安装了 `git`、`curl` 等工具，并支持通过 `docker/requirements.txt` 安装额外 Python 依赖（目前包含 `boto3` 和 `pandas`）。
- **DAG 同步脚本**：`scripts/sync_dags.sh` 会将指定的 S3 路径同步到 EC2 上的本地 `dags/` 目录，可用于从一个 S3 bucket 下发 DAG 到 Airflow。需要在脚本中把 `S3_DAG_BUCKET` 替换成真实 bucket。
- **GitHub Actions 占位**：`README` 和目录结构示例预留了 `.github/workflows/deploy.yml`，但仓库里还没有实际的 workflow。可以在此基础上添加流水线来构建/推送镜像或同步 DAG。

## 现有代码做不到的部分（需要补充）

- **没有实际的 DAG 代码**：仓库中缺少 `dags/` 目录和处理逻辑。当前镜像和 compose 只提供运行 Airflow 的框架，没有定义任何任务去检测 `data/` 目录或处理文件。
- **未配置数据检测流程**：代码中没有监听 GitHub `data/` 目录变化的机制，也没有 Sensors/Triggers 去感知 S3 或本地文件新增。
- **S3 桶名未配置**：`scripts/sync_dags.sh` 使用占位 bucket 路径，与你的 `airflow-dags-bucket-20251121`、`airflow-output-bucket-20251121` 无直接关联，需要手动替换。
- **缺少 GitHub Actions 自动化**：没有 workflow 去检测仓库变更、构建镜像或将 `data/` 目录与 S3 同步，从而触发 EC2 上的 Airflow。

## 要实现“GitHub data 目录有新文件 → EC2 Airflow 处理 → 结果存 S3”的改造思路

1. **补充 DAG 与依赖**
   - 在仓库添加 `dags/` 目录，创建一个 DAG（例如 `data_file_pipeline.py`），包含：
     - Sensor：
       - 若选择 **S3 作为中转**，用 `S3KeySensor`/`S3PrefixSensor` 监听 `airflow-dags-bucket-20251121` 中的 `data/` 前缀；
       - 若直接监听本地挂载目录，使用 `FileSensor` 监听宿主机挂载的 `./data`（需在 `docker-compose.yml` 增加卷挂载 `./data:/opt/airflow/data`）。
     - Processing Task：用 `PythonOperator`/`BashOperator` 读取新文件并处理。
     - Upload Task：用 `S3Hook`/`boto3` 把结果写入 `airflow-output-bucket-20251121` 指定前缀。
   - 在 `docker/requirements.txt` 中添加 DAG 所需的库（如 `apache-airflow-providers-amazon`）。

2. **同步 data/ 与 DAG 到 EC2/S3**
   - 在 GitHub Actions 新增 workflow（位于 `.github/workflows/deploy.yml`），在仓库 `data/` 或 `dags/` 变更时执行：
     - 将 `dags/` 同步到 `airflow-dags-bucket-20251121/dags/`；
     - 将 `data/` 同步到同一 bucket 下的 `data/`（供 Sensor 监听）或直接通过 SSH/rsync 同步到 EC2 本地挂载目录。
   - 在 EC2 上运行 `scripts/sync_dags.sh`（把 `S3_DAG_BUCKET` 改成 `s3://airflow-dags-bucket-20251121/dags`）定时/开机同步 DAG。

3. **更新 docker-compose 配置**
   - 添加 `./data:/opt/airflow/data` 卷挂载，如果 DAG 要监听本地文件。
   - 在 `.env` 中配置 AWS 访问密钥或使用 EC2 实例角色，以便 DAG 中的 `S3Hook` 和同步脚本可以访问 `airflow-dags-bucket-20251121` 与 `airflow-output-bucket-20251121`。

4. **Airflow 连接与变量**
   - 在 Airflow UI 或通过环境变量预置 `aws_default` 连接（或自定义连接 ID），包含区域和凭证/角色。
   - 在 DAG 中用同一连接 ID 访问两个 bucket，任务写结果到 `s3://airflow-output-bucket-20251121/{prefix}/`。

5. **可选：镜像自动构建与推送**
   - 在 GitHub Actions 中添加构建步骤，打包 `docker/Dockerfile`，推送到 ECR。
   - EC2 上的 `docker-compose.yml` 可改为拉取自定义镜像标签，确保依赖和 DAG 一致。

6. **运行与监控**
   - EC2 启动后运行 `docker compose up -d` 启动 Airflow。
   - 确保 `scripts/sync_dags.sh` 定时执行（cron/systemd）或在容器启动时挂载执行，保证 DAG 与数据同步。
   - 在 Airflow UI 查看 DAG 状态，确认文件被感知、处理结果出现在 `airflow-output-bucket-20251121`。

通过以上补充，GitHub 上 `data/` 目录的新增文件可以被同步到 S3（或直接同步到 EC2 本地），由 Airflow DAG 监听并处理，最终结果写入指定的 S3 输出桶。
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

Doker compose-plugin RPM
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