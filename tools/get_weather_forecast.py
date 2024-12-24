
import requests
import json
from geopy.geocoders import Nominatim

def get_weather_forecast(zip_code):
    try:
        # Initialize geocoder
        geolocator = Nominatim(user_agent="weather_forecast_app")
        
        # Get location coordinates from ZIP code
        location = geolocator.geocode(zip_code)
        if not location:
            return {"error": "Unable to find coordinates for the given ZIP code"}
        
        # Get NWS grid point
        grid_url = f"https://api.weather.gov/points/{location.latitude},{location.longitude}"
        grid_response = requests.get(grid_url, headers={'User-Agent': 'WeatherApp/1.0'})
        grid_data = grid_response.json()
        
        if grid_response.status_code != 200:
            return {"error": "Unable to retrieve grid information"}
        
        # Get forecast
        forecast_url = grid_data['properties']['forecast']
        forecast_response = requests.get(forecast_url, headers={'User-Agent': 'WeatherApp/1.0'})
        forecast_data = forecast_response.json()
        
        if forecast_response.status_code != 200:
            return {"error": "Unable to retrieve forecast"}
        
        # Extract key forecast information
        periods = forecast_data['properties']['periods']
        forecast_summary = []
        for period in periods[:4]:  # First 4 periods
            forecast_summary.append({
                "name": period['name'],
                "temperature": f"{period['temperature']}°{period['temperatureUnit']}",
                "short_forecast": period['shortForecast'],
                "detailed_forecast": period['detailedForecast']
            })
        
        return {
            "location": f"{location.address}",
            "forecast": forecast_summary
        }
    
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
