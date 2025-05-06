import os
import sys

# /home/ubuntu/financial-etl-poc/this_folder
current_folder = os.path.dirname(__file__)
# /home/ubuntu/financial-etl-poc/
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)
# For loading credentials from .env under financial-etl-poc
dotenv_path = os.path.join(project_root_folder, ".env")

import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from dotenv import load_dotenv

from db_utils import connect_to_rds

def create_tbl_api_payloads_yfinance_daily(cursor: Cursor, conn: Connection) -> None:
    """
    Create the tbl_api_payloads_yfinance_daily table if it doesn't already exist.
    """

    create_tbl_api_payloads_yfinance_daily_query = """
    CREATE TABLE IF NOT EXISTS tbl_api_payloads_yfinance_daily (
        business_date DATE NOT NULL,
        ingestion_timestamp TIMESTAMPTZ DEFAULT NOW(),
        raw_payload JSONB,
        PRIMARY KEY (business_date)
    );
    """

    cursor.execute(create_tbl_api_payloads_yfinance_daily_query)
    conn.commit()

    print("Ran create_tbl_api_payloads_yfinance_daily")

def create_tbl_yfinance_prices_daily_staging(cursor: Cursor, conn: Connection) -> None:
    """
    Create the tbl_yfinance_prices_daily_staging table if it doesn't already exist
    """

    create_tbl_yfinance_prices_daily_staging_query = """
    CREATE TABLE IF NOT EXISTS tbl_yfinance_prices_daily_staging (
        ticker TEXT NOT NULL,
        business_date DATE NOT NULL,
        price_open NUMERIC,
        price_low NUMERIC,
        price_high NUMERIC,
        price_close NUMERIC,
        volume NUMERIC,
        created_timestamp TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (ticker, business_date)
    );
    """

    cursor.execute(create_tbl_yfinance_prices_daily_staging_query)
    conn.commit()

    print("Ran create_tbl_yfinance_prices_daily_staging")

def create_tbl_yfinance_tickers(cursor: Cursor, conn: Connection) -> None:
    """
    Create the tbl_yfinance_tickers table if it doesn't already exist
    """

    create_tbl_yfinance_tickers_query = """
    CREATE TABLE IF NOT EXISTS tbl_yfinance_tickers (
        ticker TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        updated_timestamp TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (ticker)
    );
    """

    cursor.execute(create_tbl_yfinance_tickers_query)
    conn.commit()

    print("Ran create_tbl_yfinance_tickers")

def main_setup_tables():

    # Load .env file, which is required for connecting to AWS RDS
    load_dotenv(dotenv_path)
    conn, cursor = connect_to_rds()

    create_tbl_api_payloads_yfinance_daily(cursor, conn)
    create_tbl_yfinance_prices_daily_staging(cursor, conn)
    create_tbl_yfinance_tickers(cursor, conn) 

if __name__ == "__main__":
    main_setup_tables()
