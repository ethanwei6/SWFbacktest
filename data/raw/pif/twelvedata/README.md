# PIF Twelve Data Inputs

This folder is optional.

Use it if you want to keep any manually curated mapping notes or saved API responses related to the `PIF` `Twelve Data` workflow.

The automated scripts themselves write processed outputs to:

- `data/processed/pif/`

## Required Environment Variable

Set your API key before running the scripts:

```bash
export TWELVEDATA_API_KEY="your_key_here"
```

## Main Scripts

- `python3 scripts/pif_twelvedata_mapping_builder.py`
- `python3 scripts/pif_twelvedata_price_fetcher.py`
