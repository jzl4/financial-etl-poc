import os
import sys
import argparse
from typing import Tuple, List, Optional
from datetime import datetime, date

# Required to import other modules from this project, in folders such as utils/ or notebooks/
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)
# Import functionalities from other modules in this project
from utils.db_utils import *
from utils.datetime_utils import get_today_est

# Global variables
conn, cursor = connect_to_rds()
today = get_today_est()

def get_etl_cli_args() -> argparse.Namespace:
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

def validate_etl_cli_args(args: argparse.Namespace, cursor: Cursor) -> Tuple[date, date, List[str]]:
    """
    Validate args from CLI: start_date, end_date, and list of tickers.  Also, enforces that start_end <= end_date
    """
    start_date = validate_date_format_and_not_in_future_or_return_today(args.start_date, "start_date")
    end_date = validate_date_format_and_not_in_future_or_return_today(args.end_date, "end_date")
  
    start_date, end_date = validate_start_date_less_than_or_equal_end_date(start_date, end_date)

    tickers = validate_list_of_tickers_or_fetch_from_db(args.tickers, cursor)
    
    return start_date, end_date, tickers