# PIF Backtest `P5`: Cash-Aware Copy Trade

`P5` is a more literal mirror of the disclosed `PIF` 13F sleeve than the earlier fully invested strategies.

## Intent

The strategy is designed to answer:

> If we simply copy the disclosed buys and sells as soon as the filings make them public, and we keep sale proceeds in cash instead of forcing reinvestment, does the sleeve produce alpha?

This differs from `P2` through `P4`, which reinterpret the disclosed sleeve into fully invested portfolios.

## Core Rules

### Initialization

- Start with `initial_nav = 1.0`
- On the first public filing date, buy the full eligible common-equity sleeve
- Use a global scaling factor so our initial holdings are proportional to disclosed `PIF` share counts while exactly fitting our starting capital

### Ongoing Trade Logic

On each later public filing date:

- `exit_observed`: sell the mirrored position and hold the proceeds in cash
- `likely_reduction`: reduce the mirrored position proportionally to the disclosed share-count reduction and hold the proceeds in cash
- `likely_accumulation`: increase the mirrored position proportionally to the disclosed share-count increase, but only using available cash
- `entry_observed`: buy the new name using available cash

### Cash Constraint

If disclosed buys on a rebalance date require more capital than available cash:

- scale all buy orders for that date down proportionally
- do not borrow
- do not force sells of unchanged names to fund buys

This means the strategy's gross exposure can fall over time when `PIF` is a net seller of the disclosed sleeve.

## Price Basis

- Execution and mark-to-market are recorded with split-adjusted closes for return correctness
- Raw closes are retained in the order output for auditability

## Outputs

- `p5cac_signal_eligibility.csv`
- `p5cac_rebalance_events.csv`
- `p5cac_orders.csv`
- `p5cac_holdings_daily.csv`
- `p5cac_portfolio_daily.csv`
- `p5cac_summary.json`

## Important Caveat

`P5` mirrors only what is visible in the US `13F` sleeve. If `PIF` funds a disclosed buy from assets outside the visible sleeve, the backtest will not see that funding source and may partially scale down those purchases. That is deliberate: the strategy is constrained to public information and public capital flows visible from the disclosed sleeve alone.
