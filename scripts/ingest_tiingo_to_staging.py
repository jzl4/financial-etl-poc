# Standard library imports
import sys
import os
import argparse
from typing import Tuple, List, Optional
from datetime import datetime, date
import pandas as pd
import requests

# Required to import other modules from this project, in folders such as utils/ or notebooks/
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)
# Import functionalities from other modules in this project
from utils.db_utils import *
from utils.general_utils import get_today_est
from psycopg2 import extras

# Load .env file for AWS RDS login credentials and Tiingo API token
dotenv_path = os.path.join(project_root_folder, ".env")
from dotenv import load_dotenv
tiingo_api_token = os.getenv("tiingo_api_token")

today = get_today_est()

def get_cli_args() -> argparse.Namespace:
    """
    Get CLI arguments start_date, end_date, and list of tickers, for extracting end-of-day data from Tiingo API
    """

    # Create the ArgumentParser instance and define the expected CLI arguments
    parser = argparse.ArgumentParser(description = "Get CLI arguments start_date, end_date, and list of tickers, for extracting end-of-day data from Tiingo API. Example 1: python ingest_tiingo_to_staging.py -s '2025-05-29' -e '2025-05-30' -t 'SPY GLD' | Example 2: python ingest_tiingo_to_staging.py --start_date '2025-05-29' --end_date '2025-05-30' --tickers 'SPY GLD'")
    parser.add_argument("-s", "--start_date", type = str, default = today, help = "Start date in YYYY-MM-DD format")
    parser.add_argument("-e", "--end_date", type = str, default = today, help = "End date in YYYY-MM-DD format")
    parser.add_argument("-t", "--tickers", nargs = "*", help = "List of tickers, separated by spaces. If not provided, will use default tickers from tbl_active_tickers table")

    # Parse the CLI inputs and return a Namespace object containing: parsed_args.start_date, etc.
    parsed_args = parser.parse_args()
    return parsed_args

def validate_date_format_and_not_in_future_or_return_today(date_str: str, start_or_end_date: str) -> date:
    """
    Verify that provided date has YYYY-MM-DD format and is not in the future
    """
    try:
        verified_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"{start_or_end_date} must be in YYYY-MM-DD format")
        sys.exit(1)

    if verified_date > today:
        print(f"{start_or_end_date} cannot be in the future")
        sys.exit(1)    

    return verified_date

def validate_start_date_less_than_or_equal_end_date(start_date: date, end_date: date) -> Tuple[date, date]:
    """
    Verify that start_date is less than or equal to end_date
    """
    if start_date > end_date:
        print(f"Start date {start_date} should not be greater than end date {end_date}")
        sys.exit(1)
    
    return start_date, end_date

def validate_list_of_tickers_or_fetch_from_db(tickers: Optional[List[str]], cursor: Cursor) -> List[str]:
    """
    If end user does not provide a list of tickers via CLI, then try to get list of active tickers from tbl_active_tickers. If even that is empty, exit program with explanation that no active tickers exist
    """
    if tickers is None:

        print("User provided no tickers in CLI, so getting active tickers from tbl_active_tickers")
        
        active_tickers_query = """
        SELECT ticker FROM tbl_active_tickers WHERE is_active = TRUE;
        """

        df_active_tickers = sql_query_as_df(active_tickers_query, cursor)
        tickers = df_active_tickers["ticker"].tolist()

    if not tickers:
        print("Error: tbl_active_tickers contains no active tickers. Please update tbl_active_tickers to include active tickers")
        sys.exit(1)

    return tickers

def validate_cli_args(args: argparse.Namespace, cursor: Cursor) -> Tuple[date, date, List[str]]:
    """
    Validate args from CLI: start_date, end_date, and list of tickers.  Also, enforces that start_end <= end_date
    """
    start_date = validate_date_format_and_not_in_future_or_return_today(args.start_date, "start_date")
    end_date = validate_date_format_and_not_in_future_or_return_today(args.end_date, "end_date")
  
    start_date, end_date = validate_start_date_less_than_or_equal_end_date(start_date, end_date)

    tickers = validate_list_of_tickers_or_fetch_from_db(args.tickers, cursor)
    
    return start_date, end_date, tickers

def download_tiingo_data(start_date: date, end_date: date, tickers: List[str]) -> pd.DataFrame:
    """
    Downloads closing prices from Tiingo between start_date and end_date for list of tickers, and returns result as DataFrame
    """

    dfs = []

    for ticker in tickers:
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"

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
    df = download_tiingo_data(start_date, end_date, tickers)
    df = format_tiingo_data(df)
    insert_into_tiingo_daily_staging(df, cursor, conn)

def main_cli():
    """
    Main function for manual run via CLI. Useful for backfilling historical prices for multiple securites and/or correcting data
    """
    # Load AWS RDS credentials from .env and connect to database
    load_dotenv(dotenv_path)
    conn, cursor = connect_to_rds()

    args = get_cli_args()
    start_date, end_date, user_provided_tickers = validate_cli_args(args, cursor)
    main_shared(start_date, end_date, user_provided_tickers, conn, cursor)

def main_airflow():
    """
    Main function used by Airflow to run daily EOD job, to pull that day's closing stock prices
    """
    # Load AWS RDS credentials from .env and connect to database
    load_dotenv(dotenv_path)
    conn, cursor = connect_to_rds()

    active_tickers = validate_list_of_tickers_or_fetch_from_db(None, cursor)
    main_shared(today, today, active_tickers, conn, cursor)
  
if __name__ == "__main__":
    # By default, this driver should run the CLI version. Airflow job will be invoked in DAGs
    main_cli()