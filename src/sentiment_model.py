# sentiment_model.py

import streamlit as st
from transformers import pipeline

# --- Load Pre-trained Sentiment Analysis Model ---
@st.cache_resource
def load_sentiment_model():
    """
    Loads a pre-trained sentiment analysis model and tokenizer using Hugging Face transformers.
    """
    # Using a model fine-tuned on the Stanford Sentiment Treebank v2 (SST-2)
    # This model classifies text as 'POSITIVE' or 'NEGATIVE'.
    model = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    return model

# --- Aggregate Sentiment Function ---
def get_place_reviews_with_sentiment(sentiment_pipeline, place_details_reviews):
    """
    Analyzes the sentiment of a list of reviews using the ML model
    and provides an aggregated summary, including individual results.
    Args:
        sentiment_pipeline: The loaded sentiment analysis pipeline.
        place_details_reviews (list): A list of review dictionaries from the Google Places API.
                                      Each dict is expected to have a 'text' key, which itself
                                      is a dictionary with 'text' and 'languageCode',
                                      and an 'authorAttribution' key which has a 'displayName'.
    Returns:
        dict: A dictionary containing the aggregated sentiment counts
              (positive, negative, total analyzed) and an overall category.
              Includes 'individual_results' for each review's sentiment,
              now also containing the author's display name.
              Returns None if no valid reviews are provided.
    """
    if not place_details_reviews:
        return None

    positive_count = 0
    negative_count = 0
    total_analyzed = 0
    individual_results = []

    for review in place_details_reviews:
        # CRUCIAL FIX: Access the nested 'text' field within the 'text' dictionary
        review_text_content = review.get('text', {}).get('text', '') # Extract only the string content
        author_name = review.get('authorAttribution', {}).get('displayName', 'Anonymous') # Extract author name
        
        if review_text_content: # Ensure there is actual text content to analyze
            sentiment = None
            try:
                # Attempt to get sentiment for each review using only the text content
                sentiment = sentiment_pipeline(review_text_content)[0] # Pipeline returns list of dicts
                total_analyzed += 1
                if sentiment['label'] == 'POSITIVE':
                    positive_count += 1
                elif sentiment['label'] == 'NEGATIVE':
                    negative_count += 1
            except Exception as e:
                # Catch the error (e.g., 'languageCode' error)
                st.warning(f"Could not analyze sentiment for review: '{review_text_content[:50]}...' Error: {e}")
                # If sentiment analysis fails, we still want to record the original review text
                # but its sentiment will be 'None' or 'N/A' in the display logic.

            # Store the original review text (from Google API), author, and the sentiment result
            individual_results.append({
                'review': review_text_content, # Store the extracted text content
                'author': author_name,
                'sentiment': sentiment
            })


    overall_category = "Neutral 😐"
    if total_analyzed > 0:
        if positive_count > negative_count * 1.5: # Example threshold for "Mostly Positive"
            overall_category = "Mostly Positive 😊"
        elif negative_count > positive_count * 1.5: # Example threshold for "Mostly Negative"
            overall_category = "Mostly Negative 😞"
        elif positive_count > 0 or negative_count > 0: # If there are reviews but not strongly one way
            overall_category = "Mixed Feelings 😐"
        else: # Should fall into neutral_count, but handle explicitly
            overall_category = "Neutral 😐"

    return {
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': total_analyzed - positive_count - negative_count, # Calculate neutral count based on analyzed reviews
        'total_analyzed': total_analyzed,
        'overall_category': overall_category,
        'individual_results': individual_results
    }
