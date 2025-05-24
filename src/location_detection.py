import streamlit as st
import requests
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
import json

def get_coordinates(location_name):
    """
    Gets the latitude and longitude coordinates for a given location name using Nominatim.
    """
    geolocator = Nominatim(user_agent="tourism_explorer_app")
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except Exception as e:
        # st.error(f"Geocoding error for '{location_name}': {e}") # Suppress for cleaner output
        return None, None

def get_location_name(latitude, longitude):
    """
    Gets a human-readable location name from coordinates using Nominatim.
    """
    geolocator = Nominatim(user_agent="tourism_explorer_app")
    try:
        reverse_location = geolocator.reverse(f"{latitude}, {longitude}", exactly_one=True)
        if reverse_location:
            return reverse_location.address
        else:
            return "Location name not found"
    except Exception as e:
        # st.error(f"Reverse geocoding error for {latitude}, {longitude}: {e}") # Suppress for cleaner output
        return "Error fetching location name"

# The get_precise_location_gcloud_http function has been removed as requested.

def display_map(latitude, longitude, location_name="Location"):
    """
    Displays a Folium map centered at the given coordinates.
    """
    if latitude is None or longitude is None:
        latitude, longitude = 20.5937, 78.9629 # Center of India approximate
        location_name = "Default Location (Could not find specific coordinates)"

    m = folium.Map(location=[latitude, longitude], zoom_start=12)
    folium.Marker([latitude, longitude], popup=location_name).add_to(m)
    folium_static(m, width=600, height=250)
