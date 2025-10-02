import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, mean_squared_error

# ============================================
# LOAD DATA
# ============================================

df_car = pd.read_csv('datacar.csv')

# Clean data
df_car = df_car[df_car['X_OBSTAT_'] != -1]  # Remove bad observations
df_car = df_car.dropna()

print(f"Total policies: {len(df_car):,}")
print(f"Claim rate: {df_car['clm'].mean():.2%}")

# ============================================
# PREPARE FEATURES
# ============================================

# Convert categorical to numeric if needed
from sklearn.preprocessing import LabelEncoder

le_body = LabelEncoder()
le_gender = LabelEncoder()
le_area = LabelEncoder()

df_car['veh_body_encoded'] = le_body.fit_transform(df_car['veh_body'])
df_car['gender_encoded'] = le_gender.fit_transform(df_car['gender'])
df_car['area_encoded'] = le_area.fit_transform(df_car['area'])

# ============================================
# COMPONENT 1: DRIVER AGE MODEL
# ============================================

print("\n" + "="*50)
print("COMPONENT 1: Driver Age Model")
print("="*50)

X_age = df_car[['agecat']]
y_freq = df_car['clm']

X_train, X_test, y_train, y_test = train_test_split(X_age, y_freq, test_size=0.2, random_state=42)

age_model = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
age_model.fit(X_train, y_train)

age_risk_scores = age_model.predict_proba(X_test)[:, 1]
print(f"Age Model AUC: {roc_auc_score(y_test, age_risk_scores):.4f}")

# Analyze age effect
print("\nClaim Rate by Age Category:")
print(df_car.groupby('agecat')['clm'].agg(['mean', 'count']))

# ============================================
# COMPONENT 2: VEHICLE MODEL
# ============================================

print("\n" + "="*50)
print("COMPONENT 2: Vehicle Characteristics Model")
print("="*50)

X_vehicle = df_car[['veh_value', 'veh_age', 'veh_body_encoded']]
y_freq = df_car['clm']

X_train, X_test, y_train, y_test = train_test_split(X_vehicle, y_freq, test_size=0.2, random_state=42)

vehicle_model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
vehicle_model.fit(X_train, y_train)

vehicle_risk_scores = vehicle_model.predict_proba(X_test)[:, 1]
print(f"Vehicle Model AUC: {roc_auc_score(y_test, vehicle_risk_scores):.4f}")

# Feature importance
print("\nVehicle Feature Importance:")
for feat, imp in zip(['veh_value', 'veh_age', 'veh_body'], vehicle_model.feature_importances_):
    print(f"  {feat}: {imp:.3f}")

# ============================================
# COMPONENT 3: LOCATION MODEL
# ============================================

print("\n" + "="*50)
print("COMPONENT 3: Geographic Location Model")
print("="*50)

X_location = df_car[['area_encoded']]
y_freq = df_car['clm']

X_train, X_test, y_train, y_test = train_test_split(X_location, y_freq, test_size=0.2, random_state=42)

location_model = RandomForestClassifier(n_estimators=100, max_depth=3, random_state=42)
location_model.fit(X_train, y_train)

location_risk_scores = location_model.predict_proba(X_test)[:, 1]
print(f"Location Model AUC: {roc_auc_score(y_test, location_risk_scores):.4f}")

print("\nClaim Rate by Area:")
print(df_car.groupby('area')['clm'].agg(['mean', 'count']))

# ============================================
# COMPONENT 4: GENDER MODEL (demographic)
# ============================================

print("\n" + "="*50)
print("COMPONENT 4: Driver Gender Model")
print("="*50)

X_gender = df_car[['gender_encoded']]
y_freq = df_car['clm']

X_train, X_test, y_train, y_test = train_test_split(X_gender, y_freq, test_size=0.2, random_state=42)

gender_model = RandomForestClassifier(n_estimators=100, max_depth=2, random_state=42)
gender_model.fit(X_train, y_train)

gender_risk_scores = gender_model.predict_proba(X_test)[:, 1]
print(f"Gender Model AUC: {roc_auc_score(y_test, gender_risk_scores):.4f}")

print("\nClaim Rate by Gender:")
print(df_car.groupby('gender')['clm'].agg(['mean', 'count']))

# ============================================
# COMBINE COMPONENTS: WEIGHTED ENSEMBLE
# ============================================

print("\n" + "="*50)
print("WEIGHTED ENSEMBLE MODEL")
print("="*50)

# Prepare full dataset
X_full = df_car[['agecat', 'veh_value', 'veh_age', 'veh_body_encoded', 
                 'area_encoded', 'gender_encoded']]
y_full = df_car['clm']

X_train_full, X_test_full, y_train_full, y_test_full = train_test_split(
    X_full, y_full, test_size=0.2, random_state=42
)

# Get component scores on test set
age_scores = age_model.predict_proba(X_test_full[['agecat']])[:, 1]
vehicle_scores = vehicle_model.predict_proba(
    X_test_full[['veh_value', 'veh_age', 'veh_body_encoded']]
)[:, 1]
location_scores = location_model.predict_proba(X_test_full[['area_encoded']])[:, 1]
gender_scores = gender_model.predict_proba(X_test_full[['gender_encoded']])[:, 1]

# Stack component scores
component_scores = np.column_stack([
    age_scores,
    vehicle_scores,
    location_scores,
    gender_scores
])

# Method 1: Learn optimal weights with Ridge
from sklearn.linear_model import Ridge

meta_model = Ridge(alpha=1.0, fit_intercept=False, positive=True)
meta_model.fit(component_scores, y_test_full)

# Normalize weights to sum to 1
weights = meta_model.coef_ / meta_model.coef_.sum()

print("\n📊 Learned Component Weights:")
print(f"  Age:      {weights[0]:.3f} ({weights[0]*100:.1f}%)")
print(f"  Vehicle:  {weights[1]:.3f} ({weights[1]*100:.1f}%)")
print(f"  Location: {weights[2]:.3f} ({weights[2]*100:.1f}%)")
print(f"  Gender:   {weights[3]:.3f} ({weights[3]*100:.1f}%)")

# Calculate final ensemble scores
ensemble_scores = component_scores @ weights

# Evaluate
ensemble_auc = roc_auc_score(y_test_full, ensemble_scores)
print(f"\n🎯 Ensemble AUC: {ensemble_auc:.4f}")

# Compare to single model
from sklearn.ensemble import RandomForestClassifier
single_model = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
single_model.fit(X_train_full, y_train_full)
single_scores = single_model.predict_proba(X_test_full)[:, 1]
single_auc = roc_auc_score(y_test_full, single_scores)

print(f"📊 Single Model AUC: {single_auc:.4f}")
print(f"✨ Improvement: {(ensemble_auc - single_auc)*100:+.2f} percentage points")

# ============================================
# SAVE COMPONENT MODELS
# ============================================

import pickle

models = {
    'age_model': age_model,
    'vehicle_model': vehicle_model,
    'location_model': location_model,
    'gender_model': gender_model,
    'weights': weights,
    'label_encoders': {
        'veh_body': le_body,
        'gender': le_gender,
        'area': le_area
    }
}

with open('component_models.pkl', 'wb') as f:
    pickle.dump(models, f)

print("\n✅ Component models saved to 'component_models.pkl'")