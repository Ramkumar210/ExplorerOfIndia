# pages/weather_predictor.py

import streamlit as st
import requests
import datetime
import json
from collections import Counter

# --- Configuration ---
st.set_page_config(layout="wide", page_title="Weather Predictor")

# --- API Keys ---
# IMPORTANT: Store your API keys securely using Streamlit Secrets.
# Create a .streamlit/secrets.toml file with:
# OPENWEATHER_API_KEY="your_openweathermap_api_key_here"
try:
    # Using OpenWeatherMap API key
    OPENWEATHER_API_KEY = st.secrets["OPENWEATHER_API_KEY"]
    api_keys_available = True
except KeyError:
    st.error("🚨 **OpenWeatherMap API key is missing.** Please add it to your Streamlit secrets.toml file.")
    st.info("You can get a free API key from https://openweathermap.org/api")
    api_keys_available = False
    OPENWEATHER_API_KEY = "5a81057a4cc1392ae594871821b0633a" # Placeholder

# --- OpenWeatherMap API Endpoints ---
# These are the correct base endpoints for OpenWeatherMap API.
# Parameters like 'q' (city name) and 'appid' (API key) are passed separately in the 'params' dictionary.
OPENWEATHER_CURRENT_API_URL = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_FORECAST_API_URL = "https://api.openweathermap.org/data/2.5/forecast" # 5-day / 3-hour forecast (free tier)

# A boolean to check if API keys are configured and ready
weather_api_available = api_keys_available and OPENWEATHER_CURRENT_API_URL and OPENWEATHER_FORECAST_API_URL


