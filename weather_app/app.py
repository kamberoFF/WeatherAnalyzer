import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils import fetch_weather_forecast, process_forecast_data, calculate_gdd

# Climate Normals for Plovdiv (Can be expanded or made farmer-specific if needed)
NORMALS = {
    "January": {"temp": 1.5, "rain_days": 5, "frost_days": 20},
    "February": {"temp": 3.5, "rain_days": 4, "frost_days": 15},
    "March": {"temp": 7.5, "rain_days": 5, "frost_days": 10},
    "April": {"temp": 12.5, "rain_days": 6, "frost_days": 2},
    "May": {"temp": 17.5, "rain_days": 8, "frost_days": 0},
    "June": {"temp": 21.5, "rain_days": 7, "frost_days": 0},
    "July": {"temp": 24.0, "rain_days": 5, "frost_days": 0},
    "August": {"temp": 23.5, "rain_days": 4, "frost_days": 0},
    "September": {"temp": 19.0, "rain_days": 4, "frost_days": 1},
    "October": {"temp": 13.0, "rain_days": 5, "frost_days": 5},
    "November": {"temp": 7.5, "rain_days": 6, "frost_days": 12},
    "December": {"temp": 2.5, "rain_days": 6, "frost_days": 18},
}

# --- Predefined Crop Data ---
CROP_DATA = {
    "Generic (10°C)": {"gdd_base": 10.0},
    "Corn/Maize": {"gdd_base": 10.0, "notes": "Typically requires significant GDDs."},
    "Wheat": {"gdd_base": 5.0, "notes": "Cool season crop, sensitive to spring frosts during flowering."},
    "Barley": {"gdd_base": 5.0, "notes": "Similar to wheat, generally hardy."},
    "Soybean": {"gdd_base": 10.0, "notes": "Warm season crop."},
    "Sunflower": {"gdd_base": 7.0, "notes": "Needs warm conditions for optimal growth."},
    "Potato": {"gdd_base": 7.0, "notes": "Cool weather crop, tubers sensitive to frost."} 
    # Add more crops as needed
}

# --- Streamlit App ---
st.set_page_config(page_title="Farmer's Weather Dashboard", layout="wide")
st.title("🌾 Farmer's Weather Dashboard")
st.markdown("Weekly weather insights for agricultural planning.")

# API Key Configuration
st.sidebar.header("⚙️ Configuration")

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

# Crop Selection
selected_crop_name = st.sidebar.selectbox(
    "Select Crop for Analysis",
    options=list(CROP_DATA.keys()),
    index=0, # Default to Generic
    help="Selecting a crop will pre-fill the GDD Base Temperature. You can still adjust it manually."
)

# GDD Base Temperature Input - value updated by crop selection
gdd_base_temp_default = CROP_DATA[selected_crop_name]["gdd_base"]
gdd_base_temp = st.sidebar.number_input(
    "GDD Base Temperature (°C)",
    min_value=-10.0, max_value=30.0, value=gdd_base_temp_default, step=0.5,
    help="Adjust for your specific crop variety and local conditions if needed."
)

# Month Selector (optional override)
current_month_name = datetime.now().strftime("%B")
available_months = list(NORMALS.keys())
if current_month_name not in available_months: # Fallback if current month not in NORMALS
    current_month_name = available_months[datetime.now().month -1]

