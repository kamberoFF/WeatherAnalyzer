# Helper functions for the Weather Analyzer App 
import requests
import pandas as pd
from datetime import datetime

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
    """Processes raw forecast data to get daily aggregates."""
    if not forecast_data or 'list' not in forecast_data:
        return pd.DataFrame(), 0, 0.0

    processed_data = []
    for item in forecast_data['list']:
        dt_object = datetime.fromtimestamp(item['dt'])
        processed_data.append({
            'date': dt_object.date(),
            'temp': item['main']['temp'],
            'precipitation': item.get('rain', {}).get('3h', 0)  # rain.3h if exists, else 0
        })

    if not processed_data:
        return pd.DataFrame(), 0, 0.0

    df = pd.DataFrame(processed_data)

    # Aggregate by day
    daily_summary = df.groupby('date').agg(
        avg_temp=('temp', 'mean'),
        total_precipitation=('precipitation', 'sum')
    ).reset_index()

    # Ensure we have data for 7 days, even if API returns less for the start/end
    # This part might need refinement based on exact API behavior for "7 days"
    # For now, we'll take up to the first 7 unique days available.
    daily_summary = daily_summary.head(7)


    # Count rainy days
    rainy_days_count = daily_summary[daily_summary['total_precipitation'] > 0]['date'].nunique()

    # Overall average temperature for the period
    overall_avg_temp = daily_summary['avg_temp'].mean() if not daily_summary.empty else 0.0

    return daily_summary, rainy_days_count, overall_avg_temp 