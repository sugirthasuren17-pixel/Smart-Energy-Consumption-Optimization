
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

# ---------------- LOAD DATASET ----------------
st.title("⚡ Smart Energy Consumption & Optimization")
st.caption(
    "Explore energy usage patterns, identify peak periods, "
    "and discover opportunities to improve energy efficiency."
)

PROJECT_DIR = Path(__file__).resolve().parent.parent


   
possible_files = [
    PROJECT_DIR / "dataset" / "energydata_complete.xlsx",
    PROJECT_DIR / "energydata_complete.xlsx",


]

data_file = next((p for p in possible_files if p.exists()), None)

if data_file is None:
    st.error(
        "Dataset not found. Put Smart_Energy_Cleaned.csv "
        "inside your project's dataset folder."
    )
    st.stop()

try:
    df = pd.read_csv(data_file)
except Exception as error:
    st.error(f"Could not read the dataset: {error}")
    st.stop()

# ---------------- VALIDATE DATA ----------------
if "Appliances" not in df.columns:
    st.error(
        "The dataset must contain an 'Appliances' column. "
        "Please check that you selected the correct dataset."
    )
    st.stop()

if "date" not in df.columns:
    st.error("The dataset must contain a 'date' column.")
    st.stop()

df["date"] = pd.to_datetime(df["date"], errors="coerce")
df["Appliances"] = pd.to_numeric(df["Appliances"], errors="coerce")

df = df.dropna(subset=["date", "Appliances"]).copy()

if df.empty:
    st.error("No valid date and energy consumption records were found.")
    st.stop()

# Add time columns for analysis
df["day"] = df["date"].dt.day_name()
df["hour"] = df["date"].dt.hour
df["date_only"] = df["date"].dt.date

# ---------------- SIDEBAR FILTERS ----------------
st.sidebar.header("🔎 Dashboard Filters")

min_date = df["date"].min().date()
max_date = df["date"].max().date()

start_date = st.sidebar.date_input(
    "Start date",
    value=min_date,
    min_value=min_date,
    max_value=max_date
)

end_date = st.sidebar.date_input(
    "End date",
    value=max_date,
    min_value=min_date,
    max_value=max_date
)

if start_date > end_date:
    st.error("Start date must be before or equal to end date.")
    st.stop()

filtered = df[
    (df["date"].dt.date >= start_date) &
    (df["date"].dt.date <= end_date)
].copy()

if filtered.empty:
    st.warning("No records are available for the selected dates.")
    st.stop()

# ---------------- KEY METRICS ----------------
st.subheader("📊 Energy Overview")

average_usage = filtered["Appliances"].mean()
maximum_usage = filtered["Appliances"].max()
minimum_usage = filtered["Appliances"].min()
total_records = len(filtered)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Average Appliance Reading", f"{average_usage:.2f} Wh")
c2.metric("Maximum Reading", f"{maximum_usage:.2f} Wh")
c3.metric("Minimum Reading", f"{minimum_usage:.2f} Wh")
c4.metric("Records Analyzed", f"{total_records:,}")

st.caption(
    "Appliances values are reported in Wh per measurement interval "
    "in the selected dataset. These readings are not automatically "
    "equivalent to total daily or monthly electricity consumption."
)

# ---------------- HOURLY ANALYSIS ----------------
st.divider()
st.subheader("🕒 Energy Consumption by Hour")

hourly = (
    filtered.groupby("hour", as_index=False)["Appliances"]
    .mean()
)

hourly.columns = ["Hour", "Average Consumption (Wh)"]

fig_hour = px.bar(
    hourly,
    x="Hour",
    y="Average Consumption (Wh)",
    color="Average Consumption (Wh)",
    color_continuous_scale="Blues",
    title="Average Appliance Consumption Across the Day",
    hover_data={"Hour": True}
)

fig_hour.update_layout(
    xaxis=dict(dtick=1, title="Hour of Day"),
    coloraxis_showscale=False
)

st.plotly_chart(fig_hour, use_container_width=True)

peak_row = hourly.loc[hourly["Average Consumption (Wh)"].idxmax()]

st.info(
    f"Highest average consumption occurs at hour "
    f"{int(peak_row['Hour']):02d}:00, with an average reading of "
    f"{peak_row['Average Consumption (Wh)']:.2f} Wh."
)

# ---------------- DAILY TREND ----------------
st.subheader("📈 Energy Consumption Trend")

daily = (
    filtered.groupby("date_only", as_index=False)["Appliances"]
    .mean()
)

daily.columns = ["Date", "Average Consumption (Wh)"]

