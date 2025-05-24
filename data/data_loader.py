import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from geopy.distance import geodesic  # Import geodesic here


def load_and_preprocess_data(csv_path="data/tamil_nadu_tourist_place3.csv"):
    """
    Loads, preprocesses, and splits the travel data for model training.

    Args:
        csv_path (str, optional): Path to the CSV file.

    Returns:
        tuple: (X_train, X_test, y_train, y_test, scaler) - Split and preprocessed data, and the fitted scaler.
    """

    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError(f"CSV file at '{csv_path}' is empty!")
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at '{csv_path}'")
    except pd.errors.EmptyDataError:
        raise pd.errors.EmptyDataError(f"CSV file at '{csv_path}' contains no data")
    except Exception as e:
        raise Exception(f"Error loading CSV file: {e}")

    # 1. One-hot encode categorical features
    categorical_cols = ["city", "district", "category", "season"]
    df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

    # 2. Handle potential multicollinearity (example: dropping mid-tier columns)
    # Ensure these columns exist before attempting to drop
    if "hotel_mid" in df_encoded.columns:
        df_encoded = df_encoded.drop(columns=["hotel_mid"])
    if "food_mid" in df_encoded.columns:
        df_encoded = df_encoded.drop(columns=["food_mid"])

    # 3. Feature Scaling for numerical columns
    numerical_cols = [
        "lat",
        "lng",
        "bus_km_rate",
        "train_km_rate",
        "flight_base_rate",
        "local_transport_urban",
        "local_transport_rural",
    ]

    # Create a new StandardScaler instance
    scaler = StandardScaler()

    # Apply scaling only to columns that exist in the DataFrame
    cols_to_scale_exist = [col for col in numerical_cols if col in df_encoded.columns]
    if cols_to_scale_exist:
        df_encoded[cols_to_scale_exist] = scaler.fit_transform(
            df_encoded[cols_to_scale_exist]
        )

    # 4. Define Target Variables
    target_cols = [
        "hotel_budget",
        "hotel_luxury",
        "food_budget",
        "food_luxury",
        "local_transport_urban",
        "local_transport_rural",
    ]

    # Ensure target columns are handled correctly, dropping only if they exist
    features = df_encoded.drop(
        columns=[col for col in target_cols if col in df_encoded.columns],
        errors="ignore",
    )
    targets = df_encoded[target_cols]

    # 5. Split Data
    X_train, X_test, y_train, y_test = train_test_split(
        features, targets, test_size=0.2, random_state=42
    )

    return X_train, X_test, y_train, y_test, scaler


def load_original_data(csv_path="data/tamil_nadu_tourist_place3.csv"):
    """
    Loads the original, unprocessed data.

    Args:
        csv_path (str, optional): Path to the CSV file.

    Returns:
        pd.DataFrame: The original DataFrame.
    """
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            raise ValueError(f"CSV file at '{csv_path}' is empty!")
        return df
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at '{csv_path}'")
    except pd.errors.EmptyDataError:
        raise pd.errors.EmptyDataError(f"CSV file at '{csv_path}' contains no data")
    except Exception as e:
        raise Exception(f"Error loading CSV file: {e}")


def get_city_coordinates(df, city_name):
    """
    Gets the latitude and longitude coordinates for a given city.

    Args:
        df (pd.DataFrame): The DataFrame containing city data.
        city_name (str): The name of the city.

    Returns:
        tuple: (latitude, longitude)
    """
    try:
        city = df[df["city"] == city_name].iloc[0]
        return (city["lat"], city["lng"])
    except IndexError:
        raise ValueError(f"City '{city_name}' not found in the DataFrame.")


def calculate_distance(df, from_city, to_city):
    """
    Calculates the geodesic distance between two cities.

    Args:
        df (pd.DataFrame): The DataFrame containing city data.
        from_city (str): The origin city.
        to_city (str): The destination city.

    Returns:
        float: The distance in kilometers.
    """
    try:
        coord1 = get_city_coordinates(df, from_city)
        coord2 = get_city_coordinates(df, to_city)
        return geodesic(coord1, coord2).km
    except ValueError as e:
        raise ValueError(f"Error calculating distance: {e}")


if __name__ == "__main__":
    try:
        X_train, X_test, y_train, y_test, scaler_obj = load_and_preprocess_data()
        print("X_train shape:", X_train.shape)
        print("y_train shape:", y_train.shape)
        print("X_test shape:", X_test.shape)
        print("y_test shape:", y_test.shape)
        print("Scaler type:", type(scaler_obj))

        original_df = load_original_data()
        print("Original DataFrame shape:", original_df.shape)

        # Example distance calculation
        if not original_df.empty:
            try:
                distance = calculate_distance(original_df, "Chennai", "Madurai")
                print(f"Distance between Chennai and Madurai: {distance:.2f} km")
            except ValueError as e:
                print(f"Error calculating distance: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")