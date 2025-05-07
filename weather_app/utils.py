# Helper functions for the Weather Analyzer App 
import requests
import pandas as pd
from datetime import datetime, date # Added date for type hinting

def fetch_weather_forecast(api_key, city_name="Plovdiv"):
    """Fetches 5-day/3-hour weather forecast from OpenWeatherMap API."""
    base_url = "http://api.openweathermap.org/data/2.5/forecast"
    params = {
        "q": city_name,
        "appid": api_key,
        "units": "metric"
    }
    response = requests.get(base_url, params=params)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return response.json()

def process_forecast_data(forecast_data):
    """Processes raw forecast data to get daily aggregates relevant for farmers."""
    if not forecast_data or 'list' not in forecast_data:
        cols = ['date', 'avg_temp', 'min_temp', 'max_temp', 'avg_humidity', 
                'total_precipitation', 'avg_wind_speed', 'max_wind_speed', 'max_wind_gust',
                'max_pop', 'avg_cloud_cover', 'avg_visibility']
        return pd.DataFrame(columns=cols), 0, 0.0, 0.0

    processed_data = []
    for item in forecast_data['list']:
        dt_object = datetime.fromtimestamp(item['dt'])
        processed_data.append({
            'datetime': dt_object,
            'date': dt_object.date(),
            'temp': item['main']['temp'],
            'temp_min_3hr': item['main']['temp_min'],
            'temp_max_3hr': item['main']['temp_max'],
            'humidity': item['main']['humidity'],
            'precipitation': item.get('rain', {}).get('3h', 0),
            'wind_speed': item.get('wind', {}).get('speed', 0),
            'wind_gust': item.get('wind', {}).get('gust', 0),
            'pop': item.get('pop', 0) * 100,
            'cloud_cover': item.get('clouds', {}).get('all', 0),
            'visibility': item.get('visibility', 10000)
        })

    if not processed_data:
        cols = ['date', 'avg_temp', 'min_temp', 'max_temp', 'avg_humidity', 
                'total_precipitation', 'avg_wind_speed', 'max_wind_speed', 'max_wind_gust',
                'max_pop', 'avg_cloud_cover', 'avg_visibility']
        return pd.DataFrame(columns=cols), 0, 0.0, 0.0

    df = pd.DataFrame(processed_data)

    daily_summary = df.groupby('date').agg(
        avg_temp=('temp', 'mean'),
        min_temp=('temp_min_3hr', 'min'),
        max_temp=('temp_max_3hr', 'max'),
        avg_humidity=('humidity', 'mean'),
        total_precipitation=('precipitation', 'sum'),
        avg_wind_speed=('wind_speed', 'mean'),
        max_wind_speed=('wind_speed', 'max'),
        max_wind_gust=('wind_gust', 'max'),
        max_pop=('pop', 'max'),
        avg_cloud_cover=('cloud_cover', 'mean'),
        avg_visibility=('visibility', 'mean')
    ).reset_index()

    daily_summary = daily_summary.head(7)

    rainy_days_count = daily_summary[daily_summary['total_precipitation'] > 0]['date'].nunique()
    overall_avg_temp = daily_summary['avg_temp'].mean() if not daily_summary.empty else 0.0
    overall_avg_humidity = daily_summary['avg_humidity'].mean() if not daily_summary.empty else 0.0

    return daily_summary, rainy_days_count, overall_avg_temp, overall_avg_humidity

def calculate_gdd(daily_df, base_temp):
    """Calculates Growing Degree Days (GDD) for each day and cumulative GDD.
    GDD = ((T_max + T_min) / 2) - T_base
    If (T_max + T_min) / 2 < T_base, GDD for the day is 0.
    T_min cannot be below T_base for calculation (effectively, if actual T_min < T_base, use T_base).
    If T_max < T_base, GDD is 0.
    """
    if daily_df.empty or not all(col in daily_df.columns for col in ['min_temp', 'max_temp']):
        return daily_df # Return original df if columns are missing
    
    gdd_series = []
    for index, row in daily_df.iterrows():
        t_max = row['max_temp']
        t_min = row['min_temp']

        # Adjust T_min: if T_min < base_temp, use base_temp for GDD calculation part
        # However, if T_max itself is less than base_temp, GDD is 0.
        if t_max < base_temp:
            daily_gdd = 0.0
        else:
            # Effective T_min for GDD calculation (cannot go below base_temp)
            eff_t_min = max(t_min, base_temp)
            avg_daily_temp_for_gdd = (t_max + eff_t_min) / 2
            if avg_daily_temp_for_gdd < base_temp:
                 daily_gdd = 0.0
            else:
                 daily_gdd = avg_daily_temp_for_gdd - base_temp
        gdd_series.append(daily_gdd)
    
    daily_df['gdd'] = gdd_series
    daily_df['cumulative_gdd'] = daily_df['gdd'].cumsum()
    return daily_df 