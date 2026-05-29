# PIF Interactive Explorer

## Objective

Turn the static `PIF` backtest outputs into a step-through visual narrative that lets a user:

- choose a focus strategy
- optionally overlay comparison strategies
- reveal the backtest one filing at a time
- see the disclosed signals, executed orders, and holdings snapshots alongside the resulting performance

## Main files

- App: `outputs/pif/backtests/interactive/pif_strategy_explorer.html`
- Data bundle: `outputs/pif/backtests/interactive/pif_strategy_explorer_data.js`
- Builder: `scripts/pif_interactive_explorer_builder.py`

## Design choices

### 1. Focus strategy vs overlay strategies

The app uses one **focus strategy** to drive the narrative stepper.

That focus strategy determines:

- filing segments
- current report window
- visible signals table
- executed orders table
- holdings snapshots
- cash / exposure panel
- filing-by-filing return bars

The user can still overlay additional strategies on the comparison charts.

### 2. Filing-step playback

The explorer starts empty.

Each press of `Next Filing`:

- selects the next rebalance/report window
- shows the report metadata and strategy decisions for that filing
- animates the charts forward until the next filing boundary

This matches the intended mental model:

- information becomes public
- the strategy reacts
- the portfolio evolves until the next public disclosure

### 3. PIF proxy treatment

`P2` is described in the app as the closest thing to a visible `PIF` disclosed-sleeve proxy.

It is not the true economic `PIF` portfolio. It is simply the broadest fully invested interpretation of the visible 13F sleeve.

### 4. Benchmark treatment

The benchmark is `SPY`, matched to each strategy’s own live window.

The app surfaces:

- absolute strategy NAV
- benchmark NAV
- relative NAV ratio
- filing-window strategy return vs filing-window benchmark return

## Data bundle contents

For each strategy, the bundle includes:

- summary metrics
- daily portfolio path
- filing/rebalance segments
- normalized signal rows by filing
- normalized order rows by filing
- top holdings snapshot after the trade
- top holdings snapshot at the end of the filing window

## Rebuild instructions

Run:

```bash
python3 scripts/pif_interactive_explorer_builder.py
```

This refreshes:

- `outputs/pif/backtests/interactive/pif_strategy_explorer_data.js`

The HTML app itself is static and does not need regeneration unless the interface code changes.

## Validation performed

The app was checked in Chrome as a local `file://` page for:

- successful load of the generated bundle
- empty initial state
- first filing-step playback
- synchronized update of metrics, charts, signals, orders, and holdings panels

## Known limitations

- The app is optimized for local exploration, not yet for deployment.
- The stepper is driven by strategy rebalance windows, not by every raw filing artifact independently.
- `P2` is a disclosed-sleeve proxy, not a true reconstruction of all `PIF` exposures.
