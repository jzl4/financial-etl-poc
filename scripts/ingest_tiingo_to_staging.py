# Standard library imports
import sys
import os
from datetime import date
import pandas as pd
import requests

# Required to import other modules from this project, in folders such as utils/ or notebooks/
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)
# Import functionalities from other modules in this project
from utils.db_utils import *
from utils.datetime_utils import get_today_est
from utils.argparse_utils import *
from psycopg2 import extras

# Load .env file for AWS RDS login credentials and Tiingo API token
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root_folder, ".env")
load_dotenv(dotenv_path)

# Global variables
conn, cursor = connect_to_rds() # Connect to AWS RDS
tiingo_api_token = os.getenv("tiingo_api_token")    # Token for using Tiingo API
today = get_today_est()

def download_tiingo_data(start_date: date, end_date: date, tickers: List[str]) -> pd.DataFrame:
    """
    Downloads closing prices from Tiingo between start_date and end_date for list of tickers, and returns result as DataFrame
    """

    dfs = []

    for ticker in tickers:
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"

        # TODO: remove token from params and move into headers. (Does Tiingo's doc suggest this as best practice?)
        # TODO: Use requests.Session() object for better performance, to reuse TCP connections.  Ex:
        #   session = requests.Session()
        #   response = session.get(url, headers, params)
        headers = {'Content-Type': 'application/json'}

        params = {
            "startDate": start_date,
            "endDate": end_date,
            "resampleFreq": "daily",
            "format": "json",
            "token": tiingo_api_token
        }

        # A single ticker could fail because the ticker is invalid
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()  # always good for catching HTTP errors
        except requests.exceptions.HTTPError as e:
            print(f"{e} due to invalid ticker {ticker}")
            continue    # Skip rest of lines in this iteration, and continue to next ticker in tickers

        # If no error, parse json into DataFrame
        list_of_dict = response.json()  # Each dict is price/volume/ratio data for one business_date
        df_payloads_for_one_ticker_between_start_end_dates = pd.DataFrame(list_of_dict)

        # A single ticker could fail because there was no price/volume data in that date range
        if df_payloads_for_one_ticker_between_start_end_dates.empty:
            print(f"No data between {start_date} and {end_date} for ticker {ticker}")
            continue    # Skip rest of lines in this iteration, and continue to next ticker in tickers

        # If ticker is valid and data is found between start and end date, append to dfs (list of df)
        df_payloads_for_one_ticker_between_start_end_dates["ticker"] = ticker
        dfs.append(df_payloads_for_one_ticker_between_start_end_dates)
    
    # If dfs is an empty list (all tickers return no data)
    if not dfs:
        print(f"Zero rows returned when downloading data from Tiingo between {start_date} and {end_date} for {tickers}")
        sys.exit(1)
    # Otherwise, stack the data from various tickers on top of each other
    else:
        df = pd.concat(dfs, axis = 0)

    print(f"{len(df)} rows returned from Tiingo API call")

    return df

def format_tiingo_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert dataframe of Tiingo API results into proper format, to match tbl_tiingo_daily_staging table format
    """
    
    # Convert datetime to date
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Rename columns
    df = df.rename(columns = {
        "date": "business_date",
        "adjClose": "adj_close",
        "adjHigh": "adj_high",
        "adjLow": "adj_low",
        "adjOpen": "adj_open",
        "adjVolume": "adj_volume",
        "divCash": "div_cash",
        "splitFactor": "split_factor"
    })

    # Reorder columns
    columns = [
        "ticker", "business_date",  # Primary keys
        "open", "low", "high", "close", "volume",   # Raw fields
        "adj_open", "adj_low", "adj_high", "adj_close", "adj_volume",   # Adjusted fields
        "div_cash", "split_factor"  # Corporate actions
    ]
    df = df[columns]

    return df

def insert_into_tiingo_daily_staging(df: pd.DataFrame, cursor, conn):
    """
    Inserts data into tbl_tiingo_daily_staging table
    """
    # How to convert from dataframe into list of tuples
    values = list(df.itertuples(index = False, name = None))

    # Use execute_values to insert into tbl_tiingo_daily_staging
    insert_query = """
    INSERT INTO tbl_tiingo_daily_staging (
        ticker, business_date, open, low, high, close, volume,
        adj_open, adj_low, adj_high, adj_close, adj_volume,
        div_cash, split_factor     
    )
    VALUES %s
    ON CONFLICT (ticker, business_date) DO UPDATE SET
        open = EXCLUDED.open,
        low = EXCLUDED.low,
        high = EXCLUDED.high,
        close = EXCLUDED.close,
        volume = EXCLUDED.volume,
        adj_open = EXCLUDED.adj_open,
        adj_low = EXCLUDED.adj_low,
        adj_high = EXCLUDED.adj_high,
        adj_close = EXCLUDED.adj_close,
        adj_volume = EXCLUDED.adj_volume,
        div_cash = EXCLUDED.div_cash,
        split_factor = EXCLUDED.split_factor,
        ingestion_ts = now(),
        source = 'Tiingo';        
    """

    extras.execute_values(cursor, insert_query, values)
    conn.commit()
    print(f"✅ Bulk inserted/updated {len(df)} rows into tbl_tiingo_daily_staging.")

def main_shared(start_date: date, end_date: date, tickers: List[str], conn: Connection, cursor: Cursor) -> None:
    """
    Shared functionality between main_cli() and main_airflow() to download Tiingo data, format it, and insert into staging table tbl_tiingo_daily_staging
    """
    df_tiingo_raw = download_tiingo_data(start_date, end_date, tickers)
    df_tiingo_formatted = format_tiingo_data(df_tiingo_raw)
    insert_into_tiingo_daily_staging(df_tiingo_formatted, cursor, conn)

def main_cli():
    """
    Main function for manual run via CLI. Useful for backfilling historical prices for multiple securites and/or correcting data
    """

    args = get_cli_args()
    start_date, end_date, user_provided_tickers = validate_cli_args(args, cursor)
    main_shared(start_date, end_date, user_provided_tickers, conn, cursor)

def main_airflow():
    """
    Main function used by Airflow to run daily EOD job, to pull that day's closing stock prices
    """

    active_tickers = validate_list_of_tickers_or_fetch_from_db(None, cursor)
    main_shared(today, today, active_tickers, conn, cursor)
  
if __name__ == "__main__":
    # By default, this driver should run the CLI version. Airflow job will be invoked in DAGs
    main_cli()