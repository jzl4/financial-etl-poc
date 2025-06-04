-- Test query, for developing and checking logic for converting raw stock prices into adjusted stock prices, to handle corporate actions (dividend payments and stock splits)
select business_date, "close", adj_close, div_cash, split_factor
from tbl_tiingo_daily_staging
where ticker = 'NVDA'
order by ticker, business_date;