# --- Helper function to fetch current weather data from OpenWeatherMap API ---
def get_current_weather_data(city_name, units='metric'): # OpenWeatherMap uses 'metric' or 'imperial'
    """
    Fetches current weather data for a given city using OpenWeatherMap API.
    """
    if not weather_api_available:
        return None

    api_url = OPENWEATHER_CURRENT_API_URL
    params = {
        'q': city_name,
        'appid': OPENWEATHER_API_KEY, # Use the correct variable name
        'units': units # 'metric' for Celsius, 'imperial' for Fahrenheit
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching current weather data from OpenWeatherMap API: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON response from OpenWeatherMap API: {e}. Raw response might not be JSON.")
        try:
            response = requests.get(api_url, params=params)
            print("Raw Response that failed to decode:")
            print(response.text)
        except Exception as inner_e:
            print(f"Could not re-fetch raw response for debugging: {inner_e}")
        return None


# --- Helper function to fetch forecast weather data from OpenWeatherMap API ---
def get_forecast_weather_data(city_name, country_code=None, units='metric', days=5):
    """
    Fetches 5-day / 3-hour forecast weather data for a given city using OpenWeatherMap API.
    Note: OpenWeatherMap's free API provides 5-day / 3-hour forecast, not daily summary directly.
    We will process it to show daily summaries.
    """
    if not weather_api_available:
        return None

    api_url = OPENWEATHER_FORECAST_API_URL
    
    # Construct the 'q' parameter with city name and optional country code
    if country_code:
        city_param = f"{city_name},{country_code}"
    else:
        city_param = city_name

    params = {
        'q': city_param,
        'appid': OPENWEATHER_API_KEY, # Use the correct variable name
        'units': units, # 'metric' for Celsius, 'imperial' for Fahrenheit
        'cnt': days * 8 # 8 data points per day for 3-hour forecast
    }

    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching forecast weather data from OpenWeatherMap API: {e}")
        return None
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON response from OpenWeatherMap API: {e}. Raw response might not be JSON.")
        try:
            response = requests.get(api_url, params=params)
            print("Raw Response that failed to decode:")
            print(response.text)
        except Exception as inner_e:
            print(f"Could not re-fetch raw response for debugging: {inner_e}")
        return None


# --- Custom CSS (Optional: for consistent styling with app.py) ---
st.markdown("""
<style>
/* General styling for containers/boxes */
.stContainer, .stForm, .stTable {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    background-color: #ffffff;
}

/* Ensure buttons are centered within their own space */
.stButton > button {
    display: block;
    margin-left: auto;
    margin-right: auto;
    width: 80%; /* Make button take up more space in its column */
    padding: 10px 15px;
    border-radius: 8px;
    background-color: #4CAF50; /* Example color */
    color: white;
    border: none;
    cursor: pointer;
    font-size: 1em;
    transition: background-color 0.3s ease;
}

.stButton > button:hover {
    background-color: #45a049;
}

/* Specific button styling for "Back" button */
.stButton button[key*="back"] {
    background-color: #6c757d; /* Grey for back button */
}

.stButton button[key*="back"]:hover {
    background-color: #5a6268;
}

/* Input bar styling */
.stTextInput>div>div>input {
    border-radius: 8px;
    border: 1px solid #ced4da;
    padding: 10px;
    font-size: 16px;
}

/* Selectbox styling */
.stSelectbox>div>div>div {
    border-radius: 8px;
    border: 1px solid #ced4da;
    padding: 10px;
    font-size: 16px;
}

.main-title {
    text-align: center;
    font-size: 3em; /* Adjust as needed */
    color: #007bff; /* A nice blue color */
    margin-bottom: 30px;
    font-family: 'Inter', sans-serif; /* Use Inter font */
}

.weather-card {
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 15px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
    background-color: #f9f9f9;
}

.weather-card h4 {
    color: #007bff;
    margin-top: 0;
}
</style>
""", unsafe_allow_html=True)


# --- Initialize Session State for this page ---
if 'weather_current_data' not in st.session_state:
    st.session_state.weather_current_data = None
if 'weather_forecast_data' not in st.session_state:
    st.session_state.weather_forecast_data = None
if 'weather_selected_date' not in st.session_state:
    st.session_state.weather_selected_date = datetime.date.today()
if 'manual_city_input' not in st.session_state: # New state for manual city input
    st.session_state.manual_city_input = ""


# --- Weather Prediction Page UI ---
st.markdown("<h1 class='main-title'>Weather Forecast</h1>", unsafe_allow_html=True)

# Ensure selected_place_details is available from app.py
selected_place_details = st.session_state.get('selected_place_details')

# Determine initial city name for input field
initial_city_name = ""
if selected_place_details:
    initial_city_name = selected_place_details.get('displayName', {}).get('text', '')

# Manual City Input
st.markdown("### Enter City Name")
st.session_state.manual_city_input = st.text_input(
    "City Name:",
    value=initial_city_name,
    key="weather_city_input",
    help="Enter the city name to get weather forecast."
)

# Attempt to extract country code from addressComponents if a place was selected
place_country_code = None
if selected_place_details:
    if 'addressComponents' in selected_place_details:
        for component in selected_place_details['addressComponents']:
            if 'country' in component.get('types', []):
                place_country_code = component.get('shortText')
                break

# Display coordinates and country code if a place was selected (for user info)
if selected_place_details:
    place_lat = selected_place_details['location']['latitude']
    place_lon = selected_place_details['location']['longitude']
    st.write(f"Coordinates of selected place: Lat {place_lat:.6f}, Lon {place_lon:.6f}")
    if place_country_code:
        st.write(f"Country Code of selected place: {place_country_code}")
    st.write("---") # Separator


if st.session_state.manual_city_input:
    current_city_for_api = st.session_state.manual_city_input

    if weather_api_available:
        # --- Current Weather ---
        st.markdown("### Current Weather")
        if st.button("Get Current Weather", key="get_current_weather_manual"):
            with st.spinner(f"Fetching current weather for {current_city_for_api}..."):
                st.session_state.weather_current_data = get_current_weather_data(current_city_for_api)

        if st.session_state.weather_current_data:
            current_weather = st.session_state.weather_current_data
            st.markdown("<div class='weather-card'>", unsafe_allow_html=True)
            # Extract and display data based on OpenWeatherMap response
            st.write(f"**Weather:** {current_weather['weather'][0]['description'].title()}")
            st.write(f"**Temperature:** {current_weather['main']['temp']} °C")
            st.write(f"**Feels like:** {current_weather['main']['feels_like']} °C")
            st.write(f"**Humidity:** {current_weather['main']['humidity']}%")
            st.markdown("</div>", unsafe_allow_html=True)
        elif st.button("Try again for current weather", key="retry_current_weather_manual_btn"):
            st.session_state.weather_current_data = get_current_weather_data(current_city_for_api)


        # --- 5-Day Forecast ---
        st.markdown("### 5-Day Forecast (3-Hour Intervals)")
        st.info("OpenWeatherMap provides forecast data in 3-hour intervals for the next 5 days.")
        if st.button("Get 5-Day Forecast", key="get_forecast_weather_manual"):
            with st.spinner(f"Fetching 5-day forecast for {current_city_for_api}..."):
                # Use the extracted country code if available, otherwise just city name
                st.session_state.weather_forecast_data = get_forecast_weather_data(current_city_for_api, country_code=place_country_code)

        if st.session_state.weather_forecast_data:
            forecast_list = st.session_state.weather_forecast_data.get('list', [])

            # Group forecast by day
            daily_forecasts = {}
            for item in forecast_list:
                dt_object = datetime.datetime.fromtimestamp(item['dt'])
                date_str = dt_object.strftime('%Y-%m-%d')
                if date_str not in daily_forecasts:
                    daily_forecasts[date_str] = []
                daily_forecasts[date_str].append(item)

            if daily_forecasts:
                for date_str, forecasts_for_day in daily_forecasts.items():
                    st.markdown(f"#### {datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%A, %B %d, %Y')}")

                    # Display summary for the day (e.g., min/max temp, main condition)
                    min_temp = min(item['main']['temp_min'] for item in forecasts_for_day)
                    max_temp = max(item['main']['temp_max'] for item in forecasts_for_day)

                    # Get the most common weather condition for the day
                    conditions = [item['weather'][0]['description'] for item in forecasts_for_day]
                    most_common_condition = Counter(conditions).most_common(1)[0][0]

                    st.markdown("<div class='weather-card'>", unsafe_allow_html=True)
                    st.write(f"**Min Temp:** {min_temp} °C")
                    st.write(f"**Max Temp:** {max_temp} °C")
                    st.write(f"**Main Condition:** {most_common_condition.title()}")
                    st.markdown("</div>", unsafe_allow_html=True)

                    # Optionally, show more detailed intervals for the day in an expander
                    with st.expander(f"See all 3-hour intervals for {datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%A, %B %d')}"):
                        for item in forecasts_for_day:
                            dt_object = datetime.datetime.fromtimestamp(item['dt'])
                            st.write(
                                f"**{dt_object.strftime('%I:%M %p')}:** "
                                f"Temp: {item['main']['temp']}°C, "
                                f"Feels like: {item['main']['feels_like']}°C, "
                                f"Condition: {item['weather'][0]['description'].title()}, "
                                f"Humidity: {item['main']['humidity']}%"
                            )
            else:
                st.info("No forecast data available for this location or date range from OpenWeatherMap API.")
        elif st.button("Try again for 5-day forecast", key="retry_forecast_weather_manual_btn"):
            st.session_state.weather_forecast_data = get_forecast_weather_data(current_city_for_api, country_code=place_country_code)

    else:
        st.warning("Weather API is not configured or available. Please ensure `OPENWEATHER_API_KEY` is set in `secrets.toml`.")

    st.write("---")
    # --- Navigation Buttons ---
    col_back, col_budget = st.columns(2)
    with col_back:
        if st.button("Back to Place Details", key="back_to_place_details_from_weather", use_container_width=True):
            st.session_state.step = 2 # Ensure app.py is in step 2
            st.session_state.step2_view = 'place_details' # Ensure app.py shows place details
            st.switch_page("app.py")
    with col_budget:
        if st.button("Go to Budget Predictor", key="go_to_budget_predictor_from_weather", use_container_width=True):
            st.switch_page("pages/budget_predictor.py")

else:
    st.warning("Please enter a city name above to get weather information.")
    if st.button("Go to Home Page", key="go_home_from_weather_no_place"):
        st.session_state.step = 1
        st.session_state.step2_view = 'explore_options'
        st.session_state.selected_place_details = None
        st.switch_page("app.py")
