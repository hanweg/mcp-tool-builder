import requests
import json
from datetime import datetime

def get_temperature(zip_code):
    try:
        # Get coordinates from zip code
        geocode_url = f"https://geocoding.geo.census.gov/geocoder/locations/address?benchmark=2020&format=json&zip={zip_code}"
        geocode_response = requests.get(geocode_url)
        geocode_response.raise_for_status()
        geocode_data = geocode_response.json()
        
        if not geocode_data['result']['addressMatches']:
            return {"error": "Invalid ZIP code"}
            
        coordinates = geocode_data['result']['addressMatches'][0]['coordinates']
        lat, lon = coordinates['y'], coordinates['x']
        
        # Get NWS grid points
        points_url = f"https://api.weather.gov/points/{lat},{lon}"
        points_response = requests.get(points_url, headers={'User-Agent': 'Temperature Checker 1.0'})
        points_response.raise_for_status()
        points_data = points_response.json()
        
        # Get temperature from forecast
        forecast_url = points_data['properties']['forecast']
        forecast_response = requests.get(forecast_url, headers={'User-Agent': 'Temperature Checker 1.0'})
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        current_temp = forecast_data['properties']['periods'][0]['temperature']
        units = forecast_data['properties']['periods'][0]['temperatureUnit']
        
        return {
            "temperature": current_temp,
            "units": units,
            "timestamp": datetime.now().isoformat()
        }
        
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return {"error": f"Data parsing error: {str(e)}"}