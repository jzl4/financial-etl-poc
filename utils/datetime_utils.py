from pytz import timezone   # Zoneinfo library requires Python 3.9, which conflicts with my Airflow 2.8.1 (which uses Python 3.8)
from datetime import datetime, date

def get_today_est() -> date:
    """
    Get today's date in EST. AWS's servers are in UTC, so if we are on the East Coast and pull stock price data late in the evening, we will end up grabbing data from "tomorrow" and crash. To prevent this, force EST
    """
    eastern_time_zone = timezone("US/Eastern")
    today_est = datetime.now(eastern_time_zone).date()
    return today_est