import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sales Forecasting Dashboard", page_icon="📈", layout="wide")
st.title("Sales Forecasting Dashboard")
st.caption("Map your CSV columns, check the data, and create an explainable baseline forecast.")

uploaded = st.sidebar.file_uploader("Upload transaction CSV", type="csv")
try:
    raw = pd.read_csv(uploaded) if uploaded else pd.read_csv("sample_sales.csv")
except Exception as exc:
    st.error(f"Could not read this CSV: {exc}")
    st.stop()
if raw.empty:
    st.error("The CSV has no rows.")
    st.stop()
if not uploaded:
    st.info("Showing the included synthetic sample. Upload your own CSV to try another format.")

cols = list(raw.columns)
low = {c: c.strip().lower().replace("_", "").replace(" ", "") for c in cols}
def find_col(names):
    return next((c for c in cols if low[c] in names), None)

date_guess = find_col({"date", "invoicedate", "transactiondate", "orderdate", "timestamp", "datetime"})
product_guess = find_col({"product", "productname", "description", "item", "itemname", "sku"}) or find_col({"stockcode"})
category_guess = find_col({"category", "productcategory", "department"})
quantity_col = find_col({"quantity", "qty", "units", "unitssold"})
price_col = find_col({"unitprice", "priceperunit", "price"})

with st.sidebar:
    st.header("1. Map your columns")
    st.caption("Suggestions are based on column names and data types. Confirm or change them for each file.")
    date_col = st.selectbox("Date column", cols, index=cols.index(date_guess) if date_guess in cols else 0, key="date_col")
    nums = list(raw.select_dtypes(include="number").columns)
    derived_revenue = "Net revenue (quantity × unit price)"
    if quantity_col and price_col:
        work_source = raw.copy()
        work_source[derived_revenue] = pd.to_numeric(work_source[quantity_col], errors="coerce") * pd.to_numeric(work_source[price_col], errors="coerce")
    else:
        work_source = raw.copy()
    measures = nums + ([derived_revenue] if quantity_col and price_col else [])
    if not measures:
        st.error("No numeric columns found. The forecast measure must be numeric.")
        st.stop()
    measure_guess = find_col({"revenue", "sales", "salesamount", "netsales"})
    if measure_guess not in measures:
        measure_guess = derived_revenue if derived_revenue in measures else find_col({"quantity", "qty", "units"})
    if measure_guess not in measures:
        measure_guess = measures[0]
    measure_col = st.selectbox("What should be forecast?", measures, index=measures.index(measure_guess), key="measure")
    if measure_col == derived_revenue:
        st.caption("Calculated per row as quantity × unit price. Negative quantities reduce net sales and may include returns or cancellations.")
    st.caption("Product and category filters are optional; this app does not invent categories.")
    product_options = ["(No product filter)"] + [c for c in cols if c != date_col and c != measure_col]
    product_default = product_options.index(product_guess) if product_guess in product_options else 0
    product_choice = st.selectbox("Product/name column", product_options, index=product_default, key="product_map")
    category_options = ["(No category filter)"] + [c for c in cols if c not in {date_col, measure_col, product_choice}]
    category_default = category_options.index(category_guess) if category_guess in category_options else 0
    if st.session_state.get("category_map") not in category_options:
        st.session_state["category_map"] = category_options[category_default]
    category_choice = st.selectbox("Category column", category_options, key="category_map")
    freq = st.selectbox("Time grouping", ["Daily", "Weekly", "Monthly"], index=2, key="frequency")
    freq_code = {"Daily":"D", "Weekly":"W", "Monthly":"MS"}[freq]
    horizon = st.slider("Periods to forecast", 1, 24, 6, key="horizon")
    holdout = st.slider("Periods to hold out for evaluation", 2, 24, 6, key="holdout")

product_col = None if product_choice == "(No product filter)" else product_choice
category_col = None if category_choice == "(No category filter)" else category_choice
work = work_source.copy()
parsed_dates = pd.to_datetime(work[date_col], errors="coerce")
valid_ratio = parsed_dates.notna().mean()
if valid_ratio < 0.8:
    st.error(f"The selected date column '{date_col}' has only {valid_ratio:.0%} values that parse as dates. Choose the actual date column (for UCI Online Retail, use InvoiceDate).")
    st.stop()
work[date_col] = parsed_dates
work[measure_col] = pd.to_numeric(work[measure_col], errors="coerce")
initial_rows = len(work)
work = work.dropna(subset=[date_col, measure_col])
dropped = initial_rows - len(work)
if dropped:
    st.info(f"Skipped {dropped:,} rows with a missing/invalid date or forecast value.")

for label, col, key in [("Products", product_col, "products"), ("Categories", category_col, "categories")]:
    if col:
        vals = sorted(work[col].dropna().astype(str).unique())
        if key not in st.session_state or not set(st.session_state[key]).issubset(set(vals)):
            st.session_state[key] = vals
        if st.sidebar.button(f"Clear {label.lower()} selection", key=f"{key}_clear"):
            st.session_state[key] = []
        chosen = st.sidebar.multiselect(f"Filter {label.lower()}", vals, default=vals, key=key)
        work = work[work[col].astype(str).isin(chosen)]
if work.empty:
    st.warning("No rows remain after filtering. Select at least one product/category or clear the filters.")
    st.stop()

st.subheader("Current analysis")
summary = [f"Date: {date_col}", f"Measure: {measure_col}", f"Grouping: {freq}"]
if product_col:
    summary.append(f"Product: {product_col} ({work[product_col].nunique()} selected)")
if category_col:
    summary.append(f"Category: {category_col} ({work[category_col].nunique()} selected)")
