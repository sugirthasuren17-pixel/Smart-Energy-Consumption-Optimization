import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ---------------- PAGE CONFIGURATION ----------------
st.set_page_config(
    page_title="Smart Energy Dashboard",
    page_icon="⚡",
    layout="wide"
)

# ---------------- CUSTOM DESIGN ----------------
st.markdown("""
<style>
.stApp {
    background-color: #f4f8f6;
}
[data-testid="stSidebar"] {
    background-color: #e3f1e9;
}
h1, h2, h3 {
    color: #12664f;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 12px;
    border: 1px solid #d7e7df;
}
</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.title("⚡ Smart Energy Consumption & Optimization")
st.markdown(
    "### Energy Analytics Dashboard | Exploratory Data Analysis"
)
st.write(
    "Monitor energy consumption, identify high-usage appliances, "
    "analyze consumption patterns and explore energy-saving opportunities."
)

# ---------------- LOAD DATASET ----------------
st.sidebar.header("📁 Dataset")

uploaded_file = st.sidebar.file_uploader(
    "Upload Excel or CSV file",
    type=["xlsx", "xls", "csv"]
)

try:
    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    else:
        file_path = Path(__file__).parent / "cleaned_dataset.xlsx"

        if not file_path.exists():
            st.error(
                "cleaned_dataset.xlsx not found. "
                "Place it in the same folder as app.py or upload it using the sidebar."
            )
            st.stop()

        df = pd.read_excel(file_path)

except Exception as error:
    st.error(f"Unable to load dataset: {error}")
    st.stop()

# ---------------- VALIDATE DATA ----------------
required_columns = [
    "Timestamp",
    "Building_Type",
    "Appliance",
    "Energy_Consumption_kWh",
    "Temperature_C",
    "Occupancy_Percent",
    "Tariff_Period",
    "Renewable_Generation_kWh"
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    st.error("Missing columns: " + ", ".join(missing_columns))
    st.write("Available columns:", df.columns.tolist())
    st.stop()

# ---------------- DATA CLEANING ----------------
df["Timestamp"] = pd.to_datetime(
    df["Timestamp"], errors="coerce"
)

numeric_columns = [
    "Energy_Consumption_kWh",
    "Temperature_C",
    "Occupancy_Percent",
    "Renewable_Generation_kWh"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(
    subset=["Timestamp", "Energy_Consumption_kWh"]
)

df = df[df["Energy_Consumption_kWh"] >= 0].copy()

if df.empty:
    st.error("No valid energy readings found in the dataset.")
    st.stop()

for col in ["Building_Type", "Appliance", "Tariff_Period"]:
    df[col] = df[col].fillna("Unknown").astype(str)

df["Temperature_C"] = df["Temperature_C"].fillna(
    df["Temperature_C"].median()
)
df["Occupancy_Percent"] = df["Occupancy_Percent"].fillna(0)
df["Renewable_Generation_kWh"] = (
    df["Renewable_Generation_kWh"].fillna(0)
)

df["Hour"] = df["Timestamp"].dt.hour
df["Date"] = df["Timestamp"].dt.date
df["Day"] = df["Timestamp"].dt.day_name()

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("🔍 Filters")

buildings = sorted(df["Building_Type"].unique())
appliances = sorted(df["Appliance"].unique())
tariffs = sorted(df["Tariff_Period"].unique())

selected_buildings = st.sidebar.multiselect(
    "Building Type",
    buildings,
    default=buildings
)

selected_appliances = st.sidebar.multiselect(
    "Appliance",
    appliances,
    default=appliances
)

selected_tariffs = st.sidebar.multiselect(
    "Tariff Period",
    tariffs,
    default=tariffs
)

min_date = df["Timestamp"].min().date()
max_date = df["Timestamp"].max().date()

date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# ---------------- APPLY FILTERS ----------------
filtered = df[
    df["Building_Type"].isin(selected_buildings)
    & df["Appliance"].isin(selected_appliances)
    & df["Tariff_Period"].isin(selected_tariffs)
].copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range

    filtered = filtered[
        (filtered["Timestamp"].dt.date >= start_date)
        & (filtered["Timestamp"].dt.date <= end_date)
    ]

if filtered.empty:
    st.warning("No data found for the selected filters.")
    st.stop()

# ---------------- KPI METRICS ----------------
st.header("📊 Energy Overview")

total_energy = filtered["Energy_Consumption_kWh"].sum()
average_energy = filtered["Energy_Consumption_kWh"].mean()
peak_reading = filtered["Energy_Consumption_kWh"].max()
renewable_energy = filtered["Renewable_Generation_kWh"].sum()

electricity_rate = st.sidebar.number_input(
    "Electricity rate (₹/kWh)",
    min_value=0.0,
    value=8.0,
    step=0.5
)

estimated_cost = total_energy * electricity_rate

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Total Consumption",
    f"{total_energy:,.2f} kWh"
)

col2.metric(
    "Average Consumption",
    f"{average_energy:.3f} kWh"
)

col3.metric(
    "Highest Reading",
    f"{peak_reading:.3f} kWh"
)

col4.metric(
    "Estimated Cost",
    f"₹{estimated_cost:,.2f}"
)

col5, col6 = st.columns(2)

col5.metric(
    "Renewable Generation",
    f"{renewable_energy:,.2f} kWh"
)

renewable_share = (
    renewable_energy / total_energy * 100
    if total_energy > 0 else 0
)

col6.metric(
    "Renewable / Consumption",
    f"{renewable_share:.1f}%"
)

st.caption(
    "Cost is an estimate based on the selected tariff. "
    "The highest reading represents an individual kWh reading, "
    "not peak electrical demand in kW."
)

st.divider()

# ---------------- ENERGY TREND ----------------
st.header("📈 Energy Consumption Trend")

frequency = st.selectbox(
    "Choose trend interval",
    ["Hourly", "Daily", "Weekly"]
)

time_series = filtered.set_index("Timestamp")[
    "Energy_Consumption_kWh"
]

if frequency == "Hourly":
    trend = time_series.resample("h").sum()
elif frequency == "Daily":
    trend = time_series.resample("D").sum()
else:
    trend = time_series.resample("W").sum()

trend_df = trend.rename("Energy (kWh)").reset_index()

fig = px.line(
    trend_df,
    x="Timestamp",
    y="Energy (kWh)",
    markers=True,
    title=f"{frequency} Energy Consumption",
    template="plotly_white"
)

fig.update_traces(line_color="#159570")
fig.update_layout(
    hovermode="x unified",
    xaxis_title="Time",
    yaxis_title="Energy (kWh)"
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- APPLIANCE ANALYSIS ----------------
st.header("🔌 Appliance-wise Consumption")

appliance_data = (
    filtered.groupby("Appliance", as_index=False)
    ["Energy_Consumption_kWh"]
    .sum()
    .sort_values("Energy_Consumption_kWh", ascending=False)
)

fig = px.bar(
    appliance_data,
    x="Appliance",
    y="Energy_Consumption_kWh",
    color="Energy_Consumption_kWh",
    title="Energy Used by Each Appliance",
    labels={
        "Energy_Consumption_kWh": "Energy (kWh)",
        "Appliance": "Appliance"
    },
    template="plotly_white",
    color_continuous_scale="Teal"
)

st.plotly_chart(fig, use_container_width=True)

if not appliance_data.empty:
    top_appliance = appliance_data.iloc[0]["Appliance"]
    top_value = appliance_data.iloc[0]["Energy_Consumption_kWh"]

    st.info(
        f"💡 Highest-consuming appliance in the selected data: "
        f"**{top_appliance}** ({top_value:.2f} kWh)."
    )

# ---------------- BUILDING ANALYSIS ----------------
st.header("🏢 Building-wise Energy Consumption")

building_data = (
    filtered.groupby("Building_Type", as_index=False)
    ["Energy_Consumption_kWh"]
    .sum()
    .sort_values("Energy_Consumption_kWh", ascending=False)
)

fig = px.pie(
    building_data,
    names="Building_Type",
    values="Energy_Consumption_kWh",
    hole=0.45,
    title="Consumption Distribution by Building",
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- HOURLY PATTERN ----------------
st.header("🕒 Peak Usage Time Analysis")

hourly_data = (
    filtered.groupby("Hour", as_index=False)
    ["Energy_Consumption_kWh"]
    .mean()
)

fig = px.bar(
    hourly_data,
    x="Hour",
    y="Energy_Consumption_kWh",
    title="Average Energy Consumption by Hour",
    labels={
        "Hour": "Hour of Day (0–23)",
        "Energy_Consumption_kWh": "Average Energy (kWh)"
    },
    template="plotly_white",
    color="Energy_Consumption_kWh",
    color_continuous_scale="YlGn"
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- ENVIRONMENT ANALYSIS ----------------
st.header("🌡️ Temperature and Occupancy Analysis")

col1, col2 = st.columns(2)

with col1:
    fig = px.scatter(
        filtered,
        x="Temperature_C",
        y="Energy_Consumption_kWh",
        color="Building_Type",
        title="Temperature vs Energy Consumption",
        labels={
            "Temperature_C": "Temperature (°C)",
            "Energy_Consumption_kWh": "Energy (kWh)"
        },
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = px.scatter(
        filtered,
        x="Occupancy_Percent",
        y="Energy_Consumption_kWh",
        color="Appliance",
        title="Occupancy vs Energy Consumption",
        labels={
            "Occupancy_Percent": "Occupancy (%)",
            "Energy_Consumption_kWh": "Energy (kWh)"
        },
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

# ---------------- ANOMALY DETECTION ----------------
st.header("🚨 Unusual Energy Usage Alerts")

q1 = filtered["Energy_Consumption_kWh"].quantile(0.25)
q3 = filtered["Energy_Consumption_kWh"].quantile(0.75)
iqr = q3 - q1

upper_limit = q3 + 1.5 * iqr

anomalies = filtered[
    filtered["Energy_Consumption_kWh"] > upper_limit
].sort_values(
    "Energy_Consumption_kWh",
    ascending=False
)

st.write(f"Statistical high-usage threshold: **{upper_limit:.3f} kWh**")
st.write(f"Potential high-usage readings found: **{len(anomalies)}**")

if not anomalies.empty:
    st.dataframe(
        anomalies[
            [
                "Timestamp",
                "Building_Type",
                "Appliance",
                "Energy_Consumption_kWh",
                "Temperature_C",
                "Occupancy_Percent"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )
else:
    st.success("No readings exceeded the current statistical threshold.")

st.caption(
    "These are potential outliers identified using the IQR method, "
    "not confirmed equipment faults."
)

# ---------------- CORRELATION ANALYSIS ----------------
st.header("🔗 Energy Factor Correlation")

correlation = filtered[
    [
        "Energy_Consumption_kWh",
        "Temperature_C",
        "Occupancy_Percent",
        "Renewable_Generation_kWh"
    ]
].corr(numeric_only=True)

fig = px.imshow(
    correlation,
    text_auto=".2f",
    aspect="auto",
    zmin=-1,
    zmax=1,
    color_continuous_scale="RdYlGn",
    title="Correlation Heatmap",
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Correlation indicates association; it does not prove causation."
)

# ---------------- DATA TABLE AND DOWNLOAD ----------------
st.header("📁 Filtered Dataset")

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True
)

csv_data = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="⬇️ Download Filtered Dataset",
    data=csv_data,
    file_name="smart_energy_filtered.csv",
    mime="text/csv"
)

# ---------------- FOOTER ----------------
st.divider()

st.markdown("""
### 🌱 Smart Energy Insights

- Identify appliances with high energy consumption.
- Examine hourly and daily consumption patterns.
- Compare energy usage across building types.
- Review unusual readings for possible energy waste.
- Use the findings to plan future energy optimization.

**Project:** Smart Energy Consumption & Optimization  
**Department:** Artificial Intelligence & Data Science
""")


