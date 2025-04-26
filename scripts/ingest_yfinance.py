# Standard library imports
import sys
import os

current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)

import argparse
from datetime import datetime, date
from typing import List, Tuple, Optional
from datetime import timedelta

# Third-party libraries.  Hard to believe pandas is "third-party", but it's true because we need to pip-install it
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

# Local project imports
from utils.db_utils import *

def get_cli_args() -> argparse.Namespace:
    """
    Get command line arguments for start_date, end_date, and tickers
    """
    parser = argparse.ArgumentParser(description="Arguments for ingesting Yahoo Finance data, including start_date, end_date, and tickers.")
    parser.add_argument("--start_date", type = str, help = "Start date of yahoo finance data extraction in YYYY-MM-DD format")
    parser.add_argument("--end_date", type = str, help = "End date of yahoo finance data extraction in YYYY-MM-DD format")
    parser.add_argument("--tickers", nargs = "*", help = "List of tickers, separated by spaces. If not provided, will use default tickers from tbl_yfinance_tickers table")

    return parser.parse_args()

def validate_date_format_and_not_in_future_or_return_today(date_str: Optional[str], date_name: str) -> date:
    """
    If user provides no date, default to today's date. Otherwise, validate format and ensure not future.
    """
    if date_str is None:
        output_date = datetime.today().date()
    else:
        try:
            output_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if output_date > date.today():
                print(f"{date_name} cannot be in the future")
                sys.exit(1)
        except ValueError:
            print(f"{date_name} needs to be in YYYY-MM-DD format")
            sys.exit(1)
    
    return output_date

def validate_start_date_less_than_or_equal_end_date(start_date: date, end_date: date) -> Tuple[date, date]:
    
    if end_date < start_date:
        print("End date must be greater than, or equal to, start date.")
        sys.exit(1)
    
    return start_date, end_date

def validate_list_of_tickers_or_fetch_from_db(tickers: Optional[List[str]], cursor: Cursor) -> List[str]:

    # TODO: In the future, I could cache the fetched tickers for faster dev cycles, so I don't need to query DB every time
    if tickers is None:

        print("User provided no tickers via CLI, so getting active tickers from tbl_yfinance_tickers")

        active_ticker_query = """
        SELECT ticker FROM tbl_yfinance_tickers WHERE is_active = TRUE;
        """
        
        df_active_tickers = sql_query_as_df(active_ticker_query, cursor)
        tickers = df_active_tickers["ticker"].tolist()

    if not tickers:
        print("Error: User provided no tickers, but tbl_yfinance_tickers contains no active tickers either")
        sys.exit(1)

    return tickers

def validate_cli_args(args: argparse.Namespace, cursor: Cursor) -> Tuple[date, date, List[str]]:
    """
    Validate args from CLI: start_date, end_date, and list of tickers.  Also, enforces that start_end <= end_date
    """
    start_date = validate_date_format_and_not_in_future_or_return_today(args.start_date, "Start date")
    end_date = validate_date_format_and_not_in_future_or_return_today(args.end_date, "End date")
  
    start_date, end_date = validate_start_date_less_than_or_equal_end_date(start_date, end_date)

    tickers = validate_list_of_tickers_or_fetch_from_db(args.tickers, cursor)
    
    return start_date, end_date, tickers

def download_yfinance_data(start_date: date, end_date: date, tickers: List[str]) -> pd.DataFrame:
    """
    Extracts end-of-day closing prices for list of tickers from yahoo finance API
    Yahoo finance API excludes end_date's prices, so adjust the end_date to include end_date's data
    """
    adjusted_end_date = end_date + timedelta(days = 1)

    df_yahoo_finance_api = yf.download(
        tickers = tickers, 
        start = start_date, 
        end = adjusted_end_date, 
        period = "1d", 
        group_by = "ticker")
    
    return df_yahoo_finance_api

def insert_yfinance_payload_by_date():
    # Placeholder for inserting data into RDS
    pass

def main():

    # Load .env file, which is required for connecting to AWS RDS
    load_dotenv()
    conn, cursor = connect_to_rds()

    # Get arguments from command line
    args = get_cli_args()
    start_date, end_date, tickers = validate_cli_args(args, cursor)

    df_yahoo_finance_api = download_yfinance_data(start_date, end_date, tickers)
    print(df_yahoo_finance_api.head(n = 5))

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()