st.info(" · ".join(summary))

st.subheader("2. Check the data mapping")
st.caption("Confirm that the selected columns mean what you expect. For example, UCI Online Retail uses InvoiceDate for date, Description for product, Quantity for units, and Quantity × UnitPrice for net revenue.")
st.dataframe(work[[date_col] + ([product_col] if product_col else []) + ([category_col] if category_col and category_col != product_col else []) + [measure_col]].head(8), use_container_width=True)
unique_dates = pd.Series(work[date_col].dropna().sort_values().unique())
if len(unique_dates) > 1:
    median_gap_days = pd.Series(unique_dates).diff().dropna().median() / pd.Timedelta(days=1)
    requested_days = {"Daily": 1, "Weekly": 7, "Monthly": 28}[freq]
    if median_gap_days > requested_days * 1.5:
        st.warning(f"Your records are typically {median_gap_days:.0f} days apart, but the selected grouping is {freq.lower()}. This creates empty periods and can make evaluation misleading. Choose a grouping at least as broad as the data spacing.")
series = work.set_index(date_col)[measure_col].resample(freq_code).sum().replace(0, np.nan).dropna()
if len(series) < 8:
    st.error(f"Only {len(series)} non-empty {freq.lower()} periods remain. At least 8 are needed; choose a broader time range or grouping.")
    st.stop()

st.subheader("3. Past values")
st.caption("This chart shows recorded values after grouping them by time. It describes history; it does not predict the future.")
a,b,c=st.columns(3)
a.metric("Periods", f"{len(series):,}")
b.metric(f"Total {measure_col}", f"{series.sum():,.2f}")
c.metric("Average per period", f"{series.mean():,.2f}")
st.line_chart(series.rename(measure_col))
if product_col:
    st.caption("Totals by selected product names")
    st.bar_chart(work.groupby(product_col)[measure_col].sum().sort_values(ascending=False))

test_n=min(holdout,max(2,len(series)//3)); train,test=series.iloc[:-test_n],series.iloc[-test_n:]
season=12 if freq_code=="MS" else 7 if freq_code=="D" else 52
seasonal_available = len(train) >= 2 * season
last=float(train.iloc[-1]); mean=float(train.mean())
drift=(float(train.iloc[-1])-float(train.iloc[0]))/max(1,len(train)-1)
models={"Naive (last value)":np.repeat(last,test_n),"Training mean":np.repeat(mean,test_n),"Drift":last+drift*np.arange(1,test_n+1)}
if seasonal_available:
    models["Seasonal naive"] = np.array([train.iloc[-season+(i%season)] for i in range(test_n)])
rows=[]
for name,pred in models.items():
    err=test.to_numpy()-pred
    rows.append({"Method":name,"MAE":np.mean(np.abs(err)),"RMSE":np.sqrt(np.mean(err**2)),"WAPE (%)":100*np.sum(np.abs(err))/max(1e-9,np.sum(np.abs(test.to_numpy())))})
scores=pd.DataFrame(rows).set_index("Method")
st.subheader("4. Compare simple forecasting methods")
st.caption(f"The most recent {test_n} periods are temporarily held aside (the slider allows up to roughly one third of the history). Methods use only earlier periods, then their guesses are compared with actual values.")
if not seasonal_available:
    st.info(f"Seasonal naive is omitted: {freq.lower()} data needs at least {2 * season} training periods to check two complete seasonal cycles. This file does not contain enough history for a reliable seasonal comparison.")
st.markdown("**Reading the scores:** MAE is the typical size of a miss; RMSE gives extra weight to large misses; WAPE is total error as a percentage of actual values. Lower is better. The lowest-MAE method is used below.")
st.dataframe(scores.style.format("{:.2f}"),use_container_width=True)
comparison=pd.DataFrame({"Actual":test})
for name,pred in models.items(): comparison[name]=pred
st.caption("Actual means recorded values. The other lines are the methods' guesses for those same test dates; closer to Actual is better.")
st.line_chart(comparison)

best=scores["MAE"].idxmin()
if best=="Naive (last value)": forecast=np.repeat(float(series.iloc[-1]),horizon)
elif best=="Training mean": forecast=np.repeat(float(series.mean()),horizon)
elif best=="Drift": forecast=float(series.iloc[-1])+((float(series.iloc[-1])-float(series.iloc[0]))/max(1,len(series)-1))*np.arange(1,horizon+1)
elif best=="Seasonal naive": forecast=np.array([series.iloc[-season+(i%season)] for i in range(horizon)])
else: forecast=np.repeat(float(series.iloc[-1]),horizon)
resid=test.to_numpy()-models[best]; sigma=max(float(np.sqrt(np.mean(resid**2))),float(series.std())*.05,1e-9)
future=pd.date_range(series.index[-1],periods=horizon+1,freq=freq_code)[1:]
out=pd.DataFrame({"forecast":forecast,"approx_lower":forecast-1.96*sigma,"approx_upper":forecast+1.96*sigma},index=future); out.index.name="date"
st.subheader("5. Future estimate")
st.caption(f"Selected method: {best}. It is recalculated using all available history. This is an estimate if past patterns continue, not a promise or explanation of why sales change.")
st.caption("Forecast is the central estimate. approx_lower and approx_upper are rough limits based on earlier test errors; they are not calibrated 95% confidence bounds.")
st.line_chart(pd.concat([series.rename("Actual"),out]))
st.dataframe(out,use_container_width=True)
st.download_button("Download forecast CSV",out.to_csv().encode("utf-8"),"sales_forecast.csv","text/csv")
st.warning("This app compares simple rules, not a trained machine-learning model. Check returns, missing periods, and business context before using results.")
