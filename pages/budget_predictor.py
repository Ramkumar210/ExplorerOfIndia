import streamlit as st
import pandas as pd
from data.data_loader import load_original_data, calculate_distance
from src.price_calculator import PriceCalculator

# Configure page for the budget predictor
st.set_page_config(page_title="Explorer of INDIA - Budget Predictor", layout="wide")

# Custom CSS to center elements and align text in columns
st.markdown(
    """
    <style>
    .centered-title {
        text-align: center;
    }
    .aligned-label {
        font-weight: bold;
        min-width: 150px; /* Adjust as needed */
        display: inline-block;
    }
    /* Specific button styling for "Back" button */
    .stButton button[key*="back"] {
        background-color: #6c757d; /* Grey for back button */
    }

    .stButton button[key*="back"]:hover {
        background-color: #5a6268;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Load data and initialize calculator (cached for performance)
@st.cache_resource
def initialize_budget_resources():
    try:
        original_df = load_original_data("data/tamil_nadu_tourist_place3.csv")
        calculator = PriceCalculator(original_df)
        return original_df, calculator
    except FileNotFoundError:
        st.error(
            "Budget data file not found. Please ensure 'data/tamil_nadu_tourist_place3.csv' "
            "exists in the 'data' folder."
        )
        st.stop()
    except Exception as e:
        st.error(
            "An error occurred during budget calculator initialization: "
            f"{e}. Please check your data and model files."
        )
        st.stop()

original_df, calculator = initialize_budget_resources()

def main():
    st.title("Travel Budget Predictor")

    if original_df is None or calculator is None:
        return

    # Initial User Inputs
    budget_tier = st.selectbox("Select Budget Tier", ["budget", "medium", "luxury"])
    num_people = st.number_input("Number of People", min_value=1, max_value=20, value=1)
    num_days = st.number_input("Number of Days", min_value=1, max_value=31, value=1)

    trip_details = []
    total_budget = 0.0

    for day in range(1, num_days + 1):
        st.header(f"Day {day}")
        plan_type = st.radio(
            f"Day {day}: Would you like to:",
            ["Explore multiple cities", "Stay & explore local places"],
        )

        daily_plan = {"Day": day}

        if plan_type == "Explore multiple cities":
            from_location = st.selectbox(f"Day {day}: From Location", sorted(original_df["city"].unique()))
            to_location = st.selectbox(f"Day {day}: To Location", sorted([c for c in original_df["city"].unique() if c != from_location]))
            season = st.selectbox(f"Day {day}: Season", ["peak", "offpeak"])
            transport_mode = st.selectbox(f"Day {day}: Transportation", ["train", "bus", "flight"])

            try:
                distance_km = calculate_distance(original_df, from_location, to_location)
                budget_predictions = calculator.predict_budget(from_location, season, budget_tier)

                if budget_predictions:
                    transport_cost = calculator.calculate_transport_cost(from_location, transport_mode, distance_km) * num_people
                    accommodation_cost = budget_predictions.get("hotel", 0) * num_people # Assuming per night cost
                    food_cost = budget_predictions.get("food", 0) * num_people # Assuming per day cost
                    local_transport_cost = 500 # As per your request

                    total_daily_cost = accommodation_cost + food_cost + transport_cost + local_transport_cost

                    daily_plan.update({
                        "Plan Type": plan_type,
                        "Route": f"{from_location} → {to_location}",
                        "Distance": f"{distance_km:,.2f} km",
                        "Season": season.capitalize(),
                        "Transportation": transport_mode.capitalize(),
                        "Accommodation": accommodation_cost,
                        "Food": food_cost,
                        "Transport": transport_cost,
                        "Local Transport": local_transport_cost,
                        "Total Estimated Cost": total_daily_cost,
                    })
                    trip_details.append(daily_plan)
                    total_budget += total_daily_cost
                else:
                    st.error(f"Could not get budget predictions for Day {day}.")
                    return
            except Exception as e:
                st.error(f"Error calculating costs for Day {day}: {e}")
                return

        elif plan_type == "Stay & explore local places":
            location = st.selectbox(f"Day {day}: Location to explore", sorted(original_df["city"].unique()))
            try:
                budget_predictions = calculator.predict_budget(location, "offpeak", budget_tier) # Assuming offpeak and getting local costs
                if budget_predictions:
                    accommodation_cost = budget_predictions.get("hotel", 0) * num_people
                    food_cost = budget_predictions.get("food", 0) * num_people
                    local_transport_cost = budget_predictions.get("local_transport_urban", 500) # Default to 500 if not available

                    total_daily_cost = accommodation_cost + food_cost + local_transport_cost

                    daily_plan.update({
                        "Plan Type": plan_type,
                        "Location": location,
                        "Accommodation": accommodation_cost,
                        "Food": food_cost,
                        "Transport": 0,
                        "Local Transport": local_transport_cost,
                        "Total Estimated Cost": total_daily_cost,
                    })
                    trip_details.append(daily_plan)
                    total_budget += total_daily_cost
                else:
                    st.error(f"Could not get budget predictions for staying in {location} on Day {day}.")
                    return
            except Exception as e:
                st.error(f"Error calculating stay costs for Day {day}: {e}")
                return

        if day < num_days:
            continue_trip = st.radio(f"Day {day}: Continue planning?", ["Yes", "No"])
            if continue_trip == "No":
                break

    st.header("Trip Summary")
    for item in trip_details:
        st.subheader(f"DAY {item['Day']}")
        st.write("Estimated Budget Breakdown:")
        st.write(f"  Accommodation: ₹{int(item.get('Accommodation', 0)):,}")
        st.write(f"  Food: ₹{int(item.get('Food', 0)):,}")
        st.write(f"  Transport: ₹{int(item.get('Transport', 0)):,}")
        st.write(f"  Local Transport: ₹{int(item.get('Local Transport', 500)):,}")
        st.write(f"  **Total Estimated Cost: ₹{int(item['Total Estimated Cost']):,}**")
        st.write("Trip Details:")
        for key, value in item.items():
            if key not in ["Accommodation", "Food", "Transport", "Local Transport", "Total Estimated Cost", "Day", "Plan Type"]:
                st.write(f"  {key.replace('_', ' ').title()}: {value}")
        st.markdown("---")

    st.subheader(f"Total Budget for {num_days} Days:")
    st.write(f"**₹{int(total_budget):,}**")

    st.markdown("---")
    if st.button("Back to Explorer", key="back_to_explorer_from_budget", type="primary"):
        st.switch_page("app.py")

if __name__ == "__main__":
    main()