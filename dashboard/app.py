

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------- PAGE SETTINGS ----------------
st.set_page_config(
    page_title="Smart Energy Dashboard",
    page_icon="⚡",
    layout="wide"
)

# ---------------- CUSTOM STYLE ----------------
st.markdown("""
<style>
.main {
    background-color: #f5f8fc;
}
.block-container {
    padding-top: 1.5rem;
}
[data-testid="stMetric"] {
    background-color: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #e5eaf2;
}
</style>
""", unsafe_allow_html=True)

# ---------------- LOAD EXCEL DATASET ----------------
PROJECT_DIR = Path(__file__).resolve().parent.parent

possible_files = [
    PROJECT_DIR / "dataset" / "energydata_complete.xlsx",
    PROJECT_DIR / "dataset" / "energydata_complete.xls",
    PROJECT_DIR / "energydata_complete.xlsx",
    PROJECT_DIR / "energydata_complete.xls",
]

data_file = next(
    (file for file in possible_files if file.exists()),
    None
)

st.title("⚡ Smart Energy Consumption & Optimization")
st.caption(
    "Explore energy usage patterns, identify peak periods, "
    "and discover opportunities to improve energy efficiency."
)

if data_file is None:
    st.error(
        "Excel dataset not found. Upload energydata_complete.xlsx "
        "inside the repository's dataset folder."
    )
    st.code(
        "dataset/energydata_complete.xlsx\n"
        "dashboard/app.py\n"
        "dashboard/requirements.txt"
    )
    st.stop()

try:
    df = pd.read_excel(data_file)
except Exception as error:
    st.error(f"Unable to read the Excel file: {error}")
    st.info("Check that openpyxl is listed in requirements.txt.")
    st.stop()

# ---------------- CLEAN COLUMN NAMES ----------------
df.columns = df.columns.astype(str).str.strip()

# Find columns without depending on capitalization
column_lookup = {col.lower(): col for col in df.columns}

date_col = column_lookup.get("date")
appliances_col = column_lookup.get("appliances")
outside_temp_col = column_lookup.get("t_out")

if date_col is None:
    st.error(
        "A 'date' column was not found. Available columns: "
        + ", ".join(df.columns.astype(str))
    )
    st.stop()

if appliances_col is None:
    st.error(
        "An 'Appliances' column was not found. Available columns: "
        + ", ".join(df.columns.astype(str))
    )
    st.stop()

df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
df[appliances_col] = pd.to_numeric(
    df[appliances_col], errors="coerce"
)

df = df.dropna(subset=[date_col, appliances_col]).copy()
df = df.sort_values(date_col)

if df.empty:
    st.error("No valid rows remain after cleaning the dataset.")
    st.stop()

# Create time-related features
df["Hour"] = df[date_col].dt.hour
df["Day"] = df[date_col].dt.day
df["Weekday"] = df[date_col].dt.day_name()
df["Date"] = df[date_col].dt.date
df["Month"] = df[date_col].dt.strftime("%Y-%m")

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("🎛️ Dashboard Filters")

min_date = df[date_col].min().date()
max_date = df[date_col].max().date()

selected_dates = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = selected_dates
    end_date = selected_dates

