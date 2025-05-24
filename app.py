# app.py (Part 1: New Google Places API Integration)

from json.tool import main
import streamlit as st
import requests
import json
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.distance import geodesic # Changed from 'distance' to 'geodesic' for direct use
import datetime # Import datetime for date inputs
import os # Import os for environment variables

# Import functions from src/
from src.sentiment_model import load_sentiment_model, get_place_reviews_with_sentiment # Import sentiment analysis function
# Removed get_precise_location_gcloud_http from import list as it's no longer used
from src.location_detection import get_coordinates, get_location_name, display_map
from src.explorer_utils import (
    google_places_text_search_new,
    google_places_details_new,
    fetch_place_photos,
    find_nearby_attractions
)


# --- Configuration ---
st.set_page_config(layout="wide", page_title="Explorer of India")


# --- Import sentiment_model AFTER set_page_config ---
sentiment_model_available = False
sentiment_pipeline = None # Initialize to None
try:
    sentiment_pipeline = load_sentiment_model()
    sentiment_model_available = True
except Exception as e:
    st.error(f"Error during sentiment model import or loading: {e}")
    sentiment_model_available = False


# Replace with your Google Cloud API key that has access to the NEW Places API
# IMPORTANT: For photos to display, your API key MUST also have the 'Place Photos API' enabled.
# WARNING: Exposing API keys directly in frontend code is not secure for production.
# Consider using Streamlit Secrets or environment variables.
GOOGLE_CLOUD_API_KEY = "AIzaSyB6H2yO6ESSD6XzX4tqc_VSYMYvRXfWFq0" # <<< IMPORTANT: REPLACE THIS!


# Base URLs for Google APIs (Updated for New Places API)
GOOGLE_PLACES_BASE_URL = "https://places.googleapis.com/v1/"
# Removed GOOGLE_CLOUD_GEOLOCATION_API_URL as it's no longer used for auto-detection

# Check if the API key is set (and not the original placeholder)
api_key_provided = (GOOGLE_CLOUD_API_KEY == "AIzaSyB6H2yO6ESSD6XzX4tqc_VSYMYvRXfWFq0")
if not api_key_provided:
    st.error("🚨 **Google Cloud API key is missing or not replaced.** Please add your key with access to the NEW Places API.")
    st.info("API features are disabled until a valid key is provided.")
    GOOGLE_PLACES_BASE_URL = None
    # GOOGLE_CLOUD_GEOLOCATION_API_URL = None # This line is removed as the variable is no longer declared


# --- Apply Custom CSS (Embedded directly for simplicity) ---
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

/* Styles for place cards in details view and nearby attractions */
.details-box, .sentiment-box, .nearby-card {
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 15px;
    margin-bottom: 20px;
    box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    background-color: #fff;
}

.details-box h3, .sentiment-box h3, .nearby-card h5 {
    color: #333;
    margin-top: 0;
}

/* Styles for the new list row items */
.list-item-row {
    border: 1px solid #eee;
    border-radius: 8px;
    padding: 10px 15px;
    margin-bottom: 10px;
    background-color: #f9f9f9;
    box-shadow: 1px 1px 5px rgba(0,0,0,0.05);
    display: flex; /* Use flexbox for horizontal alignment */
    align-items: center; /* Vertically align items in the row */
}

.list-item-row h5 {
    margin: 0; /* Remove default margin for h5 in list items */
    flex-grow: 1; /* Allow name to take available space */
    text-align: left;
}

