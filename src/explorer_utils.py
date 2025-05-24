import streamlit as st
import requests
import json
import os

# --- Google Places API Functions ---

def google_places_text_search_new(query, location_bias=None, location_restriction=None, api_base_url=None, api_key=None):
    """
    Performs a text search using the NEW Google Places API (places.googleapis.com/v1/places:searchText).
    Args:
        query (str): The text string on which to search.
        location_bias (dict, optional): Location biasing preferences.
        location_restriction (dict, optional): Location restriction preferences.
        api_base_url (str): The base URL for the Google Places API.
        api_key (str): Your Google Cloud API key.
    Returns:
        list: A list of place dictionaries from the API response, or None on error.
    """
    if not api_base_url or not api_key:
        st.error("API key or base URL is missing for Google Places Text Search.")
        return None

    url = api_base_url + "places:searchText"

    field_mask = [
        'places.id', 'places.displayName', 'places.formattedAddress',
        'places.location', 'places.types', 'places.rating', 'places.userRatingCount',
        'places.priceLevel'
    ]

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': ','.join(field_mask)
    }

    data = {
        'textQuery': query,
    }

    if location_bias:
        data['locationBias'] = location_bias
    if location_restriction:
        data['location_restriction'] = location_restriction

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        response_data = response.json()
        return response_data.get('places', [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling New Places Text Search API: {e}")
        return None
    except json.JSONDecodeError:
        st.error("Invalid JSON response from New Places Text Search API.")
        return None


def google_places_details_new(place_id, api_base_url=None, api_key=None):
    """
    Fetches detailed information for a place using its Place ID
    from the NEW Google Places API (places.googleapis.com/v1/places/{place_id}).
    Args:
        place_id (str): The unique identifier of the place.
        api_base_url (str): The base URL for the Google Places API.
        api_key (str): Your Google Cloud API key.
    Returns:
        dict: A dictionary containing place details, or None on error/not found.
    """
    if not api_base_url or not api_key:
        st.error("API key or base URL is missing for Google Places Details.")
        return None

    url = api_base_url + f"places/{place_id}"

    field_mask = [
        'id', 'displayName', 'formattedAddress', 'location', 'types', 'rating',
        'userRatingCount', 'regularOpeningHours', 'websiteUri', 'internationalPhoneNumber',
        'photos', 'reviews', 'priceLevel', 'accessibilityOptions'
    ]

    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': ','.join(field_mask)
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        place_details = response.json()
        return place_details
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling New Places Details API for {place_id}: {e}")
        return None
    except json.JSONDecodeError:
        st.error("Invalid JSON response from New Places Details API.")
        return None


def fetch_place_photos(photo_name, api_key, maxwidth=400):
    """
    Fetches a photo URL from a photo.name reference.
    Args:
        photo_name (str): The 'name' field from a photo object in Places API response.
        api_key (str): Your Google Cloud API key.
        maxwidth (int, optional): Maximum width of the photo. Defaults to 400.
    Returns:
        str: The URL of the photo, or None if not available.
    """
    if not api_key or not photo_name:
        return None

    url = f"https://places.googleapis.com/v1/{photo_name}/media?key={api_key}&maxWidthPx={maxwidth}"
    return url


def get_place_reviews_with_sentiment(sentiment_pipeline, place_details_reviews):
    """
    Analyzes the sentiment of a list of reviews using the ML model
    and provides an aggregated summary, including individual results.
    Args:
        sentiment_pipeline: The loaded sentiment analysis pipeline.
        place_details_reviews (list): A list of review dictionaries from the Google Places API.
                                      Each dict is expected to have a 'text' key.
    Returns:
        dict: A dictionary containing the aggregated sentiment counts
              (positive, negative, total analyzed) and an overall category.
              Includes 'individual_results' for each review's sentiment.
              Returns None if no valid reviews are provided.
    """
    if not place_details_reviews:
        return None

    positive_count = 0
    negative_count = 0
    total_analyzed = 0
    individual_results = []

    for review in place_details_reviews:
        review_text = review.get('text', '')
        if review_text:
            try:
                sentiment = sentiment_pipeline(review_text)[0] # Pipeline returns list of dicts
                individual_results.append({'review': review_text, 'sentiment': sentiment})
                total_analyzed += 1
                if sentiment['label'] == 'POSITIVE':
                    positive_count += 1
                elif sentiment['label'] == 'NEGATIVE':
                    negative_count += 1
            except Exception as e:
                st.warning(f"Could not analyze sentiment for a review: {e}")

    overall_category = "Neutral 😐"
    if total_analyzed > 0:
        if positive_count > negative_count * 1.5:
            overall_category = "Mostly Positive 😊"
        elif negative_count > positive_count * 1.5:
            overall_category = "Mostly Negative 😞"
        elif positive_count > 0 or negative_count > 0:
            overall_category = "Mixed Feelings 😐"

    return {
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': total_analyzed - positive_count - negative_count,
        'total_analyzed': total_analyzed,
        'overall_category': overall_category,
        'individual_results': individual_results
    }


def find_nearby_attractions(lat, lng, api_base_url, api_key):
    """
    Finds nearby tourist attractions using the Google Places Text Search API.
    Args:
        lat (float): Latitude of the center point.
        lng (float): Longitude of the center point.
        api_base_url (str): The base URL for the Google Places API.
        api_key (str): Your Google Cloud API key.
    Returns:
        list: A list of nearby attraction dictionaries, or None on error.
    """
    query = "tourist attraction"
    location_bias = {
        'circle': {
            'center': {'latitude': lat, 'longitude': lng},
            'radius': 5000 # Search within 5km radius for nearby attractions
        }
    }
    return google_places_text_search_new(query, location_bias=location_bias, api_base_url=api_base_url, api_key=api_key)