fig_daily = px.line(
    daily,
    x="Date",
    y="Average Consumption (Wh)",
    markers=True,
    title="Daily Average Appliance Consumption"
)

fig_daily.update_layout(
    xaxis_title="Date",
    yaxis_title="Average Consumption (Wh)"
)

st.plotly_chart(fig_daily, use_container_width=True)

# ---------------- DAY-OF-WEEK ANALYSIS ----------------
st.subheader("📅 Consumption by Day of the Week")

day_order = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday"
]

day_usage = (
    filtered.groupby("day")["Appliances"]
    .mean()
    .reindex(day_order)
    .dropna()
    .rename("Average Consumption (Wh)")
    .reset_index()
)

day_usage = day_usage.rename(columns={"day": "Day"})

fig_day = px.bar(
    day_usage,
    x="Day",
    y="Average Consumption (Wh)",
    title="Average Consumption by Day",
    color="Average Consumption (Wh)",
    color_continuous_scale="Teal"
)

fig_day.update_layout(coloraxis_showscale=False)

st.plotly_chart(fig_day, use_container_width=True)

# ---------------- CONSUMPTION DISTRIBUTION ----------------
st.subheader("📊 Consumption Distribution")

fig_hist = px.histogram(
    filtered,
    x="Appliances",
    nbins=30,
    marginal="box",
    title="Distribution of Appliance Energy Readings",
    labels={"Appliances": "Appliance Consumption (Wh)"}
)

st.plotly_chart(fig_hist, use_container_width=True)

# ---------------- TEMPERATURE ANALYSIS ----------------
if "T_out" in filtered.columns:
    st.subheader("🌡️ Temperature and Energy Consumption")

    temp_df = filtered[["T_out", "Appliances"]].copy()
    temp_df["T_out"] = pd.to_numeric(
        temp_df["T_out"], errors="coerce"
    )
    temp_df = temp_df.dropna()

    if not temp_df.empty:
        fig_temp = px.scatter(
            temp_df,
            x="T_out",
            y="Appliances",
            opacity=0.5,
            title="Outside Temperature vs Appliance Consumption",
            labels={
                "T_out": "Outside Temperature",
                "Appliances": "Appliance Consumption (Wh)"
            }
        )

        st.plotly_chart(fig_temp, use_container_width=True)

        corr = temp_df["T_out"].corr(temp_df["Appliances"])

        st.write(
            f"Pearson correlation between outside temperature "
            f"and appliance readings: **{corr:.3f}**"
        )

        st.caption(
            "Correlation describes a linear association and does not "
            "prove that temperature causes changes in energy use."
        )

# ---------------- CORRELATION ANALYSIS ----------------
st.subheader("🔗 Relationships Between Variables")

numeric_df = filtered.select_dtypes(include="number")
numeric_df = numeric_df.loc[:, numeric_df.nunique() > 1]

if numeric_df.shape[1] >= 2:
    corr_matrix = numeric_df.corr()

    if "Appliances" in corr_matrix.columns:
        appliance_corr = (
            corr_matrix["Appliances"]
            .drop("Appliances")
            .dropna()
        )

        if not appliance_corr.empty:
            st.write("Variables most positively associated with Appliances:")
            st.dataframe(
                appliance_corr.sort_values(ascending=False)
                .head(5)
                .rename("Correlation")
                .to_frame(),
                use_container_width=True
            )

    fig_corr = px.imshow(
        corr_matrix,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        title="Correlation Heatmap"
    )

    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("Not enough varying numeric columns for correlation analysis.")

# ---------------- OPTIMIZATION INSIGHTS ----------------
st.divider()
st.subheader("💡 Energy Optimization Insights")

st.markdown(
    """
    Use the patterns above to decide which actions deserve investigation:

    - **Peak-hour review:** Investigate which appliances contribute to
      high-consumption periods.
    - **Standby-power reduction:** Check whether equipment can be switched
      off when it is not needed.
    - **Temperature-related usage:** Review cooling and heating settings
      where relevant.
    - **Unusual readings:** Investigate large spikes before deciding whether
      they indicate faults or normal activity.

    These are potential recommendations. The dataset alone does not prove
    that energy was wasted or that a particular intervention will save energy.
    """
)

# ---------------- DOWNLOAD FILTERED DATA ----------------
st.subheader("⬇️ Export Data")

csv_data = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Filtered Dataset (CSV)",
    data=csv_data,
    file_name="filtered_energy_data.csv",
    mime="text/csv"
)

st.caption(
    "Smart Energy Consumption & Optimization | "
    "Exploratory Data Analysis Project"
)