.list-item-row p {
    margin: 0; /* Remove default margin for p in list items */
    font-size: 0.9em;
    color: #666;
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

/* For aligned text in budget results */
.aligned-label {
    font-weight: bold;
    min-width: 150px; /* Adjust as needed */
    display: inline-block;
}

/* Style for distance display */
.distance-display {
    font-size: 2em;
    font-weight: bold;
    color: #007bff;
    text-align: center;
    margin-top: 10px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)


# --- Initialize Session State (VERY EARLY in the script) ---
if 'step' not in st.session_state:
    st.session_state.step = 1 # Start at Step 1

if 'location_data' not in st.session_state:
    st.session_state.location_data = None # {lat: ..., lon: ..., name: ...}

if 'manual_location_input' not in st.session_state:
    st.session_state.manual_location_input = ""

if 'search_term_input' not in st.session_state:
    st.session_state.search_term_input = ""

if 'api_place_list' not in st.session_state:
    st.session_state.api_place_list = [] # List of place dictionaries from API results

if 'selected_place_details' not in st.session_state:
    st.session_state.selected_place_details = None # Dictionary of the selected place details

if 'step2_view' not in st.session_state:
    st.session_state.step2_view = 'explore_options' # 'explore_options', 'place_list', 'place_details'

if 'current_place_list_query' not in st.session_state:
    st.session_state.current_place_list_query = None

if 'search_history' not in st.session_state:
    st.session_state['search_history'] = []

# --- NEW: Recommendation-related session state ---
if 'category_counts' not in st.session_state:
    st.session_state['category_counts'] = {} # Stores counts of categories searched
if 'recommended_categories_shown' not in st.session_state:
    st.session_state['recommended_categories_shown'] = set() # To prevent showing the same recommendation repeatedly

if 'nearby_attractions_list' not in st.session_state:
    st.session_state.nearby_attractions_list = {} # Cache nearby place dictionaries by originating place ID

if 'originating_place_id' not in st.session_state:
    st.session_state.originating_place_id = None

if 'place_sentiment_cache' not in st.session_state:
    st.session_state.place_sentiment_cache = {} # Cache sentiment results by place ID

if 'budget_filter' not in st.session_state:
    st.session_state.budget_filter = 'Any' # Using a string label


# --- Helper functions for navigation (within app.py) ---
def on_place_select(place_id):
    st.session_state.selected_place_details = google_places_details_new(place_id, GOOGLE_PLACES_BASE_URL, GOOGLE_CLOUD_API_KEY)
    if st.session_state.selected_place_details:
        st.session_state.step2_view = 'place_details'
    st.rerun()


# --- NEW: Category Mapping for Recommendations ---
# This maps Google Places API types to your broader categories for recommendation
API_TYPE_TO_CATEGORY_MAP = {
    # Broad Categories
    "Beach": ["beach", "seaside", "coast", "ocean"],
    "Temple": ["temple", "hindu_temple", "church", "mosque", "synagogue"],
    "Mountain": ["mountain", "hill", "peak", "trekking_area", "nature_reserve"],
    "Park": ["park", "garden", "zoo", "botanical_garden"],
    "Restaurant": ["restaurant", "cafe", "food", "bar"],
    "Shopping Mall": ["shopping_mall", "department_store"],
    "Museum": ["museum", "art_gallery"],
    "Historical Site": ["historical_site", "landmark", "ruin", "palace", "fort"],
    # Add more mappings as needed based on common Google Places API types
    # You might need to inspect place['types'] from your API responses to refine this
}

def get_broad_category_from_api_types(place_types):
    """
    Maps Google Places API types to a list of broad categories.
    Returns a list to capture multiple relevant categories.
    """
    if not place_types:
        return [] # Return an empty list if no types

    broad_categories = set() # Use a set to avoid duplicates
    
    # Prioritize certain categories if a place has multiple types
    priority_order = ["Beach", "Temple", "Mountain", "Historical Site", "Museum", "Park", "Restaurant", "Shopping Mall"]

    for broad_cat in priority_order:
        for api_type_keyword in API_TYPE_TO_CATEGORY_MAP.get(broad_cat, []):
            if api_type_keyword in place_types:
                broad_categories.add(broad_cat)
                # If you want only the highest priority match, uncomment break:
                # break 
    
    # If no specific mapping found by priority, try to infer from general keywords in types
    # This part can be refined or removed if priority_order covers all desired cases
    if not broad_categories: # Only try general inference if no priority category was found
        for place_type in place_types:
            for broad_cat, keywords in API_TYPE_TO_CATEGORY_MAP.items():
                if any(kw in place_type for kw in keywords):
                    broad_categories.add(broad_cat)
    
    return list(broad_categories) # Convert back to a list


# --- Application Title (Centered by CSS) ---
st.markdown("<h1 class='main-title'>Explorer of INDIA</h1>", unsafe_allow_html=True)


# --- Step 1: Location Detection and Map ---
if st.session_state.step == 1:
    st.subheader("Find Your Location")
    col1, col2 = st.columns([0.5, 0.5])

    with col1:
        st.markdown("#### Enter Location Manually")
        st.session_state.manual_location_input = st.text_input(
            "City or Landmark:",
            value=st.session_state.manual_location_input,
            key="manual_input_step1",
            label_visibility="collapsed"
        )
        if st.button("Confirm Manual Location", key="geocode_manual_btn_step1"):
            manual_location = st.session_state.manual_location_input
            if manual_location:
                with st.spinner(f"Finding '{manual_location}'..."):
                    lat_manual, lon_manual = get_coordinates(manual_location)
                    if lat_manual is not None and lon_manual is not None:
                        location_name = get_location_name(lat_manual, lon_manual)
                        st.session_state.location_data = {
                            'lat': lat_manual, 'lon': lon_manual, 'name': location_name
                        }
                        st.success(f"Location Confirmed: {location_name}")
                        st.rerun()
                    else:
                        st.error(f"Could not find coordinates for '{manual_location}'. Please try again.")
            else:
                st.warning("Please enter a location in the text box first.")

        # The "Auto Detect My Location" section has been completely removed from here.
        # It was previously located below the manual input section.

    with col2:
        st.markdown("#### Your Location Map")
        if st.session_state.location_data and st.session_state.location_data['lat'] is not None:
            try:
                display_map(st.session_state.location_data['lat'], st.session_state.location_data['lon'], st.session_state.location_data.get('name', 'Confirmed Location'))
            except Exception as e:
                st.error(f"Error displaying map: {e}")
        else:
            st.info("Detect or enter location on the left to see the map.")

    if st.session_state.location_data and st.session_state.location_data['lat'] is not None:
        st.write("---")
        st.success(f"Confirmed Location: **{st.session_state.location_data.get('name', 'N/A')}**")
        st.write(f"Coordinates: Lat {st.session_state.location_data.get('lat'):.6f}, Lon {st.session_state.location_data.get('lon'):.6f}")
        st.write("---")

        center_col1, center_col2, center_col3 = st.columns([1, 1, 1])
        with center_col2:
            if GOOGLE_PLACES_BASE_URL:
                if st.button("Proceed to explore places", key="proceed_to_explore_btn_step1", use_container_width=True):
                    st.session_state.step = 2
                    # Clear states for Step 2 to start fresh exploration
                    st.session_state.search_term_input = ""
                    st.session_state.api_place_list = []
                    st.session_state.selected_place_details = None
                    st.session_state.step2_view = 'explore_options'
                    st.session_state.current_place_list_query = None
                    st.session_state['search_history'] = []
                    
                    # --- NEW: Reset recommendation related session state when proceeding to Step 2 ---
                    st.session_state['category_counts'] = {}
                    st.session_state['recommended_categories_shown'] = set()

                    st.session_state.nearby_attractions_list = {}
                    st.session_state.originating_place_id = None
                    st.session_state.place_sentiment_cache = {}
                    st.session_state.budget_filter = 'Any'
                    st.rerun()
            else:
                st.warning("Cannot proceed to explore places because the Google Cloud API key is missing or invalid.")


# --- Step 2: Explore Places (Search, Explore Options, Place List, Details) ---
elif st.session_state.step == 2:
    # Define explore options dictionary here, outside conditional view blocks
    explore_options = {
        "Explore by type": ['Tourist Attraction', 'Museum', 'Park', 'Temple', 'Restaurant', 'Shopping Mall'],
        "Popular places": ['Popular Places in North India', 'Best Beaches in Goa', 'Historical Sites in Rajasthan', 'Hill Stations near Mumbai']
    }

    # Mapping Price Level integers to labels for display and filtering
    # Google Places API price levels are 0 (Free) to 4 (Very Expensive)
    PRICE_LEVEL_MAP = {
        0: 'Free', 1: '$', 2: '$$', 3: '$$$', 4: '$$$$'
    }
    # Reverse map for filtering logic
    PRICE_LEVEL_REVERSE_MAP = {v: k for k, v in PRICE_LEVEL_MAP.items()}
    # Add 'Any' option for the filter
    PRICE_LEVEL_FILTER_OPTIONS = ['Any'] + list(PRICE_LEVEL_MAP.values())


    # This block handles the top section for Step 2 (Explore options and Place List)
    # It is NOT displayed when step2_view is 'place_details'
    if st.session_state.step2_view != 'place_details':
        # --- Location Info and Change Button (Always visible in Step 2) ---
        location_info_col, change_button_col = st.columns([4, 1])
        with location_info_col:
            if st.session_state.location_data and st.session_state.location_data['lat'] is not None:
                st.write(f"Exploring from the vicinity of: **{st.session_state.location_data.get('name', 'Your Confirmed Location')}**")
            else:
                st.warning("Location data missing. Please go back to Step 1.")

        with change_button_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Back", key="change_location_btn_step2"):
                st.session_state.step = 1
                st.rerun()

        st.write("---")

        # --- Search Bar Section ---
        search_col1, search_col2, search_col3 = st.columns([1, 3, 1])
        with search_col2:
            st.session_state.search_term_input = st.text_input(
                "Enter a place name or type (e.g., 'museum in Delhi', 'restaurant near me'):",
                value=st.session_state.search_term_input,
                key="search_input_step2",
                label_visibility="collapsed"
            )
            button_center_col1, button_center_col2, button_center_col3 = st.columns([1, 1, 1])
            with button_center_col2:
                search_button_clicked = False
                if GOOGLE_PLACES_BASE_URL:
                    search_button_clicked = st.button("Search 🔍", key="search_button_step2", use_container_width=True)
                else:
                    st.info("Search is disabled because the Google Cloud API key is missing or invalid.")

            # --- Budget Filter (Optional, can be uncommented if needed) ---
            # st.session_state.budget_filter = st.selectbox(
            #     "Filter by Price Level:",
            #     options=PRICE_LEVEL_FILTER_OPTIONS,
            #     key="budget_filter_step2",
            #     index=PRICE_LEVEL_FILTER_OPTIONS.index(st.session_state.budget_filter)
            # )


        # --- Handle Search Button Click ---
        if search_button_clicked and st.session_state.search_term_input and GOOGLE_PLACES_BASE_URL:
            search_term = st.session_state.search_term_input.strip()
            # Append to history for recommendation tracking
            st.session_state['search_history'].append(search_term) 

            st.info(f"Searching for: {search_term}...")

            # Clear previous API results and selected details when performing a new search
            st.session_state.api_place_list = []
            st.session_state.selected_place_details = None
            st.session_state.step2_view = 'place_list'
            st.session_state.current_place_list_query = search_term
            st.session_state.nearby_attractions_list = {}
            st.session_state.originating_place_id = None
            st.session_state.place_sentiment_cache = {}
            # st.session_state.budget_filter is already set by the selectbox

            location_bias = None
            if st.session_state.location_data and st.session_state.location_data['lat'] is not None:
                location_bias = {
                    'circle': {
                        'center': {
                            'latitude': st.session_state.location_data['lat'],
                            'longitude': st.session_state.location_data['lon']
                        },
                        'radius': 50000 # Bias within 50km (max allowed for bias)
                    }
                }

            places = google_places_text_search_new(search_term, location_bias=location_bias, api_base_url=GOOGLE_PLACES_BASE_URL, api_key=GOOGLE_CLOUD_API_KEY)

            if places is not None:
                # --- NEW: Update category counts based on API results ---
                for place in places:
                    if 'types' in place:
                        # Use the new get_broad_category_from_api_types function that returns a list
                        broad_categories = get_broad_category_from_api_types(place['types'])
                        for broad_category in broad_categories: # Iterate through all found broad categories
                            if broad_category:
                                st.session_state['category_counts'][broad_category] = st.session_state['category_counts'].get(broad_category, 0) + 1
                # --- END NEW ---

                selected_budget_label = st.session_state.budget_filter
                if selected_budget_label != 'Any':
                    target_price_level = PRICE_LEVEL_REVERSE_MAP.get(selected_budget_label)
                    if target_price_level is not None:
                        filtered_places = [
                            p for p in places
                            if p.get('priceLevel') is None or p.get('priceLevel') == target_price_level
                        ]
                    else:
                        filtered_places = places
                else:
                    filtered_places = places

                st.session_state.api_place_list = filtered_places
                st.rerun()
            else:
                st.error("Could not retrieve places from Google Places API.")
                st.rerun() # Rerun to clear spinner and display error

    # --- NEW: Personalized Recommendation Display Logic ---
    # This block comes *after* the search button handling but before explore_options/place_list views
    if st.session_state.step2_view != 'place_details': # Don't show recommendations on details page
        recommended_category_to_show = None
        # Find the category with the highest count that hasn't been shown yet and meets the threshold
        sorted_categories = sorted(st.session_state['category_counts'].items(), key=lambda item: item[1], reverse=True)
        for category, count in sorted_categories:
            if count >= 3 and category not in st.session_state['recommended_categories_shown']:
                recommended_category_to_show = category
                break # Show only one recommendation at a time

        if recommended_category_to_show:
            st.write("---") # Separator
            st.markdown("### Recommended For You")
            st.info(f"It seems you're interested in exploring more {recommended_category_to_show.lower()}es!")
            
            rec_col1, rec_col2, rec_col3 = st.columns([1,1,1])
            with rec_col2:
                if st.button(f"Explore {recommended_category_to_show}s", key=f"rec_button_{recommended_category_to_show}", use_container_width=True):
                    # Trigger a new search for the recommended category
                    st.session_state.search_term_input = recommended_category_to_show
                    st.session_state.step2_view = 'place_list'
                    
                    location_bias = None
                    if st.session_state.location_data and st.session_state.location_data['lat'] is not None:
                        location_bias = {
                            'circle': {
                                'center': {'latitude': st.session_state.location_data['lat'], 'longitude': st.session_state.location_data['lon']},
                                'radius': 50000
                            }
                        }
                    st.session_state.api_place_list = google_places_text_search_new(recommended_category_to_show, location_bias=location_bias, api_base_url=GOOGLE_PLACES_BASE_URL, api_key=GOOGLE_CLOUD_API_KEY)
                    
                    # Mark this category as shown so it doesn't reappear immediately
                    st.session_state['recommended_categories_shown'].add(recommended_category_to_show)
                    st.rerun()
            st.write("---") # Separator

    # --- Conditional View for Step 2 ---
    if st.session_state.step2_view == 'explore_options':
        st.write("---")
        st.markdown("### Explore by Type")
        num_cols = 2
        explore_type_buttons = explore_options["Explore by type"]
        for i in range(0, len(explore_type_buttons), num_cols):
            cols = st.columns(num_cols)
            for j in range(num_cols):
                if i + j < len(explore_type_buttons):
                    place_type = explore_type_buttons[i + j]
                    with cols[j]:
                        if st.button(place_type, key=f"explore_type_{place_type}", use_container_width=True):
                            st.session_state.search_term_input = place_type
                            st.session_state.step2_view = 'place_list'
                            location_bias = None # Recalculate or retrieve if needed for explore buttons
                            if st.session_state.location_data and st.session_state.location_data['lat'] is not None:
                                location_bias = {
                                    'circle': {
                                        'center': {'latitude': st.session_state.location_data['lat'], 'longitude': st.session_state.location_data['lon']},
                                        'radius': 50000
                                    }
                                }
                            st.session_state.api_place_list = google_places_text_search_new(place_type, location_bias=location_bias, api_base_url=GOOGLE_PLACES_BASE_URL, api_key=GOOGLE_CLOUD_API_KEY)
                            st.rerun()

        st.markdown("### Popular Places")
        popular_places_buttons = explore_options["Popular places"]
        for i in range(0, len(popular_places_buttons), num_cols):
            cols = st.columns(num_cols)
            for j in range(num_cols):
                if i + j < len(popular_places_buttons):
                    query = popular_places_buttons[i + j]
                    with cols[j]:
                        if st.button(query, key=f"popular_place_{query}", use_container_width=True):
                            st.session_state.search_term_input = query
                            st.session_state.step2_view = 'place_list'
                            location_bias = None
                            if st.session_state.location_data and st.session_state.location_data['lat'] is not None:
                                location_bias = {
                                    'circle': {
                                        'center': {'latitude': st.session_state.location_data['lat'], 'longitude': st.session_state.location_data['lon']},
                                        'radius': 50000
                                    }
                                }
                            st.session_state.api_place_list = google_places_text_search_new(query, location_bias=location_bias, api_base_url=GOOGLE_PLACES_BASE_URL, api_key=GOOGLE_CLOUD_API_KEY)
                            st.rerun()

    elif st.session_state.step2_view == 'place_list':
        st.subheader("Search Results")
        if st.session_state.api_place_list:
            for place in st.session_state.api_place_list:
                with st.container():
                    st.markdown(f"##### {place.get('displayName', {}).get('text', 'N/A')}")
                    st.write(f"Address: {place.get('formattedAddress', 'N/A')}")
                    if 'rating' in place:
                        st.write(f"Rating: {place['rating']} ({place.get('userRatingCount', 0)} reviews)")
                    if 'priceLevel' in place:
                        st.write(f"Price: {PRICE_LEVEL_MAP.get(place['priceLevel'], 'N/A')}")
                    if st.button(f"View Details for {place.get('displayName', {}).get('text', 'N/A')}", key=f"details_{place['id']}"):
                        on_place_select(place['id'])
        else:
            st.info("No places found for your search. Try a different query.")

        if st.button("Back to Search/Explore Options", key="back_to_explore_options"):
            st.session_state.step2_view = 'explore_options'
            st.session_state.api_place_list = [] # Clear the list
            st.session_state.selected_place_details = None
            st.session_state.current_place_list_query = None
            st.rerun()

    elif st.session_state.step2_view == 'place_details':
        if st.session_state.selected_place_details:
            place_details = st.session_state.selected_place_details

            # Main Place Name (under "Explorer of INDIA" title)
            st.markdown(f"<h2 class='centered-title'>{place_details.get('displayName', {}).get('text', 'N/A')}</h2>", unsafe_allow_html=True)

            info_col, map_col = st.columns([0.6, 0.4]) # Adjust ratio as needed

            with info_col:
                st.markdown("### Place Information")
                
                # --- NEW: Display Location, Types, and Rating ---
                if 'location' in place_details:
                    location = place_details['location']
                    st.write(f"**Location:** Lat: {location.get('latitude', 'N/A')}, Lon: {location.get('longitude', 'N/A')}")
                else:
                    st.write("**Location:** N/A")
                    
                if 'types' in place_details:
                    types = ", ".join(place_details['types'])
                    st.write(f"**Types:** {types}")
                else:
                    st.write("**Types:** N/A")
                    
                if 'rating' in place_details:
                    rating = place_details['rating']
                    st.write(f"**Rating:** {rating}")
                else:
                    st.write("**Rating:** N/A")
                # --- END NEW ---

                st.write(f"**Address:** {place_details.get('formattedAddress', 'No address available.')}")

                # Opening Hours
                opening_hours = place_details.get('regularOpeningHours', {}).get('weekdayDescriptions')
                if opening_hours:
                    st.write("**Opening Hours:**")
                    for day_desc in opening_hours:
                        st.write(f"- {day_desc}")
                else:
                    st.write("**Opening Hours:** Not available.")

                # Accessibility Options
                accessibility = place_details.get('accessibilityOptions')
                if accessibility:
                    st.write("**Accessibility Options:**")
                    for key, value in accessibility.items():
                        if value: # Only show true options
                            # Format key for better readability (e.g., wheelchair_accessible_parking -> Wheelchair Accessible Parking)
                            st.write(f"- {key.replace('wheelchair_', '').replace('_', ' ').title()}")
                else:
                    st.write("**Accessibility:** Not available.")

                # Website
                website_uri = place_details.get('websiteUri')
                if website_uri:
                    st.markdown(f"**Official Website:** [Link]({website_uri})")
                else:
                    st.write("**Official Website:** Not available.")

                # Contact
                phone_number = place_details.get('internationalPhoneNumber')
                if phone_number:
                    st.write(f"**Contact:** {phone_number}")
                else:
                    st.write("**Contact:** Not available.")

                # Price Level
                price_level = place_details.get('priceLevel')
                if price_level is not None:
                    st.write(f"**Price Level:** {PRICE_LEVEL_MAP.get(price_level, 'N/A')}")
                else:
                    st.write("**Price Level:** Not available.")

            with map_col:
                st.markdown("### Location on Map")
                if place_details.get('location') and st.session_state.location_data:
                    place_lat = place_details['location']['latitude']
                    place_lon = place_details['location']['longitude']
                    user_lat = st.session_state.location_data['lat']
                    user_lon = st.session_state.location_data['lon']

                    # Calculate distance and display
                    if user_lat is not None and user_lon is not None:
                        try:
                            dist_km = geodesic((user_lat, user_lon), (place_lat, place_lon)).km
                            st.markdown(f"<p class='distance-display'>{int(dist_km):,} km</p>", unsafe_allow_html=True)
                        except Exception as e:
                            st.warning(f"Could not calculate distance: {e}")
                            st.markdown(f"<p class='distance-display'>Distance N/A</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p class='distance-display'>Distance N/A</p>", unsafe_allow_html=True)

                    display_map(place_lat, place_lon, place_details.get('displayName', {}).get('text', ''))

                    # Get Directions on Google Maps
                    if user_lat is not None and user_lon is not None:
                        # Google Maps URL for directions: origin=lat,lon&destination=lat,lon
                        google_maps_url = f"http://maps.google.com/maps?saddr={user_lat},{user_lon}&daddr={place_lat},{place_lon}"
                        st.link_button("Get Directions on Google Maps", url=google_maps_url, use_container_width=True)
                    else:
                        st.info("Enter your location in Step 1 to get directions.")

                else:
                    st.info("Map location or your current location not available to display map or directions.")

            st.write("---")
            st.markdown("### Photos")
            photos = place_details.get('photos', [])
            if photos:
                # Display max 5 photos
                display_photos_count = min(len(photos), 5)
                photo_cols = st.columns(display_photos_count)
                for i, photo in enumerate(photos[:display_photos_count]):
                    with photo_cols[i]:
                        photo_url = fetch_place_photos(photo['name'], GOOGLE_CLOUD_API_KEY)
                        if photo_url:
                            st.image(photo_url, caption=f"Photo {i+1}", use_container_width=True) # Corrected parameter
                        else:
                            st.image(f"https://placehold.co/150x100/aabbcc/000000?text=No+Image", caption="Image Unavailable", use_container_width=True)
            else:
                st.info(f"No images available for {place_details.get('displayName', {}).get('text', 'this place')}.")

            st.write("---")
            st.markdown("### User Reviews & Sentiment Analysis")
            if 'reviews' in place_details: # Check if reviews exist in place_details
                reviews_data = place_details['reviews']
                if reviews_data: # Check if reviews_data is not empty
                    if sentiment_model_available:
                        sentiment_summary = get_place_reviews_with_sentiment(sentiment_pipeline, reviews_data) # Pass pipeline
                        if sentiment_summary and sentiment_summary.get('total_analyzed', 0) > 0: # Check if any reviews were analyzed
                            st.markdown(f"<div class='sentiment-box'>", unsafe_allow_html=True)
                            st.markdown(f"**Overall Sentiment:** {sentiment_summary.get('overall_category', 'N/A')}")
                            st.write(f"Positive Reviews: {sentiment_summary.get('positive_count', 0)}")
                            st.write(f"Negative Reviews: {sentiment_summary.get('negative_count', 0)}")
                            st.markdown("</div>", unsafe_allow_html=True)

                            st.markdown("#### Individual Reviews:")
                            # Display at most 5 reviews
                            for i, r_sent in enumerate(sentiment_summary['individual_results'][:5]):
                                review_text = r_sent['review']
                                sentiment_label = r_sent['sentiment']['label'] if r_sent['sentiment'] else "N/A (Analysis Failed)"
                                st.write(f"- '{review_text}' ({sentiment_label})")
                            if len(sentiment_summary['individual_results']) > 5:
                                st.info(f"Displaying first 5 reviews out of {len(sentiment_summary['individual_results'])}.")
                        else:
                            st.info("No reviews available for sentiment analysis or analysis failed for all reviews.")
                            st.markdown("#### Raw Reviews (Sentiment Analysis Failed):")
                            # Display raw reviews if sentiment analysis failed for all
                            for i, review in enumerate(reviews_data[:5]):
                                st.write(f"- '{review.get('text', 'No review text.')}'")
                            if len(reviews_data) > 5:
                                st.info(f"Displaying first 5 raw reviews out of {len(reviews_data)}.")
                    else:
                        st.warning("Sentiment analysis model not loaded. Cannot perform sentiment analysis on reviews.")
                        st.markdown("#### Raw Reviews (Sentiment Analysis Disabled):")
                        for i, review in enumerate(reviews_data[:5]): # Display raw reviews if sentiment model is not available
                            st.write(f"- '{review.get('text', 'No review text.')}'")
                        if len(reviews_data) > 5:
                            st.info(f"Displaying first 5 raw reviews out of {len(reviews_data)}.")
                else:
                    st.info("No reviews available for this place.")
            else:
                st.info("No reviews data found for this place.")


            st.write("---")
            st.markdown("### Nearby Attractions")
            if place_details.get('location'):
                place_lat = place_details['location']['latitude']
                place_lon = place_details['location']['longitude']
                nearby_attractions = find_nearby_attractions(place_lat, place_lon, GOOGLE_PLACES_BASE_URL, GOOGLE_CLOUD_API_KEY)
                if nearby_attractions:
                    # Display at most 5 nearby attractions
                    display_attractions_count = min(len(nearby_attractions), 5)
                    for i, attraction in enumerate(nearby_attractions[:display_attractions_count]):
                        with st.container():
                            attraction_cols = st.columns([0.7, 0.3]) # Name/Address and Button
                            with attraction_cols[0]:
                                st.markdown(f"**{attraction.get('displayName', {}).get('text', 'N/A')}**")
                                st.write(f"*{attraction.get('formattedAddress', 'N/A')}*")
                            with attraction_cols[1]:
                                if st.button(f"View Details", key=f"nearby_details_{attraction['id']}"):
                                    st.session_state.originating_place_id = place_details['id']
                                    st.session_state.selected_place_details = google_places_details_new(attraction['id'], GOOGLE_PLACES_BASE_URL, GOOGLE_CLOUD_API_KEY)
                                    st.rerun()
                        st.markdown("---") # Separator for each attraction
                else:
                    st.info("No nearby attractions found.")
            else:
                st.info("Location data not available for this place to find nearby attractions.")

            # Back button logic for place details
            if st.session_state.originating_place_id:
                # This means we clicked a nearby attraction, so go back to the original place's details
                if st.button("Back to Previous Place Details", key="back_to_originating_place"):
                    st.session_state.selected_place_details = google_places_details_new(st.session_state.originating_place_id, GOOGLE_PLACES_BASE_URL, GOOGLE_CLOUD_API_KEY)
                    if st.session_state.selected_place_details:
                        st.session_state.originating_place_id = None # Clear this so next 'Back' goes to list
                        st.rerun()
                    else:
                        st.error("Could not retrieve original place details. Returning to search results.")
                        st.session_state.step2_view = 'place_list'
                        st.session_state.selected_place_details = None
                        st.session_state.originating_place_id = None
                        st.rerun()
            else:
                # Otherwise, go back to the place list
                if st.button("Back to Place List", key="back_to_place_list"):
                    st.session_state.step2_view = 'place_list'
                    st.session_state.selected_place_details = None # Clear selected details
                    st.session_state.originating_place_id = None # Clear originating place ID
                    st.rerun()
        else:
            st.error("No details available for the selected place.")
            if st.button("Back to Place List", key="back_to_place_list_error"):
                st.session_state.step2_view = 'place_list'
                st.session_state.selected_place_details = None
                st.rerun()

    # --- Button to navigate to Weather Predictor ---
    st.write("---")
    st.markdown("### Planning your trip?")
    center_col_wp1, center_col_wp2, center_col_wp3 = st.columns([1, 1, 1])
    with center_col_wp2:
        if st.button("Check Weather Forecast", key="go_to_weather_predictor", use_container_width=True):
            # Ensure selected_place_details is in session state for the next page
            st.switch_page("pages/weather_predictor.py")

    # --- Button to navigate to Budget Predictor (now after Weather Predictor) ---
    st.write("---")
    st.markdown("### Ready to plan your budget?")
    center_col_bp1, center_col_bp2, center_col_bp3 = st.columns([1, 1, 1])
    with center_col_bp2:
        if st.button("Go to Budget Predictor", key="go_to_budget_predictor", use_container_width=True):
            st.switch_page("pages/budget_predictor.py")


if __name__ == "__main__":
    main()
