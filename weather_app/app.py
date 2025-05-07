import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils import fetch_weather_forecast, process_forecast_data

# Climate Normals for Plovdiv
NORMALS = {
    "January": {"temp": 1.5, "rain_days": 5},
    "February": {"temp": 3.5, "rain_days": 4},
    "March": {"temp": 7.5, "rain_days": 5},
    "April": {"temp": 12.5, "rain_days": 6},
    "May": {"temp": 17.5, "rain_days": 8},
    "June": {"temp": 21.5, "rain_days": 7},
    "July": {"temp": 24.0, "rain_days": 5},
    "August": {"temp": 23.5, "rain_days": 4},
    "September": {"temp": 19.0, "rain_days": 4},
    "October": {"temp": 13.0, "rain_days": 5},
    "November": {"temp": 7.5, "rain_days": 6},
    "December": {"temp": 2.5, "rain_days": 6},
}

# --- Streamlit App ---
st.set_page_config(page_title="Weather Analyzer Plovdiv", layout="wide")
st.title("🌦️ Weather Analysis for Plovdiv")

# API Key Configuration
st.sidebar.header("Configuration")

# Try to load API key from secrets
api_key = ""
if "OPENWEATHERMAP_API_KEY" in st.secrets and st.secrets["OPENWEATHERMAP_API_KEY"] != "YOUR_API_KEY_HERE" and st.secrets["OPENWEATHERMAP_API_KEY"]:
    api_key = st.secrets["OPENWEATHERMAP_API_KEY"]
else:
    st.sidebar.error("🛑 OpenWeatherMap API Key not found or is placeholder. ")
    st.sidebar.markdown("Please ensure `OPENWEATHERMAP_API_KEY` is correctly set in your `.streamlit/secrets.toml` file.")
    st.error("API Key not configured. Please check sidebar instructions.")
    st.stop() # Stop execution if no valid API key


# City Input (default to Plovdiv)
city_name = st.sidebar.text_input("Enter City Name", "Plovdiv")

# Month Selector (optional override)
current_month_name = datetime.now().strftime("%B")
available_months = list(NORMALS.keys())
if current_month_name not in available_months: # Fallback if current month not in NORMALS
    current_month_name = available_months[datetime.now().month -1]

selected_month = st.sidebar.selectbox(
    "Select Month for Comparison",
    options=available_months,
    index=available_months.index(current_month_name) # Default to current month
)

# Cache data fetching
@st.cache_data
def get_weather_data(api_key_param, city_name_param):
    if not api_key_param:
        return None, "API Key is missing."
    try:
        forecast_json = fetch_weather_forecast(api_key_param, city_name_param)
        return forecast_json, None
    except Exception as e:
        return None, f"Error fetching data: {e}"

