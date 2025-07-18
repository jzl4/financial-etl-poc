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

def create_tbl_active_tickers(cursor: Cursor, conn: Connection) -> None:
    """
    Create the tbl_active_tickers table if it doesn't already exist
    """

    create_tbl_active_tickers_query = """
    CREATE TABLE IF NOT EXISTS tbl_active_tickers (
        ticker TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        updated_timestamp TIMESTAMPTZ DEFAULT NOW(),
        PRIMARY KEY (ticker)
    );
    """

    cursor.execute(create_tbl_active_tickers_query)
    conn.commit()

    print("Ran create_tbl_active_tickers")

def create_tbl_tiingo_daily_staging(cursor: Cursor, conn: Connection) -> None:
    """
    Create the table tbl_tiingo_daily_staging, which is the staging/silver table for daily closing prices from Tiingo
    """

    create_tbl_tiingo_daily_staging_query = """
    CREATE TABLE IF NOT EXISTS tbl_tiingo_daily_staging (
        ticker TEXT NOT NULL,
        business_date DATE NOT NULL,
        open FLOAT,
        low FLOAT,
        high FLOAT,
        close FLOAT,
        volume BIGINT,
        adj_open FLOAT,
        adj_low FLOAT,
        adj_high FLOAT,
        adj_close FLOAT,
        adj_volume BIGINT,
        div_cash FLOAT,
        split_factor FLOAT,
        ingestion_ts TIMESTAMPTZ DEFAULT now(),
        source TEXT DEFAULT 'Tiingo',
        PRIMARY KEY (ticker, business_date)
    );
    """

    cursor.execute(create_tbl_tiingo_daily_staging_query)
    conn.commit()
    
    print("Ran create_tbl_tiingo_daily_staging")

def create_tbl_daily_prod(cursor: Cursor, conn: Connection) -> None:
    """
    Create the table tbl_daily_prod, which is the prod/gold table for daily prices from Tiingo (and possibly other future APIs)
    """

    create_tbl_daily_prod_query = """
    CREATE TABLE IF NOT EXISTS tbl_daily_prod (
        ticker TEXT NOT NULL,
        business_date DATE NOT NULL,
        adj_open FLOAT,
        adj_close FLOAT,
        adj_volume FLOAT,
        adj_open_pct_chg FLOAT,
        adj_close_pct_chg FLOAT,
        adj_volume_pct_chg FLOAT,
        ingestion_ts TIMESTAMPTZ DEFAULT now(),
        source TEXT DEFAULT 'Tiingo',
        PRIMARY KEY (ticker, business_date)
    );
    """

    cursor.execute(create_tbl_daily_prod_query)
    conn.commit()

    print("Ran create_tbl_daily_prod")

def create_tbl_rolling_correlations(cursor: Cursor, conn: Connection) -> None:
    """
    Create the table tbl_rolling_correlations, which is keyed on (ticker_1, ticker_2, n_months, business_date)
    """

    create_tbl_rolling_correlations_query = """
    CREATE TABLE IF NOT EXISTS tbl_rolling_correlations (
        ticker_1 TEXT NOT NULL,
        ticker_2 TEXT NOT NULL,
        n_months INT NOT NULL,
        business_date DATE NOT NULL,
        correlation FLOAT,
        updated_datetime TIMESTAMPTZ DEFAULT now(),
        PRIMARY KEY (ticker_1, ticker_2, n_months, business_date)
    );
    """

    cursor.execute(create_tbl_rolling_correlations_query)
    conn.commit()

    print("Ran create_tbl_rolling_correlations")

def main_setup_tables():

    # Load .env file, which is required for connecting to AWS RDS
    load_dotenv(dotenv_path)
    conn, cursor = connect_to_rds()

    create_tbl_active_tickers(cursor, conn)
    create_tbl_tiingo_daily_staging(cursor, conn)
    create_tbl_daily_prod(cursor, conn)
    create_tbl_rolling_correlations(cursor, conn)

if __name__ == "__main__":
    main_setup_tables()