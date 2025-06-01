# Standard library imports
import sys
import os
import argparse

# Required to import other modules from this project, in folders such as utils/ or notebooks/
current_folder = os.path.dirname(__file__)
project_root_folder = os.path.abspath(os.path.join(current_folder, ".."))
sys.path.append(project_root_folder)

# Load .env file for AWS RDS login credentials
# dotenv_path = os.path.join(project_root_folder, ".env")

def get_cli_args() -> argparse.Namespace:
    """
    Get CLI arguments start_date, end_date, and list of tickers, for extracting end-of-day data from Tiingo API
    """

    # Create the ArgumentParser instance and define the expected CLI arguments
    parser = argparse.ArgumentParser(description = "Get CLI arguments start_date, end_date, and list of tickers, for extracting end-of-day data from Tiingo API. Example 1: python ingest_tiingo_to_staging.py -s '2025-05-29' -e '2025-05-30' -t 'SPY GLD' | Example 2: python ingest_tiingo_to_staging.py --start_date '2025-05-29' --end_date '2025-05-30' --tickers 'SPY GLD'")
    parser.add_argument("-s", "--start_date", type = str, help = "Start date in YYYY-MM-DD format")
    parser.add_argument("-e", "--end_date", type = str, help = "End date in YYYY-MM-DD format")
    parser.add_argument("-t", "--tickers", nargs = "*", help = "List of tickers, separated by spaces. If not provided, will use default tickers from tbl_active_tickers table")

    # Parse the CLI inputs and return a Namespace object containing: parsed_args.start_date, etc.
    parsed_args = parser.parse_args()
    return parsed_args



if __name__ == "__main__":
    args = get_cli_args()
    # print(args.start_date)
    # print(args.end_date)
    # print(args.tickers)