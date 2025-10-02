# Import the file
from risk_calculator import *

# Get individual scores
age_score = get_age_risk_score(1)  # Returns 1-100
print(f"Risk score: {age_score}")

# Get all scores at once
scores = get_all_risk_scores(
    age_category=1,
    vehicle_value=6,
    vehicle_age=2,
    vehicle_body='SEDAN',
    area='C',
    gender='M'
)
print(scores)
# Returns: {'age': 78, 'vehicle': 52, 'location': 45, 'gender': 51, 'final_weighted': 61}

# Display nicely formatted
display_risk_scores(scores)

# Run interactive calculator
interactive_calculator()