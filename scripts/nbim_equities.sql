select
  int_id,
  asset_class,
  date,
  region,
  country,
  company_name_issuer_name,
  market_value_nok,
  market_value_usd,
  industry,
  voting,
  ownership,
  incorporation_country
from holdings.gpfg_holdings_public
where asset_class = 'EQ'
order by date, company_name_issuer_name;
