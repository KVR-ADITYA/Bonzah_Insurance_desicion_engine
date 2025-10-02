"""
Insurance Risk Score Calculator
Single file implementation with pickled models
Returns risk scores from 1-100 for each component
"""

import pandas as pd
import numpy as np
import pickle

# ============================================
# LOAD TRAINED MODELS
# ============================================

def load_models():
    """Load pickled models"""
    with open('component_models.pkl', 'rb') as f:
        models = pickle.load(f)
    
    print("✅ Models loaded successfully!\n")
    return models

# Load models once at module level
models = load_models()
age_model = models['age_model']
vehicle_model = models['vehicle_model']
location_model = models['location_model']
gender_model = models['gender_model']
le_body = models['label_encoders']['veh_body']
le_gender = models['label_encoders']['gender']
le_area = models['label_encoders']['area']
weights = models['weights']

# ============================================
# INDIVIDUAL COMPONENT SCORING FUNCTIONS
# ============================================

def get_age_risk_score(age_category):
    """
    Get risk score for driver age category
    
    Parameters:
    - age_category: int (1-6)
        1 = 18-25 years (youngest)
        2 = 26-35 years
        3 = 36-45 years
        4 = 46-55 years
        5 = 56-65 years
        6 = 66+ years (oldest)
    
    Returns:
    - risk_score: int (1-100)
    """
    prob = age_model.predict_proba([[age_category]])[0, 1]
    risk_score = int(prob * 100)
    return risk_score


def get_vehicle_risk_score(vehicle_value, vehicle_age, vehicle_body):
    """
    Get risk score for vehicle characteristics
    
    Parameters:
    - vehicle_value: int (1-10 scale, 1=lowest value, 10=highest)
    - vehicle_age: int (1-4)
        1 = 0-2 years (newest)
        2 = 3-5 years
        3 = 6-10 years
        4 = 11+ years (oldest)
    - vehicle_body: str (e.g., 'SEDAN', 'SUV', 'HBACK', 'TRUCK', 'COUPE', etc.)
    
    Returns:
    - risk_score: int (1-100)
    """
    try:
        body_encoded = le_body.transform([vehicle_body.upper()])[0]
    except ValueError:
        print(f"⚠️  Unknown vehicle body type: {vehicle_body}")
        print(f"    Valid types: {list(le_body.classes_)}")
        return None
    
    prob = vehicle_model.predict_proba([[vehicle_value, vehicle_age, body_encoded]])[0, 1]
    risk_score = int(prob * 100)
    return risk_score


def get_location_risk_score(area):
    """
    Get risk score for geographic area
    
    Parameters:
    - area: str ('A', 'B', 'C', 'D', 'E', or 'F')
        A = highest risk areas (urban)
        F = lowest risk areas (rural)
    
    Returns:
    - risk_score: int (1-100)
    """
    try:
        area_encoded = le_area.transform([area.upper()])[0]
    except ValueError:
        print(f"⚠️  Unknown area: {area}")
        print(f"    Valid areas: {list(le_area.classes_)}")
        return None
    
    prob = location_model.predict_proba([[area_encoded]])[0, 1]
    risk_score = int(prob * 100)
    return risk_score


def get_gender_risk_score(gender):
    """
    Get risk score for driver gender
    
    Parameters:
    - gender: str ('M' or 'F')
    
    Returns:
    - risk_score: int (1-100)
    """
    try:
        gender_encoded = le_gender.transform([gender.upper()])[0]
    except ValueError:
        print(f"⚠️  Unknown gender: {gender}")
        print(f"    Valid genders: {list(le_gender.classes_)}")
        return None
    
    prob = gender_model.predict_proba([[gender_encoded]])[0, 1]
    risk_score = int(prob * 100)
    return risk_score


# ============================================
# COMBINED SCORING FUNCTION
# ============================================

def get_all_risk_scores(age_category, vehicle_value, vehicle_age, vehicle_body, area, gender):
    """
    Get risk scores from all component models
    
    Parameters:
    - age_category: int (1-6)
    - vehicle_value: int (1-10)
    - vehicle_age: int (1-4)
    - vehicle_body: str
    - area: str (A-F)
    - gender: str (M/F)
    
    Returns:
    - dict with keys: 'age', 'vehicle', 'location', 'gender', 'final_weighted'
    """
    scores = {}
    
    # Get individual component scores
    scores['age'] = get_age_risk_score(age_category)
    scores['vehicle'] = get_vehicle_risk_score(vehicle_value, vehicle_age, vehicle_body)
    scores['location'] = get_location_risk_score(area)
    scores['gender'] = get_gender_risk_score(gender)
    
    # Check if any score failed
    if None in scores.values():
        return None
    
    # Calculate weighted final score using learned weights
    component_array = np.array([scores['age'], scores['vehicle'], 
                                scores['location'], scores['gender']])
    
    final_score = int(np.dot(component_array, weights))
    scores['final_weighted'] = final_score
    
    return scores


