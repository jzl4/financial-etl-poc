# 🧠 Financial ETL Pipeline: From Raw API to ML-Ready Gold Data

Welcome to my end-to-end **financial data pipeline** project, designed as both a **technical showcase** and a foundation for more advanced machine learning applications in the fintech domain.

This project demonstrates my ability to:
- Design modular and production-ready **ETL workflows**
- Orchestrate them using **Dockerized Apache Airflow**
- Transform noisy API payloads into structured, ML-ready datasets
- Prepare the system for downstream **machine learning**, API deployment, and front-end consumption

---

## ✅ Accomplishments So Far

### 🧱 Infrastructure
- **Dockerized Airflow Stack**: All components of the pipeline are containerized for portability and reproducibility.
- **PostgreSQL (AWS RDS)**: Centralized storage of all ETL data stages using a normalized schema.
- **AWS Integration**: Hosted components on EC2 and RDS, reflecting real-world cloud deployment scenarios.

### 🔁 Data Engineering Pipeline

| Layer       | Description                                                                                          |
|-------------|------------------------------------------------------------------------------------------------------|
| **Bronze**  | Raw JSON payloads from the [Yahoo Finance API](https://pypi.org/project/yfinance/) are ingested daily and stored in a structured format. |
| **Silver**  | Flattened time series tables containing core fields like open, high, low, close, and volume, keyed by `ticker` and `business_date`. |
| **Gold**    | Production-quality price data, adjusted for **stock splits and dividends**, suitable for backtesting and ML modeling. |

- Pipelines are modular, logged, and scheduled via Airflow DAGs for both **daily incremental updates** and **historical backfill**.

---

## 🚀 Vision & Roadmap

### 📊 Phase 1 — ML Training & Prediction
- Train machine learning models (e.g., linear regression, rolling correlation, or LSTM) on gold-layer data.
- Schedule training and prediction workflows using **Airflow-managed ML pipelines**, enabling daily inference runs.

### 🌐 Phase 2 — API Deployment
- Serve model predictions through a **FastAPI endpoint**, allowing real-time access for downstream consumers.

### 💻 Phase 3 — Front-End Dashboard
- Build a lightweight front-end (likely in **React** or **Streamlit**) to visualize:
  - Asset price trends  
  - Prediction outputs  
  - Model performance metrics

---

## 🧩 Technologies Used

- **Python**, **Pandas**, **SQLAlchemy**
- **Docker**, **Docker Compose**
- **Apache Airflow**
- **PostgreSQL (hosted on AWS RDS)**
- **AWS EC2**
- **yfinance** for data ingestion  
- *Planned:* **FastAPI**, **React.js**, **scikit-learn**, **dbt**

---

## 📁 Repo Structure (Simplified)

financial-etl-poc/

├── dags/ # Airflow DAG definitions

├── scripts/ # Python driver scripts (ingestion, transformation, etc.)

├── utils/ # Utility modules (e.g., db connectors)

├── docker/ # Dockerfiles and Airflow stack configs

├── notebook/ # Exploratory work & sanity checks

└── README.md