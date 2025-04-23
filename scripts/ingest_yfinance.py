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

def validate_cli_args(args: argparse.Namespace) -> Tuple[Optional[date], Optional[date], List[str]]:
    """
    Verify that start_date and end_date are YYYY-MM-DD format, end_date is greater than start_date, and end_date isn't in the future
    TODO: Finish validate_cli_args function with Optional args
    """
    try:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    except ValueError:
        print("Start date and end date must be in YYYY-MM-DD format.")
        sys.exit(1)
    
    if end_date < start_date:
        print("End date must be greater than, or equal to, start date.")
        sys.exit(1)

    if end_date > date.today():
        # TODO: Handle case where end_date == today() but market hasn't closed yet (before 4 PM EST)
        print("End date must be less than or equal to today.")
        sys.exit(1)

    tickers = args.tickers
    
    return start_date, end_date, tickers
    

def main():
    # Get arguments from command line
    args = get_cli_args()
    start_date, end_date, tickers = validate_cli_args(args)

    # There should be code where if CLI doesn't provide start and end dates, or tickers, use defaults





if __name__ == "__main__":
    main()