"""
Insurance Risk Score Calculator - Web UI
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import plotly.graph_objects as go
import plotly.express as px

# ============================================
# PAGE CONFIG
# ============================================

st.set_page_config(
    page_title="Insurance Risk Calculator",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# CUSTOM CSS
# ============================================

st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric label {
        font-size: 14px !important;
        font-weight: 600 !important;
    }
    .risk-low {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    .risk-moderate {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    .risk-high {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    .risk-very-high {
        background: linear-gradient(135deg, #ff0844 0%, #ffb199 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
    }
    h1 {
        color: #1f2937;
        font-weight: 700;
    }
    h2 {
        color: #374151;
        font-weight: 600;
    }
    h3 {
        color: #4b5563;
        font-weight: 600;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 12px;
        border-radius: 8px;
        border: none;
        font-size: 16px;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================
# LOAD MODELS
# ============================================

@st.cache_resource
def load_models():
    """Load pickled models (cached)"""
    try:
        with open('component_models.pkl', 'rb') as f:
            models = pickle.load(f)
        return models
    except FileNotFoundError:
        st.error("❌ Model file 'component_models.pkl' not found. Please ensure the file is in the same directory.")
        st.stop()

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
# SCORING FUNCTIONS
# ============================================

def get_age_risk_score(age_category):
    """Get risk score for driver age category (1-100)"""
    prob = age_model.predict_proba([[age_category]])[0, 1]
    return int(prob * 100)

def get_vehicle_risk_score(vehicle_value, vehicle_age, vehicle_body):
    """Get risk score for vehicle characteristics (1-100)"""
    try:
        body_encoded = le_body.transform([vehicle_body.upper()])[0]
        prob = vehicle_model.predict_proba([[vehicle_value, vehicle_age, body_encoded]])[0, 1]
        return int(prob * 100)
    except:
        return None

def get_location_risk_score(area):
    """Get risk score for geographic area (1-100)"""
    try:
        area_encoded = le_area.transform([area.upper()])[0]
        prob = location_model.predict_proba([[area_encoded]])[0, 1]
        return int(prob * 100)
    except:
        return None

def get_gender_risk_score(gender):
    """Get risk score for driver gender (1-100)"""
    try:
        gender_encoded = le_gender.transform([gender.upper()])[0]
        prob = gender_model.predict_proba([[gender_encoded]])[0, 1]
        return int(prob * 100)
    except:
        return None

def get_all_risk_scores(age_category, vehicle_value, vehicle_age, vehicle_body, area, gender):
    """Get all risk scores and weighted final score"""
    scores = {}
    scores['age'] = get_age_risk_score(age_category)
    scores['vehicle'] = get_vehicle_risk_score(vehicle_value, vehicle_age, vehicle_body)
    scores['location'] = get_location_risk_score(area)
    scores['gender'] = get_gender_risk_score(gender)
    
    if None in scores.values():
        return None
    
    component_array = np.array([scores['age'], scores['vehicle'], 
                                scores['location'], scores['gender']])
    final_score = int(np.dot(component_array, weights))
    scores['final_weighted'] = final_score
    
    return scores

def age_to_category(actual_age):
    """Convert actual age to category (1-6)"""
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

def get_risk_level_info(score):
    """Get risk level, color, and premium tier"""
    if score < 30:
        return {
            'level': '🟢 LOW RISK',
            'color': '#10b981',
            'premium': '$800 - $1,200/year',
            'css_class': 'risk-low'
        }
    elif score < 50:
        return {
            'level': '🟡 MODERATE RISK',
            'color': '#f59e0b',
            'premium': '$1,200 - $1,800/year',
            'css_class': 'risk-moderate'
        }
    elif score < 70:
        return {
            'level': '🟠 HIGH RISK',
            'color': '#ef4444',
            'premium': '$1,800 - $2,500/year',
            'css_class': 'risk-high'
        }
    else:
        return {
            'level': '🔴 VERY HIGH RISK',
            'color': '#dc2626',
            'premium': '$2,500+/year',
            'css_class': 'risk-very-high'
        }

# ============================================
# VISUALIZATION FUNCTIONS
# ============================================

def create_gauge_chart(score, title):
    """Create a gauge chart for risk score"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 20, 'color': '#1f2937'}},
        number={'font': {'size': 40, 'color': '#1f2937'}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#6b7280"},
            'bar': {'color': get_risk_level_info(score)['color']},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#e5e7eb",
            'steps': [
                {'range': [0, 30], 'color': '#d1fae5'},
                {'range': [30, 50], 'color': '#fef3c7'},
                {'range': [50, 70], 'color': '#fee2e2'},
                {'range': [70, 100], 'color': '#fecaca'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': "#1f2937", 'family': "Arial"}
    )
    
    return fig

def create_component_bar_chart(scores):
    """Create horizontal bar chart for component scores"""
    components = ['Age', 'Vehicle', 'Location', 'Gender']
    values = [scores['age'], scores['vehicle'], scores['location'], scores['gender']]
    colors = [get_risk_level_info(v)['color'] for v in values]
    
    fig = go.Figure(go.Bar(
        x=values,
        y=components,
        orientation='h',
        marker=dict(color=colors),
        text=values,
        textposition='auto',
        textfont=dict(size=14, color='white', family='Arial Black')
    ))
    
    fig.update_layout(
        title={
            'text': 'Component Risk Breakdown',
            'font': {'size': 20, 'color': '#1f2937', 'family': 'Arial'}
        },
        xaxis={'range': [0, 100], 'title': 'Risk Score', 'title_font': {'size': 14}},
        yaxis={'title': ''},
        height=300,
        margin=dict(l=20, r=20, t=50, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "#1f2937", 'family': "Arial"}
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#e5e7eb')
    
    return fig

def create_weight_pie_chart():
    """Create pie chart showing model weights"""
    labels = ['Age', 'Vehicle', 'Location', 'Gender']
    values = weights * 100  # Convert to percentages
    colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textfont=dict(size=14, color='white', family='Arial Black')
    )])
    
    fig.update_layout(
        title={
            'text': 'Model Component Weights',
            'font': {'size': 20, 'color': '#1f2937', 'family': 'Arial'}
        },
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': "#1f2937", 'family': "Arial"},
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    return fig

# ============================================
# MAIN APP
# ============================================

def main():
    # Header
    st.title("🚗 Insurance Risk Score Calculator")
    st.markdown("### Calculate insurance risk scores based on driver and vehicle characteristics")
    st.markdown("---")
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("📋 Applicant Information")
        
        # Age input
        st.subheader("👤 Driver Information")
        actual_age = st.slider("Driver Age", 18, 99, 30, help="Select the driver's age")
        age_category = age_to_category(actual_age)
        st.caption(f"Age Category: {age_category} (1=youngest, 6=oldest)")
        
        gender = st.selectbox("Gender", ["M", "F"], format_func=lambda x: "Male" if x == "M" else "Female")
        
        # Vehicle information
        st.subheader("🚙 Vehicle Information")
        vehicle_value = st.slider("Vehicle Value", 1, 10, 5, 
                                  help="1=lowest value (~$5k), 10=highest value (~$80k+)")
        
        vehicle_age = st.select_slider("Vehicle Age", 
                                       options=[1, 2, 3, 4],
                                       value=2,
                                       format_func=lambda x: {
                                           1: "0-2 years (newest)",
                                           2: "3-5 years",
                                           3: "6-10 years",
                                           4: "11+ years (oldest)"
                                       }[x])
        
        vehicle_body = st.selectbox("Vehicle Body Type", 
                                   sorted(le_body.classes_),
                                   index=list(sorted(le_body.classes_)).index('SEDAN') if 'SEDAN' in le_body.classes_ else 0)
        
        # Location
        st.subheader("📍 Location")
        area = st.select_slider("Geographic Area",
                               options=sorted(le_area.classes_),
                               value='C',
                               format_func=lambda x: f"{x} ({'Urban' if x in ['A','B'] else 'Suburban' if x in ['C','D'] else 'Rural'})")
        
        st.markdown("---")
        calculate_button = st.button("🎯 Calculate Risk Score", use_container_width=True)
    
    # Main content area
    if calculate_button or 'scores' in st.session_state:
        # Calculate scores
        scores = get_all_risk_scores(age_category, vehicle_value, vehicle_age, vehicle_body, area, gender)
        
        if scores is None:
            st.error("❌ Error calculating scores. Please check your inputs.")
            return
        
        st.session_state['scores'] = scores
        
        # Display final risk score prominently
        risk_info = get_risk_level_info(scores['final_weighted'])
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"""
                <div class="{risk_info['css_class']}">
                    <h1 style="margin:0; font-size: 48px;">{scores['final_weighted']}/100</h1>
                    <h2 style="margin:10px 0;">Final Risk Score</h2>
                    <h3 style="margin:5px 0;">{risk_info['level']}</h3>
                    <p style="margin:5px 0; font-size: 18px;">Estimated Premium: {risk_info['premium']}</p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Component scores
        st.subheader("📊 Individual Component Scores")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Age Risk", f"{scores['age']}/100", 
                     delta=None,
                     help=f"Based on age category {age_category}")
        
        with col2:
            st.metric("Vehicle Risk", f"{scores['vehicle']}/100",
                     delta=None,
                     help=f"Based on {vehicle_body}, value {vehicle_value}, age {vehicle_age}")
        
        with col3:
            st.metric("Location Risk", f"{scores['location']}/100",
                     delta=None,
                     help=f"Based on area {area}")
        
        with col4:
            st.metric("Gender Risk", f"{scores['gender']}/100",
                     delta=None,
                     help="Based on driver gender")
        
        st.markdown("---")
        
        # Visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(create_component_bar_chart(scores), use_container_width=True)
        
        with col2:
            st.plotly_chart(create_weight_pie_chart(), use_container_width=True)
        
        # Detailed breakdown
        with st.expander("📋 View Detailed Breakdown"):
            st.markdown("### Input Summary")
            input_df = pd.DataFrame({
                'Category': ['Driver Age', 'Gender', 'Vehicle Value', 'Vehicle Age', 'Vehicle Type', 'Area'],
                'Value': [
                    f"{actual_age} years (Category {age_category})",
                    "Male" if gender == "M" else "Female",
                    f"{vehicle_value}/10",
                    {1: "0-2 years", 2: "3-5 years", 3: "6-10 years", 4: "11+ years"}[vehicle_age],
                    vehicle_body,
                    f"{area} ({'Urban' if area in ['A','B'] else 'Suburban' if area in ['C','D'] else 'Rural'})"
                ]
            })
            st.dataframe(input_df, use_container_width=True, hide_index=True)
            
            st.markdown("### Score Breakdown")
            score_df = pd.DataFrame({
                'Component': ['Age', 'Vehicle', 'Location', 'Gender', 'Final (Weighted)'],
                'Risk Score': [scores['age'], scores['vehicle'], scores['location'], 
                              scores['gender'], scores['final_weighted']],
                'Weight': [f"{w*100:.1f}%" for w in weights] + ['100%']
            })
            st.dataframe(score_df, use_container_width=True, hide_index=True)
    
    else:
        # Initial state - show instructions
        st.info("👈 Fill out the applicant information in the sidebar and click 'Calculate Risk Score' to begin.")
        
        # Show sample statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            ### 🎯 How It Works
            Our risk calculator uses machine learning models trained on real insurance data to predict claim probability.
            
            Each component (age, vehicle, location, gender) is scored independently, then combined using learned weights.
            """)
        
        with col2:
            st.markdown("""
            ### 📊 Risk Levels
            - **🟢 Low (1-29)**: Preferred rates
            - **🟡 Moderate (30-49)**: Standard rates
            - **🟠 High (50-69)**: Non-standard rates
            - **🔴 Very High (70-100)**: High-risk rates
            """)
        
        with col3:
            st.markdown("""
            ### 💡 Key Factors
            - Young drivers (18-25) have higher risk
            - Vehicle type and value matter
            - Urban areas show higher claims
            - Multiple factors interact
            """)
        
        st.markdown("---")
        st.plotly_chart(create_weight_pie_chart(), use_container_width=True)

