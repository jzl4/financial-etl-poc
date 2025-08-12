#!/bin/bash

# To use this script, run: source start_airflow.sh

# This is required because .env file with RDS credentials is located in financial-etl-poc/ folder, instead of the financial-etl-poc/airflow/ folder where docker-compose.yaml needs the credentials to build the container
# Specifically this line in docker-compose.yaml needs to be resolved: AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://${rds_username}:${rds_password}@${rds_host}:${rds_port}/${rds_dbname} BEFORE running "docker compose"
    # Reads contents of file .env as multi-line output
    # xargs converts into single space-separated line: rds_host=mydb.example.com rds_port=5432 rds_username=admin...
    # export $(...) sets environmental variables in the shell: export rds_host=... rds_port=...
echo "Loading RDS login credentials from .env to resolve AIRFLOW__DATABASE__SQL_ALCHEMY_CONN in docker-compose.yaml"
export $(cat ../.env | xargs)

# Build Docker images (uses Dockerfile.airflow)
echo "Running: docker compose build..."
docker compose build

# Initialize Airflow DB (runs airflow db init inside a persistent container)
echo "Running: docker compose run airflow-init..."
docker compose run airflow-init

# Start up all Airflow services (webserver, scheduler)
echo "Running: docker compose up..."
docker compose up