selected_month = st.sidebar.selectbox(
    "Select Month for Climate Comparison",
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

if st.sidebar.button("🚜 Analyze Farm Weather"):
    if not api_key or not city_name:
        st.error("🚫 API Key or City Name is missing. Please check the sidebar.")
    else:
        with st.spinner(f"Fetching weather intelligence for {city_name}..."):
            forecast_data, error_message = get_weather_data(api_key, city_name)

        if error_message:
            st.error(error_message)
        elif forecast_data:
            st.success(f"Successfully fetched weather data for {city_name}!")

            daily_summary_df, rainy_days_count, overall_avg_temp, overall_avg_humidity = process_forecast_data(forecast_data)

            if daily_summary_df.empty or not all(col in daily_summary_df.columns for col in ['min_temp', 'max_temp', 'avg_humidity', 'total_precipitation', 'avg_wind_speed', 'max_wind_gust', 'max_pop', 'avg_cloud_cover']):
                st.warning("Could not process all required weather data fields. Some features might be unavailable.")
                # Still try to calculate GDD if basic temp data is there
                if 'min_temp' in daily_summary_df.columns and 'max_temp' in daily_summary_df.columns:
                    daily_summary_df_with_gdd = calculate_gdd(daily_summary_df.copy(), gdd_base_temp)
                else:
                    daily_summary_df_with_gdd = daily_summary_df.copy() # or an empty df with gdd columns
            else:
                daily_summary_df_with_gdd = calculate_gdd(daily_summary_df.copy(), gdd_base_temp)
            
            total_gdd_forecast = daily_summary_df_with_gdd['cumulative_gdd'].iloc[-1] if 'cumulative_gdd' in daily_summary_df_with_gdd and not daily_summary_df_with_gdd.empty else 0

            st.subheader("📅 7-Day Agricultural Weather Outlook")
            k_col1, k_col2, k_col3, k_col4 = st.columns(4)
            k_col1.metric("Avg. Temp (7d)", f"{overall_avg_temp:.1f} °C")
            k_col2.metric(f"Total GDD ({selected_crop_name}, 7d)", f"{total_gdd_forecast:.1f}", help=f"Base Temp: {gdd_base_temp}°C")
            k_col3.metric("Rainy Days (7d)", f"{rainy_days_count} day(s)")
            total_precip_sum = daily_summary_df_with_gdd['total_precipitation'].sum() if 'total_precipitation' in daily_summary_df_with_gdd else 0
            k_col4.metric("Total Precip. (7d)", f"{total_precip_sum:.1f} mm")

            with st.expander("View Detailed Daily Forecast Data", expanded=False):
                if not daily_summary_df_with_gdd.empty:
                    cols_for_display = ['date', 'min_temp', 'max_temp', 'avg_humidity', 'total_precipitation', 'gdd', 
                                        'avg_wind_speed', 'max_wind_gust', 'max_pop', 'avg_cloud_cover', 'avg_visibility']
                    available_cols = [col for col in cols_for_display if col in daily_summary_df_with_gdd.columns]
                    display_df = daily_summary_df_with_gdd[available_cols].copy()
                    
                    new_column_names = {
                        'date': 'Date', 'min_temp': 'Min Temp (°C)', 'max_temp': 'Max Temp (°C)',
                        'avg_humidity': 'Avg Humidity (%)', 'total_precipitation': 'Precip. (mm)',
                        'gdd': f'GDD ({gdd_base_temp}°C)', 'avg_wind_speed': 'Avg Wind (m/s)',
                        'max_wind_gust': 'Max Gust (m/s)', 'max_pop': 'Max PoP (%)',
                        'avg_cloud_cover': 'Avg Clouds (%)',
                        'avg_visibility': 'Avg Visibility (m)'
                    }
                    display_df.rename(columns=new_column_names, inplace=True)
                    
                    column_formats = {}
                    for col_name in display_df.columns:
                        if col_name != 'Date':
                            display_df[col_name] = pd.to_numeric(display_df[col_name], errors='coerce')
                            if col_name == 'Avg Visibility (m)':
                                column_formats[col_name] = "{:,.0f}"
                            else:
                                column_formats[col_name] = "{:.1f}"
                    
                    st.dataframe(
                        display_df.set_index('Date' if 'Date' in display_df.columns else None),
                        use_container_width=True,
                        column_config=column_formats
                    )
                else:
                    st.info("No detailed daily data to display.")

            st.markdown("---")
            st.subheader("📊 Visualizations for Farm Planning")
            charts_col1, charts_col2 = st.columns(2)

            with charts_col1:
                if 'date' in daily_summary_df_with_gdd.columns and all(c in daily_summary_df_with_gdd for c in ['min_temp', 'max_temp', 'avg_temp']):
                    fig_temp = px.line(daily_summary_df_with_gdd, x='date', y=['min_temp', 'max_temp', 'avg_temp'], title='Daily Min, Max & Avg Temperatures (°C)', labels={'date': 'Date', 'value': 'Temperature (°C)'}, markers=True)
                    st.plotly_chart(fig_temp, use_container_width=True)
                if 'date' in daily_summary_df_with_gdd.columns and 'total_precipitation' in daily_summary_df_with_gdd.columns:
                    fig_precip = px.bar(daily_summary_df_with_gdd, x='date', y='total_precipitation', title='Total Daily Precipitation (mm)', labels={'date': 'Date', 'total_precipitation': 'Precipitation (mm)'})
                    fig_precip.update_traces(marker_color='#1E90FF')
                    st.plotly_chart(fig_precip, use_container_width=True)
                if 'date' in daily_summary_df_with_gdd.columns and all(c in daily_summary_df_with_gdd for c in ['avg_wind_speed', 'max_wind_gust']):
                    fig_wind = px.line(daily_summary_df_with_gdd, x='date', y=['avg_wind_speed', 'max_wind_gust'], title='Daily Avg. Wind Speed & Max Gust (m/s)', labels={'date': 'Date', 'value': 'Wind Speed (m/s)'}, markers=True)
                    st.plotly_chart(fig_wind, use_container_width=True)

            with charts_col2:
                if 'date' in daily_summary_df_with_gdd.columns and 'cumulative_gdd' in daily_summary_df_with_gdd.columns:
                    fig_gdd = px.line(daily_summary_df_with_gdd, x='date', y='cumulative_gdd', title=f'Cumulative GDD for {selected_crop_name} (Base {gdd_base_temp}°C)', labels={'date': 'Date', 'cumulative_gdd': 'Cumulative GDD'}, markers=True)
                    fig_gdd.update_traces(line_color='#228B22')
                    st.plotly_chart(fig_gdd, use_container_width=True)
                if 'date' in daily_summary_df_with_gdd.columns and 'avg_humidity' in daily_summary_df_with_gdd.columns:
                    fig_humidity = px.line(daily_summary_df_with_gdd, x='date', y='avg_humidity', title='Average Daily Humidity (%)', labels={'date': 'Date', 'avg_humidity': 'Avg. Humidity (%)'}, markers=True)
                    fig_humidity.update_traces(line_color='#87CEEB')
                    st.plotly_chart(fig_humidity, use_container_width=True)
                if 'date' in daily_summary_df_with_gdd.columns and all(c in daily_summary_df_with_gdd for c in ['max_pop', 'avg_cloud_cover']):
                    fig_pop_clouds = px.line(daily_summary_df_with_gdd, x='date', y=['max_pop', 'avg_cloud_cover'], title='Max PoP & Avg Cloud Cover (%)', labels={'date': 'Date', 'value': 'Percentage (%)'}, markers=True)
                    st.plotly_chart(fig_pop_clouds, use_container_width=True)
            
            st.markdown("---")
            st.subheader(f"🌾 Agricultural Advisory for {selected_month} (and 7-day Outlook)")
            
            # Frost Warnings
            frost_threshold_input = st.sidebar.number_input(
                "Frost Alarm Temperature (°C)",
                min_value=-5.0, max_value=10.0, value=2.0, step=0.5,
                help="Set the temperature below which you consider a frost risk for your crops."
            )
            frost_days_forecast = daily_summary_df_with_gdd[daily_summary_df_with_gdd['min_temp'] < frost_threshold_input]
            if not frost_days_forecast.empty:
                st.warning(f"🥶 FROST RISK: {len(frost_days_forecast)} day(s) in the next 7 days with minimum temperatures below {frost_threshold_input}°C.")
                st.write("Dates with potential frost:")
                for _, row in frost_days_forecast.iterrows():
                    st.write(f"  - {row['date'].strftime('%A, %B %d')}: Min Temp {row['min_temp']:.1f}°C")
                st.markdown("Consider protective measures for sensitive crops.")
            else:
                st.success(f"✅ No immediate frost risk (below {frost_threshold_input}°C) in the 7-day forecast.")

            # Heat Stress Advisory
            if 'max_temp' in daily_summary_df_with_gdd.columns:
                heat_stress_threshold = 30 # Example threshold
                heat_stress_days = daily_summary_df_with_gdd[daily_summary_df_with_gdd['max_temp'] > heat_stress_threshold]
                if not heat_stress_days.empty:
                    st.warning(f"🥵 HEAT STRESS RISK: {len(heat_stress_days)} day(s) with temperatures above {heat_stress_threshold}°C.")
                    st.markdown("Ensure adequate water for crops and provide shade/ventilation for livestock if applicable.")

            # Spraying Advisory
            if 'avg_wind_speed' in daily_summary_df_with_gdd.columns and 'max_wind_gust' in daily_summary_df_with_gdd.columns:
                ideal_wind_lower = 1.5  # m/s (approx 5.4 km/h)
                ideal_wind_upper = 4.5  # m/s (approx 16.2 km/h)
                gust_limit = 6.0 # m/s
                
                st.info("**Spraying Conditions Advisory (general guidance):**")
                can_spray_days = []
                caution_spray_days = []
                for index, row in daily_summary_df_with_gdd.iterrows():
                    day_str = row['date'].strftime('%A, %b %d')
                    avg_ws = row['avg_wind_speed']
                    max_g = row['max_wind_gust']
                    if ideal_wind_lower <= avg_ws <= ideal_wind_upper and max_g < gust_limit:
                        can_spray_days.append(f"{day_str} (Avg: {avg_ws:.1f} m/s, Gust: {max_g:.1f} m/s)")
                    elif avg_ws < ideal_wind_lower:
                        caution_spray_days.append(f"{day_str}: Low wind (potential drift issues if too calm or inversion). Avg: {avg_ws:.1f} m/s.") 
                    else:
                        caution_spray_days.append(f"{day_str}: High wind/gusts (risk of drift). Avg: {avg_ws:.1f} m/s, Gust: {max_g:.1f} m/s.")
                if can_spray_days:
                    st.success(f"🌬️ Favorable spraying windows on: {', '.join(can_spray_days)}. Always verify on-site.")
                if caution_spray_days:
                    st.warning(f"🌬️ Caution for spraying on other days: {'; '.join(caution_spray_days)}. Verify on-site conditions.")
                st.caption("Ideal wind for spraying is generally between 5-15 km/h (1.5-4.5 m/s). Avoid high gusts. Local conditions & regulations paramount.")

            # Precipitation Chance
            if 'max_pop' in daily_summary_df_with_gdd.columns:
                high_pop_days = daily_summary_df_with_gdd[daily_summary_df_with_gdd['max_pop'] > 60]
                if not high_pop_days.empty:
                    days_str = ", ".join(high_pop_days['date'].apply(lambda x: x.strftime('%A')))
                    st.info(f"💧 High chance of rain (PoP > 60%) on: {days_str}. Plan field activities accordingly.")
            
            # Drying Conditions
            # This is a more qualitative assessment
            # ... (can add a simple heuristic based on low humidity, some wind, no rain)

            # Climate Normals Comparison (remains largely the same, but context is now 7-day outlook)
            if selected_month in NORMALS:
                norm_temp = NORMALS[selected_month]["temp"]
                norm_rain_days = NORMALS[selected_month]["rain_days"]
                norm_frost_days = NORMALS[selected_month].get("frost_days", 0)

                st.markdown(f"**Climate Normals for {selected_month} in {city_name}:**")
                st.markdown(f"- Avg. Temperature: {norm_temp}°C")
                st.markdown(f"- Expected Rainy Days: {norm_rain_days} days/month")
                st.markdown(f"- Typical Frost Days: {norm_frost_days} days/month")
                st.markdown("")
                
                if overall_avg_temp > norm_temp + 2:
                    st.info(f"🌡️ Warmer than Usual: Forecasted average ({overall_avg_temp:.1f}°C) is higher than the {selected_month} norm ({norm_temp}°C). This could accelerate crop growth, increase water demand, and affect pest cycles.")
                elif overall_avg_temp < norm_temp - 2:
                    st.info(f"🌡️ Cooler than Usual: Forecasted average ({overall_avg_temp:.1f}°C) is lower than norm. This might slow crop development. Monitor GDDs closely.")
                else:
                    st.success(f"🌡️ Temperatures appear to be within the typical range for {selected_month}.")

                if rainy_days_count > (norm_rain_days / 4) + 1:
                    st.info(f"🌧️ Wetter Conditions Expected: {rainy_days_count} rainy days forecasted. The monthly average is {norm_rain_days} days. This may delay field access but replenish soil moisture. Monitor for waterlogging and disease.")
                elif rainy_days_count < (norm_rain_days / 4) - 1 and (norm_rain_days / 4) - 1 > 0:
                    st.info(f"☀️ Drier Conditions Expected: {rainy_days_count} rainy days forecasted. This is less than typical for a week in {selected_month}. Monitor soil moisture closely and prepare for potential irrigation needs.")
                else:
                    st.success(f"🌧️ Precipitation levels seem typical for this period of {selected_month}.")

                if overall_avg_humidity > 75:
                    st.warning(f"⚠️ High Humidity Advisory ({overall_avg_humidity:.0f}% average): Sustained high humidity can increase the risk of fungal diseases. Promote air circulation where possible and monitor crops.")
            else:
                st.error(f"Climate normals not available for {selected_month}.")
        else:
            st.info("Click 'Analyze Farm Weather' in the sidebar to fetch and display the forecast.")

st.sidebar.markdown("---")
st.sidebar.markdown("🚜 Focused Weather for Smart Farming.") 