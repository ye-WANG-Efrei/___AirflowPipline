FROM apache/airflow:2.9.3-python3.9

# Install extra OS packages if needed
USER root
RUN apt-get update && apt-get install -y \
    nano \
    git \
    curl \
    unzip \
    && apt-get clean

# Create Airflow directories inside the image
RUN mkdir -p /opt/airflow/dags \
             /opt/airflow/logs \
             /opt/airflow/plugins \
             /opt/airflow/scripts

# Copy your DAG pipeline (GitHub will override this)
COPY dags /opt/airflow/dags
COPY plugins /opt/airflow/plugins


# Optional: copy any init scripts
COPY scripts /opt/airflow/scripts
RUN chmod +x /opt/airflow/scripts/* || true

USER airflow
# 复制 requirements
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt