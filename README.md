# Sales Forecasting Dashboard

An English-language Streamlit MVP for exploring retail transactions, comparing time-aware baselines, and exporting forecasts.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Included sample data

`sample_sales.csv` is a synthetic illustrative retail dataset created for this project and dedicated to the public domain under CC0 1.0. It has 36 monthly periods and includes date, product, category, units sold, list price, discount, realized revenue, region, and channel. It is not real business data.

## Use your own CSV

Upload a CSV with one date-like column and at least one numeric measure. The app suggests date, product, and category columns from common names, then lets you change the mapping. For example, UCI Online Retail uses `InvoiceDate`, `Description`, and `StockCode`. If quantity and unit-price columns are available, the app offers net revenue calculated as `quantity × unit price`; negative quantities reduce that total and may represent returns/cancellations. The app does not infer product categories when no category column exists. Duplicate dates are summed. At least eight non-empty periods must remain after filtering.

The sidebar controls immediately rerun the app and update metrics, charts, evaluation, and forecast. On a different uploaded file, choose its matching columns. Changing the measure from revenue to units changes what is forecast; changing the product/category filters changes the series.

## Evaluation and limitations

The latest selected periods form a chronological test set. Naive, mean, drift, and seasonal-naive predictions are calculated from the earlier training window; lowest holdout MAE selects the method, which is then recalculated with the full history. This is one holdout, not rolling-origin validation, and model selection may be unstable on small datasets.

The approximate lower and upper forecast limits use a constant normal-error approximation from holdout residual RMSE. They are not calibrated 95% confidence bounds. The app warns when the requested aggregation is finer than the observed date spacing. Models do not account for promotions, holidays, price effects, stockouts, or external drivers. Treat results as planning aids, not guarantees.

## Local demonstration dataset

The UCI Online Retail CSV/XLSX files are optional local test files and are intentionally excluded from version control. The app repository includes only the small synthetic `sample_sales.csv`. The UCI dataset is available under CC BY 4.0 from the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/352/online%2Bretail); cite UCI if you discuss results based on it.
