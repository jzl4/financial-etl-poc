-- Querying staging table
select
	ticker, business_date,
	close, adj_close,
	div_cash, split_factor
from tbl_tiingo_daily_staging
where ticker in ('TSLA', 'NVDA') and business_date >= '2020-01-01'
order by business_date, ticker;

-- Querying prod table
select * from tbl_daily_prod
order by ticker, business_date;

-- Comparing my algorithm for calculating adjusted prices against Tiingo's adjusted prices
select
	prod.ticker,
	prod.business_date,
	raw.div_cash as dividend,
	raw.split_factor,
	raw.adj_close as adj_close_tiingo,	-- Tiingo's adjusted prices
	prod.adj_close as adj_close_calc,	-- Adjusted prices from my corp action adjustment algo
	prod.adj_close - raw.adj_close as adj_close_diff	-- How much do we differ?
from tbl_daily_prod prod join tbl_tiingo_daily_staging raw
	on prod.ticker = raw.ticker and prod.business_date = raw.business_date
where
	prod.ticker = 'NVDA' 
	and prod.business_date between '2020-01-01' and '2025-06-20'
order by business_date;
