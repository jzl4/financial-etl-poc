import os
import sys
import argparse

import pandas as pd

# Required to import other modules from this project, in folders such as utils/ or notebooks/
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)
# Import functionalities from other modules in this project
from utils.db_utils import *
from utils.datetime_utils import get_today_est
from utils.argparse_utils import *

# Load .env file for AWS RDS login credentials
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root_folder, ".env")
load_dotenv(dotenv_path)

# Global variables
conn, cursor = connect_to_rds()
today = get_today_est()

# TODO: We need a function that pulls fields from staging table as a dataframe for a given stock/ticker, between start_date and end_date

def adj_corp_actions_for_one_stock(df_ticker: pd.DataFrame) -> pd.DataFrame:

    # TODO: I need to actually test this and validate that it works on Tingo's stock price data for at least one stock for a few business_date

    # Make a copy to avoid mutating the original dataframe
    df_ticker = df_ticker.copy()

    # Reset index of df_ticker to start from 0. Otherwise, if we don't do this, we will inherit index of df, and this iterative algorithm will fail for stock 2 onwards, and only work for the first stock in df
    df_ticker = df_ticker.reset_index(drop=True)

    # There are 4 flavors of price to adjust for corporate actions
    price_fields = ["open", "high", "low", "close"]
    volume_fields = ["volume"]  # I know this redundant but in the future we might have more volume fields such as short_volume, etc.
    fields = price_fields + volume_fields

    # Cast to float to avoid issues with division and subtract later on
    for field in fields:
        df_ticker[f"adj_{field}"] = df_ticker[field].astype(float)

    # Iterate through every business_date for this stock, from past to present
    for i in df_ticker.index:
        
        dividend = df_ticker.loc[i,"div_cash"]
        split_ratio = df_ticker.loc[i,"split_factor"]
        
        # If there is a dividend payment today, subtract all prices from yesterday & before by dividend amount to make history comparable to today
        if dividend > 0:
            for price_field in price_fields:
                df_ticker.loc[:i-1, f"adj_{price_field}"] -= dividend        
        
        # If there is a stock split today, divide all prices from yesterday & before by split_ratio to make history comparable to today
        if split_ratio != 1:
            for price_field in price_fields:
                df_ticker.loc[:i-1, f"adj_{price_field}"] /= split_ratio
            for volume_field in volume_fields:
                df_ticker.loc[:i-1, f"adj_{volume_field}"] *= split_ratio
    
    return df_ticker


# group_keys = False to avoid multi-layer index, i.e. - to keep rows keyed on (ticker, business_date)
# include_groups = True to include ticker as a column in the resulting output dataframe. If false, ticker will not appear in result
def adj_corp_actions(df: pd.DataFrame) -> pd.DataFrame:
    result = df.groupby("ticker", group_keys = False).apply(adj_corp_actions_for_one_stock, include_groups = True)
    return result

# TODO: We need a function that calculates daily (DoD) returns given adjusted prices.  Probably only need to apply this onto the closing prices for now

# TODO: We need to write to prod table afterward using psycopg2.  Need to define table schema and then add it to setup_tables.py

def main_staging_to_prod(start_date: date, end_date: date, tickers: List[str], conn: Connection, cursor: Cursor) -> None:
    # TODO: get data from staging table (extract)
    # TODO: transform using adj_corp_actions
    # TODO: calculate daily returns (DoD % change in closing prices)
    # TODO: load into prod table
    pass

def main_cli():
    args = get_cli_args()
    start_date, end_date, user_provided_tickers = validate_cli_args(args, cursor)
    main_staging_to_prod(start_date, end_date, user_provided_tickers, conn, cursor)

def main_airflow():
    active_tickers = validate_list_of_tickers_or_fetch_from_db(None, cursor)
    main_staging_to_prod(today, today, active_tickers, conn, cursor)
    pass

if __name__ == "__main__":
    # By default, this driver should run the CLI version.  Airflow job will be invoked in DAGs
    main_cli()