# ============================================
# DISPLAY FUNCTIONS
# ============================================

def display_risk_scores(scores):
    """Pretty print risk scores"""
    if scores is None:
        print("❌ Could not calculate scores due to invalid input")
        return
    
    print("\n" + "="*60)
    print("INDIVIDUAL COMPONENT RISK SCORES (1-100)")
    print("="*60)
    
    print(f"\n📊 Age Risk Score:        {scores['age']:3d}/100")
    print(f"📊 Vehicle Risk Score:    {scores['vehicle']:3d}/100")
    print(f"📊 Location Risk Score:   {scores['location']:3d}/100")
    print(f"📊 Gender Risk Score:     {scores['gender']:3d}/100")
    
    print("\n" + "-"*60)
    print(f"🎯 FINAL WEIGHTED SCORE:  {scores['final_weighted']:3d}/100")
    print("-"*60)
    
    # Risk interpretation
    final = scores['final_weighted']
    if final < 30:
        risk_level = "🟢 LOW RISK"
        premium_tier = "Preferred ($800-1200/year)"
    elif final < 50:
        risk_level = "🟡 MODERATE RISK"
        premium_tier = "Standard ($1200-1800/year)"
    elif final < 70:
        risk_level = "🟠 HIGH RISK"
        premium_tier = "Non-Standard ($1800-2500/year)"
    else:
        risk_level = "🔴 VERY HIGH RISK"
        premium_tier = "High Risk ($2500+/year)"
    
    print(f"\nRisk Level: {risk_level}")
    print(f"Estimated Premium Tier: {premium_tier}")


# ============================================
# HELPER FUNCTIONS
# ============================================

def age_to_category(actual_age):
    """
    Convert actual age to category
    
    Parameters:
    - actual_age: int (18-99)
    
    Returns:
    - category: int (1-6)
    """
    if actual_age < 26:
        return 1
    elif actual_age < 36:
        return 2
    elif actual_age < 46:
        return 3
    elif actual_age < 56:
        return 4
    elif actual_age < 66:
        return 5
    else:
        return 6


def show_all_age_scores():
    """Display risk scores for all age categories"""
    print("\n" + "="*60)
    print("AGE RISK SCORES FOR ALL CATEGORIES")
    print("="*60)
    age_ranges = ["18-25", "26-35", "36-45", "46-55", "56-65", "66+"]
    for cat in range(1, 7):
        score = get_age_risk_score(cat)
        print(f"Category {cat} ({age_ranges[cat-1]:>6s}): {score:3d}/100")


def show_all_vehicle_bodies(vehicle_value=5, vehicle_age=2):
    """Display risk scores for all vehicle body types"""
    print("\n" + "="*60)
    print(f"VEHICLE BODY TYPE RISK SCORES")
    print(f"(value={vehicle_value}, age={vehicle_age})")
    print("="*60)
    for body_type in le_body.classes_:
        score = get_vehicle_risk_score(vehicle_value, vehicle_age, body_type)
        print(f"{body_type:10s}: {score:3d}/100")


def show_all_areas():
    """Display risk scores for all geographic areas"""
    print("\n" + "="*60)
    print("GEOGRAPHIC AREA RISK SCORES")
    print("="*60)
    for area in le_area.classes_:
        score = get_location_risk_score(area)
        print(f"Area {area}: {score:3d}/100")


# ============================================
# BATCH SCORING
# ============================================

def batch_score_applicants(applicants_df):
    """
    Score multiple applicants at once
    
    Parameters:
    - applicants_df: DataFrame with columns:
        ['age_category', 'vehicle_value', 'vehicle_age', 'vehicle_body', 'area', 'gender']
    
    Returns:
    - DataFrame with risk score columns added
    """
    results = []
    
    for idx, row in applicants_df.iterrows():
        scores = get_all_risk_scores(
            row['age_category'],
            row['vehicle_value'],
            row['vehicle_age'],
            row['vehicle_body'],
            row['area'],
            row['gender']
        )
        
        if scores:
            results.append({
                'applicant_id': idx,
                'age_risk': scores['age'],
                'vehicle_risk': scores['vehicle'],
                'location_risk': scores['location'],
                'gender_risk': scores['gender'],
                'final_risk': scores['final_weighted']
            })
    
    return pd.DataFrame(results)


# ============================================
# INTERACTIVE CALCULATOR
# ============================================

