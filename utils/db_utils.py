# This module handles the connection to the PostgreSQL database on AWS RDS
# and provides utility functions for executing SQL queries and loading data into Pandas DataFrames.
 
# Crucial libraries
import os
import pandas as pd
 
# Data structures
from typing import Tuple, List, Dict, Set, Any

# Connect to AWS RDS PostgreSQL
import psycopg2
from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor
from psycopg2 import OperationalError, ProgrammingError, Error

def connect_to_rds(rds_host: str, rds_port: int, rds_dbname: str, rds_username: str, rds_password: str) -> Tuple[Connection, Cursor]:
    """
    Connect to the PostgreSQL database on AWS RDS and return the connection and cursor objects
    """

    # This assumes whichever downstream file that calls this function has already loaded the .env file
    # Access environment variables for connecting to my PostgreSQL database
    rds_host = os.getenv("rds_host")
    rds_port = int(os.getenv("rds_port"))
    rds_dbname = os.getenv("rds_dbname")
    rds_username = os.getenv("rds_username")
    rds_password = os.getenv("rds_password")

    try:
        conn = psycopg2.connect(
            host=rds_host,
            port=rds_port,
            dbname=rds_dbname,
            user=rds_username,
            password=rds_password
        )
        cursor = conn.cursor()
        print("✅ Connected successfully!")
        return conn, cursor

    except OperationalError as e:
        print("❌ Operational error (e.g. bad credentials, unreachable host):", e)
        raise
    except ProgrammingError as e:
        print("❌ Programming error (e.g. bad DB name or SQL syntax):", e)
        raise
    except Error as e:
        print("❌ psycopg2 general error:", e)
        raise
    except Exception as e:
        print("❌ Unknown error:", e)
        raise        

def sql_query_as_df(sql_query: str, cursor) -> pd.DataFrame:
    """
    Given a SQL query (string format), return the query's results as a Pandas dataframe
    """
    # Run query
    cursor.execute(sql_query)
    
    # Fetch all rows
    rows = cursor.fetchall()
    
    # Get column names from the cursor description
    column_names = [desc[0] for desc in cursor.description]
    
    # Convert to DataFrame
    df_from_query = pd.DataFrame(rows, columns=column_names)
    
    return df_from_query

# TODO: Should I keep this function in this file?  Or should I create a "setup tables" file and run that?
def create_tbl_api_payloads_yfinance_daily(cursor, conn) -> None:
    """
    Create the tbl_api_payloads_yfinance_daily table if it doesn't already exist.
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS tbl_api_payloads_yfinance_daily (
        business_date DATE NOT NULL,
        ingestion_timestamp TIMESTAMPTZ DEFAULT NOW(),
        raw_payload JSONB,
        PRIMARY KEY (business_date)
    );
    """
    cursor.execute(create_table_sql)
    conn.commit()

# TODO: Should I keep this function in this file?  Or should I create a "setup tables" file and run that?
def create_tbl_yfinance_prices_daily_staging(cursor, conn) -> None:
    create_price_table_staging = """
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

    cursor.execute(create_price_table_staging)
    conn.commit()