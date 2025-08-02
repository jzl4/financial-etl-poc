#!/bin/bash
export $(cat ../.env | xargs)

# This is required because .env file with RDS credentials is located in financial-etl-poc/ folder, instead of the financial-etl-poc/airflow/ folder where docker-compose.yaml needs the credentials to build the container
    # Reads contents of file .env as multi-line output
    # xargs converts into single space-separated line: rds_host=mydb.example.com rds_port=5432 rds_username=admin...
    # export $(...) sets environmental variables in the shell: export rds_host=... rds_port=...

# To use: 
    # source load_rds_credentials_from_env_for_airflow.sh
    # docker compose build
    # docker compose up