def interactive_calculator():
    """Interactive command-line risk calculator"""
    print("\n" + "="*60)
    print("INTERACTIVE RISK SCORE CALCULATOR")
    print("="*60)
    
    # Get age
    print("\n📋 Driver Age:")
    actual_age = int(input("Enter age (18-99): "))
    age_category = age_to_category(actual_age)
    print(f"   → Age category: {age_category}")
    
    # Get vehicle info
    print("\n📋 Vehicle Value:")
    print("   1-10 scale (1=lowest value ~$5k, 10=highest value ~$80k+)")
    vehicle_value = int(input("Enter vehicle value (1-10): "))
    
    print("\n📋 Vehicle Age:")
    print("   1 = 0-2 years (newest)")
    print("   2 = 3-5 years")
    print("   3 = 6-10 years")
    print("   4 = 11+ years (oldest)")
    vehicle_age = int(input("Enter vehicle age category (1-4): "))
    
    print(f"\n📋 Vehicle Body Types: {', '.join(le_body.classes_)}")
    vehicle_body = input("Enter vehicle body type: ").upper()
    
    # Get location
    print("\n📋 Geographic Area (A=urban/high risk, F=rural/low risk):")
    area = input("Enter area (A-F): ").upper()
    
    # Get gender
    gender = input("\n📋 Enter gender (M/F): ").upper()
    
    # Calculate and display scores
    scores = get_all_risk_scores(age_category, vehicle_value, vehicle_age, 
                                  vehicle_body, area, gender)
    display_risk_scores(scores)
    
    return scores


# ============================================
# MAIN DEMO
# ============================================

if __name__ == "__main__":
    print("="*60)
    print("INSURANCE RISK SCORE CALCULATOR")
    print("="*60)
    
    # Example 1: Young driver (18 years old)
    print("\n\n### EXAMPLE 1: Young Driver (Age 18) ###")
    scores_young = get_all_risk_scores(
        age_category=1,        # 18-25 years
        vehicle_value=6,       # Mid-range vehicle
        vehicle_age=2,         # 3-5 years old
        vehicle_body='SEDAN',
        area='C',              # Suburban
        gender='M'
    )
    display_risk_scores(scores_young)
    
    # Example 2: Middle-aged driver
    print("\n\n### EXAMPLE 2: Middle-Aged Driver (Age 45) ###")
    scores_middle = get_all_risk_scores(
        age_category=4,        # 46-55 years
        vehicle_value=7,       # Higher value vehicle
        vehicle_age=1,         # New vehicle
        vehicle_body='SUV',
        area='B',              # Urban
        gender='F'
    )
    display_risk_scores(scores_middle)
    
    # Example 3: Senior driver
    print("\n\n### EXAMPLE 3: Senior Driver (Age 70) ###")
    scores_senior = get_all_risk_scores(
        age_category=6,        # 66+ years
        vehicle_value=5,       # Mid-range vehicle
        vehicle_age=3,         # Older vehicle
        vehicle_body='SEDAN',
        area='E',              # Rural
        gender='M'
    )
    display_risk_scores(scores_senior)
    
    # Show reference tables
    show_all_age_scores()
    show_all_areas()
    show_all_vehicle_bodies()
    
    # Quick examples
    print("\n\n" + "="*60)
    print("QUICK INDIVIDUAL SCORE EXAMPLES")
    print("="*60)
    print(f"\nAge 18 (category 1) → Risk Score: {get_age_risk_score(1)}/100")
    print(f"Mid-value SEDAN → Risk Score: {get_vehicle_risk_score(6, 2, 'SEDAN')}/100")
    print(f"Area C (suburban) → Risk Score: {get_location_risk_score('C')}/100")
    print(f"Male driver → Risk Score: {get_gender_risk_score('M')}/100")
    
    # Batch scoring example
    print("\n\n" + "="*60)
    print("BATCH SCORING EXAMPLE")
    print("="*60)
    
    sample_applicants = pd.DataFrame({
        'age_category': [1, 3, 5, 2, 6],
        'vehicle_value': [5, 7, 4, 8, 6],
        'vehicle_age': [2, 1, 3, 2, 2],
        'vehicle_body': ['SEDAN', 'SUV', 'HBACK', 'TRUCK', 'SEDAN'],
        'area': ['C', 'B', 'E', 'D', 'F'],
        'gender': ['M', 'F', 'M', 'M', 'F']
    })
    
    batch_results = batch_score_applicants(sample_applicants)
    print("\nBatch Scoring Results:")
    print(batch_results.to_string(index=False))
    
    # Uncomment to run interactive calculator
    # print("\n\n")
    # interactive_calculator()