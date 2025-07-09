import os
import sys
import argparse
import pandas as pd
from typing import Optional, Tuple, List
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# Required to import other modules from this project
current_folder = os.path.dirname(__file__)
project_root_path = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_path)
# Import functionalities from other modules in this project
from utils.db_utils import *
from utils.datetime_utils import get_today_est

# Global variables
today = get_today_est()

def get_correlation_cli_args() -> argparse.Namespace:

    # Call constructor to create ArgumentParser instance
    parser = argparse.ArgumentParser(description = "TODO")

    # asset_1: str, asset_2: str, min_end_date: date, max_end_date: date, n_months: int = 3
    parser.add_argument("--tickers", nargs = "*", help = "Two tickers, separated by spaces, whose returns we will calculate the correlation of")
    parser.add_argument("--start_date", type = str, default = today, help = "Start date of rolling correlation calculation. First point in correlation time series will be correlation of 2 assets during (start_date - n_months, start_date). Default is today")
    parser.add_argument("--end_date", type = str, default = today, help = "End date of rolling correlation calculation. Last point in correlation time series will be correlation of 2 assets during (end_date - n_months, end_date). Default is today")
    parser.add_argument("--n_months", type = int, default = 3, help = "Number of months used in correlation calculation. Default is 3")

    # Ask ArgumentParser instance to parse the CLI inputs and create a Namespace object containing fields such as: .min_end_date, .max_end_date, etc.
    parsed_args = parser.parse_args()
    return parsed_args

def validate_pair_of_tickers(tickers: List[str]) -> Tuple[str, str]:
    # Given a list of tickers, such as ["SPY", "GLD"], need to convert into a tuple of alphabetically-ordered strings
    # TODO: Check that length of tickers list is exactly 2
    # TODO: Check that two tickers are not equal, i.e. - we cannot have ["SPY", "SPY"]
    # TODO: We need to sort these in alphabetical order such that asset_1 < asset_2 in alphabetical terms, i.e. - (asset_1, asest_2) = (GLD, SPY), instead of (asset_1, asset_2) = (SPY, GLD)
    # TODO: Should we also check that these tickers are active in the DB? (Optional)
    pass

# TODO: Run this on both start_date and end_date
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

# TODO: Verify that this is an integer, and if none is given, default to value 3 (3 months)
def validate_n_months(n_months: Optional[int]) -> int:
    pass

# TODO: Create a function that pulls returns for these two assets between min_start_date and max_start_date
# TODO: It should give user a warning if the min(business_date of 2 assets) > min_end_date, i.e. - "You asked for data going back to 2020-01, but actually these two assets only have data going back to 2021-05", or if max(business_date of 2 assets) < max_end_date, i.e. - "You asked for data as recent as today, but these assets only have data going up to 2 months ago"
def get_asset_returns(asset_1: str, asset_2: str, min_start_date: date, max_end_date: date) -> pd.DataFrame:
    pass

# TODO: This needs to iterate backwards, from max(business_date) to min(business_date) + n_months, like this: correlation between (max_business_date - n_months, max_business_date), then (max_business_date - n_months - 1, max_business_date - 1), etc.
def calc_rolling_correlation(asset_1: str, asset_2: str, n_months: int) -> pd.DataFrame:
    pass

# TODO: Insert into dataframe table.  This table will hook up with end-back (FastAPI) and then later front-end (React) to create a correlation dashboard
def insert_rolling_correlation_to_db(df_rolling_correlations: pd.DataFrame):
    pass

def main_cli():
    
    args = get_correlation_cli_args()
    asset_1, asset_2 = validate_pair_of_tickers(args.tickers)

    min_end_date = validate_date_format_and_not_in_future_or_return_today(args.start_date, "start_date")
    max_end_date = validate_date_format_and_not_in_future_or_return_today(args.end_date, "end_date")
    min_end_date, max_end_date = validate_start_date_less_than_or_equal_end_date(min_end_date, max_end_date)

    n_months = validate_n_months(args.n_months)
    min_start_date = min_end_date - relativedelta(months = n_months)

    df_returns = get_asset_returns(asset_1, asset_2, min_start_date, max_end_date)
    df_rolling_correlations = calc_rolling_correlation(asset_1, asset_2, n_months)
    insert_rolling_correlation_to_db(df_rolling_correlations)