filtered_df = df[
    (df[date_col].dt.date >= start_date)
    & (df[date_col].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("No data available for the selected dates.")
    st.stop()

# ---------------- KEY PERFORMANCE INDICATORS ----------------
st.subheader("📊 Energy Overview")

average_usage = filtered_df[appliances_col].mean()
peak_usage = filtered_df[appliances_col].max()
minimum_usage = filtered_df[appliances_col].min()
total_records = len(filtered_df)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Average Appliance Reading", f"{average_usage:,.2f}")
c2.metric("Peak Appliance Reading", f"{peak_usage:,.2f}")
c3.metric("Minimum Reading", f"{minimum_usage:,.2f}")
c4.metric("Total Records", f"{total_records:,}")

st.caption(
    "Readings use the units provided by the source dataset; "
    "they are not automatically converted to kWh."
)

st.divider()

# ---------------- DAILY ENERGY TREND ----------------
st.subheader("📈 Daily Consumption Trend")

daily_usage = (
    filtered_df.groupby("Date", as_index=False)[appliances_col]
    .mean()
)

fig_daily = px.line(
    daily_usage,
    x="Date",
    y=appliances_col,
    markers=True,
    title="Average Appliance Reading by Day",
    labels={
        "Date": "Date",
        appliances_col: "Average Appliance Reading"
    }
)

fig_daily.update_layout(hovermode="x unified")
st.plotly_chart(fig_daily, use_container_width=True)

# ---------------- HOURLY ANALYSIS ----------------
left, right = st.columns(2)

with left:
    st.subheader("🕒 Hourly Usage Pattern")

    hourly_usage = (
        filtered_df.groupby("Hour", as_index=False)[appliances_col]
        .mean()
    )

    fig_hourly = px.bar(
        hourly_usage,
        x="Hour",
        y=appliances_col,
        title="Average Usage by Hour",
        labels={
            "Hour": "Hour of Day",
            appliances_col: "Average Reading"
        }
    )

    st.plotly_chart(fig_hourly, use_container_width=True)

with right:
    st.subheader("📅 Weekly Usage Pattern")

    weekday_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]

    weekday_usage = (
        filtered_df.groupby("Weekday")[appliances_col]
        .mean()
        .reindex(weekday_order)
        .dropna()
        .rename("Average Reading")
        .reset_index()
    )

    fig_weekday = px.bar(
        weekday_usage,
        x="Weekday",
        y="Average Reading",
        title="Average Usage by Day of Week",
        labels={
            "Weekday": "Day",
            "Average Reading": "Average Appliance Reading"
        }
    )

    st.plotly_chart(fig_weekday, use_container_width=True)

# ---------------- DISTRIBUTION ANALYSIS ----------------
st.subheader("📉 Consumption Distribution")

fig_hist = px.histogram(
    filtered_df,
    x=appliances_col,
    nbins=40,
    title="Distribution of Appliance Readings",
    labels={appliances_col: "Appliance Reading"}
)

st.plotly_chart(fig_hist, use_container_width=True)

# ---------------- TEMPERATURE RELATIONSHIP ----------------
if outside_temp_col is not None:
    filtered_df[outside_temp_col] = pd.to_numeric(
        filtered_df[outside_temp_col], errors="coerce"
    )

    temperature_df = filtered_df.dropna(
        subset=[outside_temp_col, appliances_col]
    )

    st.subheader("🌡️ Outdoor Temperature vs Appliance Usage")

    if not temperature_df.empty:
        fig_temp = px.scatter(
            temperature_df,
            x=outside_temp_col,
            y=appliances_col,
            opacity=0.5,
            title="Temperature and Appliance Reading",
            labels={
                outside_temp_col: "Outdoor Temperature",
                appliances_col: "Appliance Reading"
            }
        )

        st.plotly_chart(fig_temp, use_container_width=True)
    else:
        st.info("There are no valid temperature readings to plot.")

# ---------------- CORRELATION ANALYSIS ----------------
st.subheader("🔗 Feature Correlation")

numeric_df = filtered_df.select_dtypes(include="number")
numeric_df = numeric_df.drop(
    columns=["Hour", "Day"], errors="ignore"
)

if numeric_df.shape[1] >= 2:
    correlation = numeric_df.corr()

    fig_corr = px.imshow(
        correlation,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlation Between Numeric Features"
    )

    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("Not enough numeric columns for correlation analysis.")

# ---------------- PEAK USAGE ALERTS ----------------
st.subheader("🚨 Peak Usage Analysis")

threshold = (
    filtered_df[appliances_col].mean()
    + 2 * filtered_df[appliances_col].std()
)

peak_rows = filtered_df[
    filtered_df[appliances_col] > threshold
].copy()

if not peak_rows.empty:
    st.warning(
        f"Found {len(peak_rows):,} unusually high readings "
        "using the mean + 2 standard deviations rule."
    )

    display_cols = [date_col, appliances_col]

    if outside_temp_col is not None:
        display_cols.append(outside_temp_col)

    st.dataframe(
        peak_rows[display_cols].head(20),
        use_container_width=True
    )
else:
    st.success("No unusually high readings were detected by this rule.")

# ---------------- OPTIMIZATION INSIGHTS ----------------
st.subheader("💡 Energy Optimization Suggestions")

peak_hour = (
    filtered_df.groupby("Hour")[appliances_col]
    .mean()
    .idxmax()
)

lowest_hour = (
    filtered_df.groupby("Hour")[appliances_col]
    .mean()
    .idxmin()
)

st.markdown(
    f"""
    - **Highest average usage hour:** {peak_hour}:00.
    - **Lowest average usage hour:** {lowest_hour}:00.
    - Review equipment operating during high-usage periods.
    - Switch off unused appliances where operationally appropriate.
    - Compare weekday and weekend patterns to identify potential waste.
    - Investigate unusually high readings before making changes.
    """
)

st.caption(
    "These are data-based observations, not proof of energy savings. "
    "Confirm recommendations against actual equipment and site conditions."
)

# ---------------- DATA PREVIEW & DOWNLOAD ----------------
with st.expander("🔍 View Filtered Dataset"):
    st.write(f"Rows: {len(filtered_df):,}")
    st.dataframe(filtered_df.head(100), use_container_width=True)

csv_data = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Filtered Data as CSV",
    data=csv_data,
    file_name="smart_energy_filtered_data.csv",
    mime="text/csv"
)

st.divider()
st.caption("Smart Energy Consumption & Optimization | EDA Dashboard")