if st.sidebar.button("Analyze Weather"):
    if not api_key:
        st.error("🚫 API Key is missing. Please enter it in the sidebar.")
    elif not city_name:
        st.error("🏙️ City Name is missing. Please enter it in the sidebar.")
    else:
        with st.spinner(f"Fetching weather data for {city_name}..."):
            forecast_data, error_message = get_weather_data(api_key, city_name)

        if error_message:
            st.error(error_message)
        elif forecast_data:
            st.success(f"Successfully fetched weather data for {city_name}!")

            daily_summary_df, rainy_days_count, overall_avg_temp = process_forecast_data(forecast_data)

            if daily_summary_df.empty:
                st.warning("Could not process weather data. The API might have returned an unexpected format or no forecast data.")
            else:
                st.subheader("📅 7-Day Weather Forecast Summary")

                col1, col2, col3 = st.columns(3)
                col1.metric("Avg. Temperature (7 days)", f"{overall_avg_temp:.1f} °C")
                col2.metric("Total Rainy Days (in next 7 days)", f"{rainy_days_count} day(s)")
                
                # Calculate total precipitation for display if column exists
                total_precipitation_sum = 0
                if 'total_precipitation' in daily_summary_df.columns:
                    total_precipitation_sum = daily_summary_df['total_precipitation'].sum()
                col3.metric("Total Precipitation (next 7 days)", f"{total_precipitation_sum:.1f} mm")


                st.markdown("---")
                st.subheader("📊 Visualizations")

                # Temperature Chart
                if 'date' in daily_summary_df.columns and 'avg_temp' in daily_summary_df.columns:
                    fig_temp = px.line(
                        daily_summary_df,
                        x='date',
                        y='avg_temp',
                        title='Average Daily Temperature (°C)',
                        labels={'date': 'Date', 'avg_temp': 'Avg. Temperature (°C)'},
                        markers=True
                    )
                    fig_temp.update_traces(line_color='#FF6347') # Tomato color
                    st.plotly_chart(fig_temp, use_container_width=True)
                else:
                    st.warning("Temperature data columns not found for plotting.")


                # Precipitation Chart
                if 'date' in daily_summary_df.columns and 'total_precipitation' in daily_summary_df.columns:
                    fig_precip = px.bar(
                        daily_summary_df,
                        x='date',
                        y='total_precipitation',
                        title='Total Daily Precipitation (mm)',
                        labels={'date': 'Date', 'total_precipitation': 'Precipitation (mm)'}
                    )
                    fig_precip.update_traces(marker_color='#1E90FF') # DodgerBlue color
                    st.plotly_chart(fig_precip, use_container_width=True)
                else:
                    st.warning("Precipitation data columns not found for plotting.")


                st.markdown("---")
                st.subheader(f"🧐 Is the Weather Unusual for {selected_month}?")

                if selected_month in NORMALS:
                    norm_temp = NORMALS[selected_month]["temp"]
                    norm_rain_days = NORMALS[selected_month]["rain_days"]

                    st.markdown(f"**Climate Norms for {selected_month}:**")
                    st.markdown(f"- Average Temperature: {norm_temp}°C")
                    st.markdown(f"- Expected Rainy Days: {norm_rain_days} days")
                    st.markdown("")


                    # Temperature Comparison
                    temp_diff_threshold = 2  # Degrees Celsius
                    if overall_avg_temp > norm_temp + temp_diff_threshold:
                        st.warning(f"⚠️ Temperatures ({overall_avg_temp:.1f}°C) are unusually high compared to the {selected_month} average of {norm_temp}°C!")
                    elif overall_avg_temp < norm_temp - temp_diff_threshold:
                        st.warning(f"⚠️ Temperatures ({overall_avg_temp:.1f}°C) are unusually low compared to the {selected_month} average of {norm_temp}°C!")
                    else:
                        st.success(f"✅ Temperatures ({overall_avg_temp:.1f}°C) are within the normal range for {selected_month} (around {norm_temp}°C).")

                    # Rainy Days Comparison
                    rain_days_diff_threshold = 2 # Days
                    # Note: We are comparing 7-day forecast rainy days with monthly norm.
                    # This comparison might not be perfectly direct but gives an indication.
                    # For a more accurate comparison, we might need to scale the forecast or have weekly norms.
                    # For now, we state this caveat.
                    st.caption(f"Note: Comparing {rainy_days_count} rainy days in the upcoming 7-day forecast against the typical {norm_rain_days} rainy days for the entire month of {selected_month}.")

                    if rainy_days_count > norm_rain_days / 4 + rain_days_diff_threshold : # Rough scaling: monthly days / 4 weeks
                        st.info(f"🌧️ It looks like there might be more rainy days ({rainy_days_count} in 7 days) than typical for {selected_month} (norm: {norm_rain_days} days/month).")
                    elif rainy_days_count < norm_rain_days / 4 - rain_days_diff_threshold and norm_rain_days / 4 - rain_days_diff_threshold > 0 :
                         st.info(f"☀️ It looks like there might be fewer rainy days ({rainy_days_count} in 7 days) than typical for {selected_month} (norm: {norm_rain_days} days/month).")
                    else:
                        st.success(f"✅ The number of rainy days ({rainy_days_count} in 7 days) seems relatively normal for this period, considering the monthly average for {selected_month} ({norm_rain_days} days/month).")

                else:
                    st.error(f"Climate normals not available for {selected_month}.")
else:
    st.info("Click 'Analyze Weather' in the sidebar to fetch and display the forecast.")

st.sidebar.markdown("---")
st.sidebar.markdown("Built with [Streamlit](https.streamlit.io) by an AI Assistant.") 