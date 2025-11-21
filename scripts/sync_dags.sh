#!/bin/bash
set -e

# S3 bucket 存 DAG 的路径
S3_DAG_BUCKET="s3://your-airflow-dag-bucket/dags"

LOCAL_DAG_DIR="/home/ec2-user/aws-airflow-pipeline/dags"

echo "$(date) - Syncing DAGs from S3..."
aws s3 sync "$S3_DAG_BUCKET" "$LOCAL_DAG_DIR"

echo "$(date) - DAG sync done."