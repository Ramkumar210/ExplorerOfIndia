import pandas as pd
import pickle
import os
from sklearn.preprocessing import StandardScaler  # Ensure StandardScaler is imported


class PriceCalculator:
    def __init__(
        self,
        original_df,
        model_path="models/models.pkl",
        scaler_path="models/scaler.pkl",
    ):
        """
        Initializes the PriceCalculator.

        Args:
            original_df (pd.DataFrame): The original (unprocessed) DataFrame.
            model_path (str, optional): Path to the saved model file.
            scaler_path (str, optional): Path to the saved scaler file.
        """
        self.original_df = original_df
        self.models = self._load_models(model_path)
        self.scaler = self._load_scaler(scaler_path)

        # We will no longer rely solely on hotel_budget's feature_names_in_ for self.feature_cols
        # Instead, we will get feature names dynamically for each model in predict_budget.
        # However, we still need a base set of features for _prepare_base_input_data.
        # Let's infer a comprehensive set of features from the data itself.
        self.base_feature_cols = self._infer_feature_columns_from_data_comprehensive()
        print(
            f"DEBUG: Base feature columns inferred for preparation: {self.base_feature_cols}"
        )

    def _infer_feature_columns_from_data_comprehensive(self):
        """
        Infers a comprehensive set of potential feature columns from the original data
        by simulating preprocessing, excluding only the explicit target columns.
        This will be used to build the initial input_df before reindexing to specific model features.
        """
        temp_df = self.original_df.copy()
        categorical_cols = ["city", "district", "category", "season"]
        temp_df_encoded = pd.get_dummies(
            temp_df, columns=categorical_cols, drop_first=True
        )

        if "hotel_mid" in temp_df_encoded.columns:
            temp_df_encoded = temp_df_encoded.drop(columns=["hotel_mid"])
        if "food_mid" in temp_df_encoded.columns:
            temp_df_encoded = temp_df_encoded.drop(columns=["food_mid"])

        # Exclude all target columns from the comprehensive feature set
        all_target_cols = [
            "hotel_budget",
            "hotel_luxury",
            "food_budget",
            "food_luxury",
            "local_transport_urban",
            "local_transport_rural",
        ]

        features_df = temp_df_encoded.drop(
            columns=[col for col in all_target_cols if col in temp_df_encoded.columns],
            errors="ignore",
        )
        return features_df.columns.tolist()

    def _load_models(self, model_path):
        """
        Loads the trained machine learning models.

        Args:
            model_path (str): Path to the saved model file.

        Returns:
            dict: A dictionary containing the loaded models, or None if loading fails.
        """
        if not os.path.exists(model_path):
            print(
                f"Error: Model file not found at {model_path}. Please train the models first."
            )
            return None
        try:
            with open(model_path, "rb") as f:
                models = pickle.load(f)
            return models
        except FileNotFoundError:
            print(f"Error: Model file not found at {model_path}.")
            return None
        except pickle.UnpicklingError as e:
            print(f"Error unpickling models: {e}. File might be corrupted.")
            return None
        except Exception as e:
            print(f"Error loading models: {e}")
            return None

    def _load_scaler(self, scaler_path):
        """Loads the StandardScaler fitted during training."""
        if not os.path.exists(scaler_path):
            print(f"Warning: Scaler file not found at {scaler_path}.")
            return None
        try:
            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)
            return scaler
        except FileNotFoundError:
            print(f"Warning: Scaler file not found at {scaler_path}.")
            return None
        except pickle.UnpicklingError as e:
            print(f"Error unpickling scaler: {e}. File might be corrupted.")
            return None
        except Exception as e:
            print(f"Error loading scaler: {e}")
            return None

    def predict_budget(self, city, season, budget_tier):
        """
        Predicts the budget components for a given city, season, and budget tier.

        Args:
            city (str): The city.
            season (str): The season.
            budget_tier (str): The budget tier ('budget', 'luxury').

        Returns:
            dict: A dictionary of predicted budget components, or None if models are not loaded.
        """
        if self.models is None:
            return None

        predictions = {}

        # Prepare a base input DataFrame that contains all potential features, scaled
        base_input_df = self._prepare_base_input_data(city, season)

        try:
            # Predict hotel budget
            hotel_model = self.models[f"hotel_{budget_tier}"]
            hotel_features = (
                hotel_model.feature_names_in_.tolist()
                if hasattr(hotel_model, "feature_names_in_")
                else self.base_feature_cols
            )
            input_for_hotel = base_input_df.reindex(
                columns=hotel_features, fill_value=0
            )
            print(f"DEBUG: Hotel model expects features: {hotel_features}")
            print(
                f"DEBUG: Input for hotel model has columns: {input_for_hotel.columns.tolist()}"
            )
            predictions["hotel"] = hotel_model.predict(input_for_hotel)[0]

            # Predict food budget
            food_model = self.models[f"food_{budget_tier}"]
            food_features = (
                food_model.feature_names_in_.tolist()
                if hasattr(food_model, "feature_names_in_")
                else self.base_feature_cols
            )
            input_for_food = base_input_df.reindex(columns=food_features, fill_value=0)
            print(f"DEBUG: Food model expects features: {food_features}")
            print(
                f"DEBUG: Input for food model has columns: {input_for_food.columns.tolist()}"
            )
            predictions["food"] = food_model.predict(input_for_food)[0]

            # Predict local transport urban
            urban_model = self.models["local_transport_urban"]
            urban_features = (
                urban_model.feature_names_in_.tolist()
                if hasattr(urban_model, "feature_names_in_")
                else self.base_feature_cols
            )
            input_for_urban = base_input_df.reindex(
                columns=urban_features, fill_value=0
            )
            print(f"DEBUG: Urban transport model expects features: {urban_features}")
            print(
                f"DEBUG: Input for urban transport model has columns: {input_for_urban.columns.tolist()}"
            )
            predictions["local_transport_urban"] = urban_model.predict(
                input_for_urban
            )[0]

            # Predict local transport rural
            rural_model = self.models["local_transport_rural"]
            rural_features = (
                rural_model.feature_names_in_.tolist()
                if hasattr(rural_model, "feature_names_in_")
                else self.base_feature_cols
            )
            input_for_rural = base_input_df.reindex(
                columns=rural_features, fill_value=0
            )
            print(f"DEBUG: Rural transport model expects features: {rural_features}")
            print(
                f"DEBUG: Input for rural transport model has columns: {input_for_rural.columns.tolist()}"
            )
            predictions["local_transport_rural"] = rural_model.predict(
                input_for_rural
            )[0]

            return predictions
        except KeyError as e:
            print(
                f"Error: Model not found for key: {e}. Ensure models are trained correctly for all tiers."
            )
            return None
        except Exception as e:
            print(f"An unexpected error occurred during prediction: {e}")
            return None

    def _prepare_base_input_data(self, city, season):
        """
        Prepares a comprehensive base input DataFrame with all potential features,
        before reindexing to specific model's feature requirements.
        """
        # 1. Create a DataFrame with city and season
        input_df = pd.DataFrame([{"city": city, "season": season}])

        # 2. Get the city's row from the original DataFrame
        city_row = self.original_df[self.original_df["city"] == city]

        if city_row.empty:
            print(f"Warning: City '{city}' not found in the data.")
            return None  # Or raise an exception, depending on how you want to handle this

        city_row = city_row.iloc[0].to_dict()  # Select the first row after filtering

        # 3. Add all relevant columns from city_row to input_df
        # This list explicitly includes all features from your dataset that are not one-hot encoded.
        for col in [
            "lat",
            "lng",
            "bus_km_rate",
            "train_km_rate",
            "flight_base_rate",
            "district",
            "category",
            "local_transport_urban",  # Include these as they exist in your dataset
            "local_transport_rural",  # Include these as they exist in your dataset
            "bus_available",
            "train_available",
            "flight_available",
        ]:
            input_df[col] = city_row.get(
                col, 0
            )  # Use get() with default to handle missing columns

        # 4. One-hot encode categorical features
        categorical_cols_to_encode = ["city", "district", "category", "season"]
        cols_to_encode_exist = [
            col for col in categorical_cols_to_encode if col in input_df.columns
        ]

        input_df = pd.get_dummies(
            input_df, columns=cols_to_encode_exist, drop_first=True, dummy_na=False
        )

        # 5. Scale numerical features (using the loaded scaler)
        # Scale all numerical features that are part of the base_feature_cols
        # and were used during training.
        numerical_cols_for_scaling = [
            "lat",
            "lng",
            "bus_km_rate",
            "train_km_rate",
            "flight_base_rate",
            "local_transport_urban",
            "local_transport_rural",  # These were part of your original dataset
        ]
        cols_to_scale_exist_in_input = [
            col for col in numerical_cols_for_scaling if col in input_df.columns
        ]

        if self.scaler is not None and cols_to_scale_exist_in_input:
            input_df[cols_to_scale_exist_in_input] = self.scaler.transform(
                input_df[cols_to_scale_exist_in_input]
            )
        elif self.scaler is None:
            print(
                "Warning: Scaler not available. Numerical features not scaled for prediction."
            )

        return input_df

    def calculate_transport_cost(self, city, transport_mode, distance):
        """
        Calculates the transport cost based on mode and distance.

        Args:
            city (str): The origin city.
            transport_mode (str): Mode of transport.
            distance (float): Distance.

        Returns:
            float: The calculated transport cost.
        """
        city_data = self.original_df[self.original_df["city"] == city]
        if city_data.empty:
            print(f"Warning: City '{city}' not found in the data.")
            return 0  # Or raise an exception

        city_data = city_data.iloc[0]

        if transport_mode == "bus":
            cost_per_km = city_data["bus_km_rate"]
        elif transport_mode == "train":
            cost_per_km = city_data["train_km_rate"]
        elif transport_mode == "flight":
            cost = city_data["flight_base_rate"] + (distance * 8)  # Example flight cost
            return cost
        else:
            return 0
        return cost_per_km * distance * 2