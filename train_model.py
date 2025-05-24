import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import pickle
from data.data_loader import load_and_preprocess_data  # Import preprocessing function
import os
from sklearn.preprocessing import StandardScaler  # Ensure StandardScaler is imported


def train_and_save_models(
    csv_path="data/tamil_nadu_tourist_place3.csv", model_dir="models"
):
    """
    Trains Random Forest Regressor models for budget prediction and saves them.

    Args:
        csv_path (str, optional): Path to the CSV data file.
        model_dir (str, optional): Directory to save the trained models.
    """
    # load_and_preprocess_data now returns the fitted scaler
    X_train, X_test, y_train, y_test, scaler = load_and_preprocess_data(csv_path)

    target_cols = [
        "hotel_budget",
        "hotel_luxury",
        "food_budget",
        "food_luxury",
        "local_transport_urban",
        "local_transport_rural",
    ]
    models = {}

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    # ***DEFINE CONSISTENT FEATURE LIST ONCE***
    common_features = [
        col for col in X_train.columns if col not in target_cols
    ]  # Exclude target columns

    # Save the common_features for use in prediction (price_calculator.py)
    # This is a simple way to pass it; you might want a more robust config system
    with open(os.path.join(model_dir, "common_features.pkl"), "wb") as f:
        pickle.dump(common_features, f)

    for target_col in target_cols:
        if target_col in y_train.columns:
            # ***USE CONSISTENT FEATURE LIST FOR TRAINING***
            current_X_train_for_model = X_train[
                common_features
            ]  # Select only common features
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(current_X_train_for_model, y_train[target_col])
            models[target_col] = model
            print(f"Trained model for: {target_col}")
        else:
            print(f"Target column not found in y_train: {target_col}")

    # Save the models
    model_path = os.path.join(model_dir, "models.pkl")
    try:
        with open(model_path, "wb") as f:
            pickle.dump(models, f)
        print(f"Trained models saved to {model_path}")
    except Exception as e:
        print(f"Error saving models: {e}")

    # Save the scaler
    scaler_path = os.path.join(model_dir, "scaler.pkl")
    try:
        with open(scaler_path, "wb") as f:
            pickle.dump(scaler, f)
        print(f"Scaler saved to {scaler_path}")
    except Exception as e:
        print(f"Error saving scaler: {e}")


if __name__ == "__main__":
    train_and_save_models()