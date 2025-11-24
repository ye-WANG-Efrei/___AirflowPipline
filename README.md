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