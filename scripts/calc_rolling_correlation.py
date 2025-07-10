import os
import sys
import argparse
import pandas as pd
from typing import Optional, Tuple, List
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from psycopg2 import extras

# Required to import other modules from this project
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)
# Import functionalities from other modules in this project
from utils.db_utils import *
from utils.datetime_utils import get_today_est

# Load .env file for AWS RDS login credentials and Tiingo API token
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root_folder, ".env")
load_dotenv(dotenv_path)

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
    """
    Given a list of tickers, such as ["SPY", "GLD"], need to convert into a tuple of alphabetically-ordered strings
    """

    # Cannot compute the correlation between (x,y,z) for example. Need exactly two assets
    if len(tickers) != 2:
        print("Error: To calculate the rolling correlation, we must have exactly 2 tickers")
        sys.exit(1)

    # Check that two tickers are not equal, i.e. - we cannot have ["SPY", "SPY"]
    if tickers[0] == tickers[1]:
        print("Error: Two tickers provided are the same security, which will trivially generate a correlation of 1. Please enter 2 different securities")

    # TODO: Should we also check that these tickers are active in the DB? (Optional)
    return tuple(sorted(tickers))

def validate_date_format_and_not_in_future_or_return_today(date_str: Optional[str], start_or_end_date: str) -> date:
    """
    Verify that provided date has YYYY-MM-DD format and is not in the future
    """
    if date_str is None:
        return today
    
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

def validate_n_months(n_months: Optional[int]) -> int:
    
    if n_months is None:
        return 3
    
    if isinstance(n_months, int) and n_months > 0:
        return n_months
    else:
        print("n_months must be a positive integer, such as 1, 3, etc.")
        sys.exit(1)

def get_daily_asset_returns(asset_1: str, asset_2: str, min_start_date: date, max_end_date: date) -> pd.DataFrame:

    returns_query = f"""
    select
        asset_1.business_date,
        asset_1.adj_close_pct_chg as asset_1_returns,
        asset_2.adj_close_pct_chg as asset_2_returns
    from tbl_daily_prod asset_1 join tbl_daily_prod asset_2
        on asset_1.business_date = asset_2.business_date
    where
        asset_1.ticker = '{asset_1}' and asset_1.business_date between '{min_start_date}' and '{max_end_date}'
        and asset_2.ticker = '{asset_2}' and asset_2.business_date between '{min_start_date}' and '{max_end_date}'
    order by asset_1.business_date;
    """

    conn, cursor = connect_to_rds()
    df_daily_returns = sql_query_as_df(returns_query, cursor)

    if df_daily_returns.empty:
        print(f"Error: Returns data for {asset_1} and {asset_2} between {min_start_date} and {max_end_date} is empty in tbl_daily_prod")
        sys.exit(1)

    min_returns_date = min(df_daily_returns["business_date"])
    max_returns_date = max(df_daily_returns["business_date"])

    if min_returns_date > min_start_date:
        print(f"Warning: Your input requires returns data going back to {min_start_date}, but returns data only goes back to {min_returns_date}")
    
    if max_returns_date > max_end_date:
        print(f"Warning: Your input requires returns data going up to {max_end_date}, but returns data only goes up to {max_end_date}")
    
    conn.close()

    return asset_1, asset_2, df_daily_returns

def calc_rolling_correlation(ticker_1: str, ticker_2: str, df_daily_returns: pd.DataFrame, n_months: int) -> pd.DataFrame:

    business_dates = df_daily_returns["business_date"]
    min_business_date = min(business_dates)

    business_dates_to_correlations = []

    for end_date in business_dates:

        # Given the end_date of the correlation calculation, get n_months before
        n_months_before_end_date = end_date - relativedelta(months = n_months)

        # Check that n_months before that end_date is actually among business_dates
        if n_months_before_end_date >= min_business_date:

            # If so, get the most recent business_date that is less than, or equal to, n_months_before_end_date => our start_date
            start_date = max([d for d in business_dates if d <= n_months_before_end_date])

            # Filter returns only to those between our start_date and end_date and calculate the correlation in this n_month window
            df_between_start_end_date = df_daily_returns.loc[
                (start_date <= df_daily_returns["business_date"]) & (df_daily_returns["business_date"] <= end_date)
            ]

            corr = df_between_start_end_date["asset_1_returns"].corr(df_between_start_end_date["asset_2_returns"])
            
            business_date_to_correlation = {
                "ticker_1": ticker_1,
                "ticker_2": ticker_2,
                "n_months": n_months,
                "business_date": end_date,
                "correlation": corr
            }

            business_dates_to_correlations.append(business_date_to_correlation)

        # If we are here, it means that end_date is too far back, and n_months before end_date falls off business_dates range. We won't have n_months of historical data to compute correlation for this end_date, so skip to next end_date
        else:
            continue
    
    # TODO: If I will just directly insert into the PostgreSQL database after this, there is no need to convert into a Pandas dataframe, because I will just convert into a list of dict before insertion
    df_correlation_time_series = pd.DataFrame(business_dates_to_correlations)

    return df_correlation_time_series
    
def insert_rolling_correlation_to_db(df_correlation_time_series: pd.DataFrame):

    # Ensure the correct columns are in the correct order
    df_correlation_time_series_ordered = df_correlation_time_series[
        ["ticker_1", "ticker_2", "n_months", "business_date", "correlation"]
    ]

    data = list(df_correlation_time_series_ordered.itertuples(index = False, name = None))

    query = """
    INSERT INTO tbl_rolling_correlations (
        ticker_1,
        ticker_2,
        n_months,
        business_date,
        correlation
    )
    VALUES %s
    ON CONFLICT (ticker_1, ticker_2, n_months, business_date) DO UPDATE SET
        correlation = EXCLUDED.correlation,
        updated_datetime = now()
    """

    conn, cursor = connect_to_rds()

    try:
        extras.execute_values(cursor, query, data)
        conn.commit()
        print(f"Bulked inserted/updated {len(df_correlation_time_series_ordered)} rows into tbl_rolling_correlations")
    except Exception as e:
        print(f"Error happened during insertion: {e}")
        conn.rollback()
    finally:
        conn.close()  

def main_cli():
    
    args = get_correlation_cli_args()
    asset_1, asset_2 = validate_pair_of_tickers(args.tickers)

    min_end_date = validate_date_format_and_not_in_future_or_return_today(args.start_date, "start_date")
    max_end_date = validate_date_format_and_not_in_future_or_return_today(args.end_date, "end_date")
    min_end_date, max_end_date = validate_start_date_less_than_or_equal_end_date(min_end_date, max_end_date)

    n_months = validate_n_months(args.n_months)
    min_start_date = min_end_date - relativedelta(months = n_months)

    asset_1, asset_2, df_daily_returns = get_daily_asset_returns(asset_1, asset_2, min_start_date, max_end_date)
    df_rolling_correlations = calc_rolling_correlation(asset_1, asset_2, df_daily_returns, n_months)
    insert_rolling_correlation_to_db(df_rolling_correlations)

if __name__ == "__main__":
    # By default, this driver should run the CLI version. Airflow job will be invoked in DAGs
    main_cli()