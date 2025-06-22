import os
import sys
import argparse

import pandas as pd

# Required to import other modules from this project, in folders such as utils/ or notebooks/
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)

# Load .env file for AWS RDS login credentials
from dotenv import load_dotenv
dotenv_path = os.path.join(project_root_folder, ".env")
load_dotenv(dotenv_path)

# Import functionalities from other modules in this project
from utils.db_utils import *
from utils.datetime_utils import get_today_est
from utils.argparse_utils import *
from psycopg2 import extras

# Global variables
today = get_today_est()

# TODO: Write a safer version of this using psycopg2 and sql module, to avoid SQL injection vulnerabilities
def extract_raw_data_from_staging(start_date: date, end_date: date, tickers: List[str], cursor: Cursor, conn: Connection):
    """
    Given start_date, end_date, and list of tickers, extract raw/unadjusted price & volume data from tbl_tiingo_daily_staging, as a Pandas dataframe
    """

    # Example: 'SPY','GLD'
    ticker_list_as_str = "'" + "','".join(ticker for ticker in tickers) + "'"

    query = f"""
    select
        ticker, business_date,
        open, high, low, close, volume,
        div_cash, split_factor
    from tbl_tiingo_daily_staging
    where business_date between '{start_date}' and '{end_date}' and ticker in ({ticker_list_as_str})
    order by ticker, business_date;
    """

    df = sql_query_as_df(query, cursor)
    return df

def adj_corp_actions_for_one_stock(df_ticker: pd.DataFrame) -> pd.DataFrame:
    """
    Given a dataframe of raw/unadjusted price history for a single ticker, sorted by business_date, iterate from oldest business_date to most recent business_date, using dividend payment and stock split ratio information, to calculate adjusted fields that reflect the true return an investor holding the stock would have earned. Dataframe must contain columns:
    - Business_date: business_date (ascending / from oldest to newest)
    - Unadjusted fields: open (opening price), high (high price), low (low price), close (closing price), volume
    - Dollar of dividends paid that day: div_cash. 0 = no dividend that day (default), 1 = $1 dividend was paid out that day, etc.
    - Stock split ratio: split_factor. 1 = no stock split that day (default), 2 = a stock of $100 split into 2 shares of $50 that date, etc.
    Returns dataframe with additional columns: adj_open, adj_high, adj_low, adj_close, adj_volume
    """

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
    """
    Applies function adj_corp_actions_for_one_stock to multiple stocks. Input dataframe df must contain columns:
    - Keys: ticker, business_date
    - Unadjusted fields: open (opening price), high (high price), low (low price), close (closing price), volume
    - Dollar of dividends paid that day: div_cash. 0 = no dividend that day (default), 1 = $1 dividend was paid out that day, etc.
    - Stock split ratio: split_factor. 1 = no stock split that day (default), 2 = a stock of $100 split into 2 shares of $50 that date, etc.
    """

    # TODO: This might not be necessary because I already sort by (ticker, business_date) in extract_raw_data_from_staging
    df.sort_values(["ticker", "business_date"], inplace = True)

    result = df.groupby("ticker", group_keys = False).apply(adj_corp_actions_for_one_stock, include_groups = True)
    return result

def calculate_daily_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily percentage change for adj_open, adj_close, adj_volume, over business_date, for each ticker in df
    """

    # TODO: This might not be necessary because I already sort by (ticker, business_date) in extract_raw_data_from_staging
    df.sort_values(["ticker", "business_date"], inplace = True)

    cols = ["adj_open", "adj_close", "adj_volume"]

    for col in cols:
        df[f"{col}_pct_chg"] = df.groupby("ticker")[col].pct_change()
        df[f"{col}_pct_chg"]  = 100 * df[f"{col}_pct_chg"]

    return df

def insert_into_daily_prod(df: pd.DataFrame, cursor, conn):
    """
    Insert data into tbl_daily_prod
    """

    # print("Columns in df for insert_into_daily_prod")
    # print(df.columns)

    cols = ["ticker", "business_date", "adj_open", "adj_close", "adj_volume", "adj_open_pct_chg", "adj_close_pct_chg", "adj_volume_pct_chg"]

    df_subset = df[cols]

    data = list(df_subset.itertuples(index = False, name = None))

    query = """
    INSERT INTO tbl_daily_prod (
        ticker,
        business_date,
        adj_open,
        adj_close,
        adj_volume,
        adj_open_pct_chg,
        adj_close_pct_chg,
        adj_volume_pct_chg
    )
    VALUES %s
    ON CONFLICT (ticker, business_date) DO UPDATE SET
        adj_open = EXCLUDED.adj_open,
        adj_close = EXCLUDED.adj_close,
        adj_volume = EXCLUDED.adj_volume,
        adj_open_pct_chg = EXCLUDED.adj_open_pct_chg,
        adj_close_pct_chg = EXCLUDED.adj_close_pct_chg,
        adj_volume_pct_chg = EXCLUDED.adj_volume_pct_chg,
        ingestion_ts = now(),
        source = 'Tiingo'
    """

    extras.execute_values(cursor, query, data)
    conn.commit()
    print(f"Bulk inserted/updated {len(df)} rows into tbl_daily_prod.")

def main_staging_to_prod(start_date: date, end_date: date, tickers: List[str], conn: Connection, cursor: Cursor) -> None:
    
    df_raw = extract_raw_data_from_staging(start_date, end_date, tickers, cursor, conn)
    df_adj = adj_corp_actions(df_raw)
    df_adj_returns = calculate_daily_returns(df_adj)
    insert_into_daily_prod(df_adj_returns, cursor, conn)

def main_cli():
    conn, cursor = connect_to_rds()
    try:
        args = get_cli_args()
        start_date, end_date, user_provided_tickers = validate_cli_args(args, cursor)
        main_staging_to_prod(start_date, end_date, user_provided_tickers, conn, cursor)
    except Exception as e:
        print(f"Error in main_cli: {e}")
        sys.exit(1)
    finally:
        conn.close()

def main_airflow():
    conn, cursor = connect_to_rds()
    try:
        active_tickers = validate_list_of_tickers_or_fetch_from_db(None, cursor)
        main_staging_to_prod(today, today, active_tickers, conn, cursor)
    except Exception as e:
        print(f"Error in main_airflow: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    # By default, this driver should run the CLI version.  Airflow job will be invoked in DAGs
    main_cli()