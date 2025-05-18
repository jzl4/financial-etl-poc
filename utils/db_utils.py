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
from psycopg2.extras import execute_values  # Bulk insertion of Pandas dataframes
from psycopg2 import OperationalError, ProgrammingError, Error

def connect_to_rds() -> Tuple[Connection, Cursor]:
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