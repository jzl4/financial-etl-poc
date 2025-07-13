# financial-etl-poc

This is a proof-of-concept (POC) project that demonstrates an end-to-end financial data pipeline architecture. It integrates **data engineering**, **cloud computing**, **quantitative finance**, and **software engineering best practices** to process, transform, and serve financial insights in a production-ready format.

## 🌐 Project Overview

The project ingests stock price data from the **Tiingo API**, applies **financial transformations**, and stores results in a PostgreSQL database. The pipeline supports both historical backfills and automated daily updates via **Dockerized Airflow** and will soon be orchestrated with **AWS Fargate**. Final outputs will be exposed via a **FastAPI** back-end and **React** front-end dashboard.

---

## 💡 Skills Showcased

### 🔬 Data Science & Engineering
- Python-based ETL scripts
- PostgreSQL: bronze (raw) → silver (cleaned) → gold (adjusted) table architecture
- Modular data pipelines with CLI and Airflow DAG orchestration
- Virtual environments for local development
- Docker containers for portability and productionization
- Airflow for pipeline scheduling
- FastAPI for RESTful endpoint creation
- React front-end for interactive dashboards (upcoming)

### ☁️ Cloud Infrastructure
- **AWS EC2**: development and orchestration
- **AWS RDS (PostgreSQL)**: persistent storage
- **AWS Fargate**: container-based task execution (upcoming)

### 📈 Quantitative Finance
- Adjustment of historical stock returns for **dividends** and **stock splits**
- Calculation of **rolling correlations** between assets
- Upcoming: 
  - Momentum and mean-reversion signals
  - Minimum-variance portfolio optimization
  - Risk metrics for portfolio construction
  - Deep learning applied to time series
  - GenAI applied to headlines/fundamental data

---

## 🔁 Current ETL Workflow

| Stage | Description |
|-------|-------------|
| **1. Ingestion** | Pulls raw price/volume data from the Tiingo API and stores it in a staging table (`tbl_api_payloads_tiingo_daily`) using a Python CLI tool. Supports historical backfill and daily automation via Airflow. |
| **2. Transformation** | Converts staging data into clean, adjusted price series (silver → gold tables) accounting for dividends and splits. Supports historical and daily runs. |
| **3. Feature Engineering** | Calculates **rolling correlation** between two tickers for a given time window. Results are stored in `tbl_rolling_correlations`. |
| **4. Automation (upcoming)** | Dockerized Airflow will be deployed to **AWS Fargate** for fully-managed, autoscaled daily ETL runs. |
| **5. API + Dashboard (upcoming)** | A REST endpoint via FastAPI will expose correlation results, consumed by a hosted React dashboard. |
| **6. Modeling (future)** | Modules to compute signals (momentum, stat arb), build portfolios, manage risk, and run ML/DL models on financial time series. |

---

## 🧰 Folder Structure
financial-etl-poc/

├── airflow/ # Dockerized Airflow stack: docker-compose.yml, Dockerfile, requirements.txt, DAGs

├── api_rolling_correlation/ # FastAPI code to expose rolling correlation results via REST API

├── archive-yahoo-finance/ # Deprecated drivers from earlier Yahoo Finance implementation; replaced by Tiingo

├── data-quality/ # (Planned) Data validation rules: positive prices, correct splits, duplicate detection

├── etl-drivers/ # ETL drivers for:
│ # - Tiingo → staging
│ # - staging → adjusted prod table
│ # - rolling correlation calculator

├── notebooks/ # Jupyter notebooks for experimentation, development, and testing

├── sql_script/ # SQL scripts for table setup, transformation, or manual debugging

├── utils/ # Shared utilities for:
│ # - datetime conversions
│ # - AWS RDS connections
│ # - parsing & validating CLI args

├── .env # Environment variables (excluded from version control)

└── requirements.txt # Python dependencies

---

## 🚧 Upcoming Features

- **🧠 Quantitative Modeling:**
  - Momentum, mean reversion, statistical arbitrage strategies
  - Minimum-variance and risk-parity portfolio construction
  - Time series forecasting with deep learning (e.g., LSTM, TCN, Transformer)
  - GenAI analysis of financial headlines, 10-Ks, or earnings transcripts

- **🛠 Software Engineering Enhancements:**
  - Logging and monitoring of pipeline events
  - Unit/integration tests
  - CI/CD for deployments (GitHub Actions or AWS CodePipeline)
  - Exception handling and retry logic

- **📊 Dashboard:**
  - Fully interactive correlation visualization
  - Inputs: ticker 1, ticker 2, time window
  - Real-time response from FastAPI + PostgreSQL
  - Hosted via AWS or other cloud provider

---

## ✅ Highlights

- Modular architecture supporting **reproducibility**, **scalability**, and **maintainability**
- Full control over both **backfilling** and **real-time daily updates**
- Clear distinction between **raw**, **clean**, and **adjusted** data layers
- Designed for extensibility into both **machine learning pipelines** and **portfolio analytics**