# ============================================
# BATCH SCORING TAB (BONUS)
# ============================================

def batch_scoring_page():
    st.title("📁 Batch Risk Scoring")
    st.markdown("### Upload a CSV file to score multiple applicants at once")
    st.markdown("---")
    
    # Show required format
    st.subheader("Required CSV Format")
    sample_df = pd.DataFrame({
        'age_category': [1, 3, 5],
        'vehicle_value': [5, 7, 4],
        'vehicle_age': [2, 1, 3],
        'vehicle_body': ['SEDAN', 'SUV', 'HBACK'],
        'area': ['C', 'B', 'E'],
        'gender': ['M', 'F', 'M']
    })
    st.dataframe(sample_df, use_container_width=True)
    
    # File uploader
    uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Loaded {len(df)} applicants")
            
            if st.button("Calculate All Scores"):
                with st.spinner("Calculating scores..."):
                    results = []
                    
                    for idx, row in df.iterrows():
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
                                'applicant_id': idx + 1,
                                'age_risk': scores['age'],
                                'vehicle_risk': scores['vehicle'],
                                'location_risk': scores['location'],
                                'gender_risk': scores['gender'],
                                'final_risk': scores['final_weighted']
                            })
                    
                    results_df = pd.DataFrame(results)
                    
                    st.subheader("Results")
                    st.dataframe(results_df, use_container_width=True)
                    
                    # Download button
                    csv = results_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Results",
                        data=csv,
                        file_name="risk_scores.csv",
                        mime="text/csv"
                    )
                    
                    # Show statistics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Average Risk Score", f"{results_df['final_risk'].mean():.1f}")
                    
                    with col2:
                        st.metric("High Risk Count", 
                                 f"{len(results_df[results_df['final_risk'] >= 70])}")
                    
                    with col3:
                        st.metric("Low Risk Count", 
                                 f"{len(results_df[results_df['final_risk'] < 30])}")
                    
                    # Distribution chart
                    fig = px.histogram(results_df, x='final_risk', nbins=20,
                                      title="Risk Score Distribution",
                                      labels={'final_risk': 'Risk Score', 'count': 'Number of Applicants'})
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")

# ============================================
# RUN APP
# ============================================

if __name__ == "__main__":
    # Create tabs
    tab1, tab2 = st.tabs(["🎯 Single Applicant", "📁 Batch Scoring"])
    
    with tab1:
        main()
    
    with tab2:
        batch_scoring_page()