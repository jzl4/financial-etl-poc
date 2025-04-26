import yfinance as yf
import argparse
import sys
import pandas as pd

from datetime import datetime, date
from dotenv import load_dotenv
from typing import List, Tuple, Optional

from utils.db_utils import *

# Load .env file, which is required for connecting to AWS RDS
load_dotenv()

def download_yfinance_data(start_date: date, end_date: date, tickers: List[str]) -> pd.DataFrame:
    
    df_yahoo_finance_api = yf.download(
        tickers = tickers, 
        start = start_date, 
        end = end_date, 
        period = "1d", 
        group_by = "ticker")
    
    return df_yahoo_finance_api

def insert_yfinance_payload_by_date():
    # Placeholder for inserting data into RDS
    pass

def load_default_tickers(config_path):
    # Placeholder for loading default tickers from a configuration file
    pass

def get_cli_args() -> argparse.Namespace:
    """
    Get command line arguments for start_date, end_date, and tickers
    """
    parser = argparse.ArgumentParser(description="Arguments for ingesting Yahoo Finance data, including start_date, end_date, and tickers.")
    parser.add_argument("--start_date", type = "str", help = "Start date of yahoo finance data extraction in YYYY-MM-DD format")
    parser.add_argument("--end_date", type = "str", help = "End date of yahoo finance data extraction in YYYY-MM-DD format")
    parser.add_argument("--tickers", nargs = "+", help = "List of tickers, separated by spaces. If not provided, will use default tickers from tbl_yfinance_tickers table")

    return parser.parse_args()

def validate_list_of_tickers_or_fetch_from_db(tickers: Optional[List[str]]) -> List[str]:

    if tickers is None:
        # TODO: get list of tickers from PostgreSQL database: tbl_yfinance_tickers then
        pass

    return tickers

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

def validate_cli_args(args: argparse.Namespace) -> Tuple[date, date, List[str]]:
    """
    Validate args from CLI: start_date, end_date, and list of tickers.  Also, enforces that start_end <= end_date
    """
    start_date = validate_date_format_and_not_in_future_or_return_today(args.start_date, "Start date")
    end_date = validate_date_format_and_not_in_future_or_return_today(args.end_date, "End date")
  
    start_date, end_date = validate_start_date_less_than_or_equal_end_date(start_date, end_date)

    tickers = validate_list_of_tickers_or_fetch_from_db(args.tickers)
    
    return start_date, end_date, tickers
    

def main():
    # Get arguments from command line
    args = get_cli_args()
    start_date, end_date, tickers = validate_cli_args(args)

    # There should be code where if CLI doesn't provide start and end dates, or tickers, use defaults





if __name__ == "__main__":
    main()