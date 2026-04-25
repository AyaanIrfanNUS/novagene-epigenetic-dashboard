
import streamlit as st
import pandas as pd
import pymssql
from sqlalchemy import create_engine, text
import urllib.parse
import pickle
import os

# --- Page Config ---
st.set_page_config(
    page_title="NovaGene Epigenetic Age Intelligence",
    page_icon=None,
    layout="wide"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: white; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; }
    .status-green { background-color: #d4edda; color: #155724; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
    .status-yellow { background-color: #fff3cd; color: #856404; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
    .status-red { background-color: #f8d7da; color: #721c24; padding: 6px 12px; border-radius: 4px; font-weight: bold; }
    .section-header { border-bottom: 2px solid #dee2e6; padding-bottom: 8px; margin-bottom: 16px; }
    .disclaimer { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# --- DB Connection ---
encoded_password = urllib.parse.quote_plus(st.secrets["db_password"])
connection_string = f"mssql+pymssql://{st.secrets['db_username']}:{encoded_password}@{st.secrets['db_server']}/{st.secrets['db_name']}"
engine = create_engine(connection_string)

@st.cache_data(ttl=300)
def load_data():
    with engine.connect() as conn:
        epigenetic = pd.read_sql(text("SELECT * FROM epigenetic_results WHERE Sentrix_ID NOT LIKE 'SYNTHETIC%'"), conn)
        grimage    = pd.read_sql(text("SELECT * FROM grimage_results WHERE Sentrix_ID NOT LIKE 'SYNTHETIC%'"), conn)
    merged = pd.merge(epigenetic, grimage, on="Sentrix_ID", suffixes=("", "_grim"))
    return epigenetic, grimage, merged

epigenetic, grimage, merged = load_data()

# --- Helper Functions ---
def get_status(aa):
    if aa < -3.6:   return "Decelerated", "green"
    elif aa <= 3.6: return "Normal", "yellow"
    else:           return "Accelerated", "red"

def status_badge(label, color):
    return f'''<span class="status-{color}">{label}</span>'''

def get_overall_risk(horvath_aa, grim_aa):
    score = 0
    if abs(horvath_aa) > 3.6: score += 1
    if abs(grim_aa) > 3.6:    score += 2
    if score >= 2:   return "High Risk", "red"
    elif score == 1: return "Moderate Risk", "yellow"
    else:            return "Low Risk", "green"

def get_actions(horvath_aa, grim_aa, smoking):
    actions = []
    if grim_aa > 3.6:
        actions.append("Metabolic health intervention: Mediterranean diet, 150 min/week aerobic exercise")
    if "past" in str(smoking).lower() or "occasional" in str(smoking).lower():
        actions.append("Pulmonary rehabilitation: Schedule spirometry, consider 8-12 week rehab program")
    if "current" in str(smoking).lower():
        actions.append("Smoking cessation program — immediate priority")
    if horvath_aa > 3.6:
        actions.append("General aging intervention: Sleep optimization (7-9 hrs), stress management")
    if not actions:
        actions.append("Maintain current healthy habits — all clocks within normal range")
    return actions

# --- Sidebar ---
st.sidebar.markdown("## NovaGene")
st.sidebar.markdown("**Epigenetic Age Intelligence Platform**")
st.sidebar.markdown("---")
page = st.sidebar.radio("Navigation", [
    "Individual Report",
    "Cohort Overview",
    "Predictive Analysis"
])
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Real samples loaded:** {len(merged)}")

# =====================
# INDIVIDUAL REPORT
# =====================
if page == "Individual Report":
    st.markdown("## Individual Epigenetic Age Report")
    st.markdown("---")

    sample_options = merged["Sentrix_ID"].tolist()
    selected = st.selectbox(
        "Select Sample",
        sample_options,
        format_func=lambda x: f"{merged[merged.Sentrix_ID==x].Sample_Name.values[0]} — {x}"
    )

    row = merged[merged["Sentrix_ID"] == selected].iloc[0]

    # Demographics
    st.markdown("### Demographics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Chronological Age", f"{row.Age} yrs")
    c2.metric("Sex", row.Sex)
    c3.metric("Tissue", row.Tissue)
    c4.metric("Smoking Status", row.SmokingStatus)

    st.markdown("---")
    st.markdown("### Epigenetic Clock Assessment")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Horvath Clock — General Aging**")
        status, color = get_status(row.AgeAcceleration_Horvath)
        st.metric("Biological Age", f"{row.Horvath:.1f} yrs", f"{row.AgeAcceleration_Horvath:+.1f} yrs")
        st.markdown(status_badge(status, color), unsafe_allow_html=True)

    with col2:
        st.markdown("**GrimAge Clock — Health Risk**")
        status, color = get_status(row.AgeAccelGrim)
        st.metric("GrimAge", f"{row.GrimAge:.1f} yrs", f"{row.AgeAccelGrim:+.1f} yrs")
        st.markdown(status_badge(status, color), unsafe_allow_html=True)

    with col3:
        st.markdown("**Hannum Clock — Alternative Estimate**")
        status, color = get_status(row.AgeAccelHannum)
        st.metric("Hannum Age", f"{row.Hannum_DNAmAge:.1f} yrs", f"{row.AgeAccelHannum:+.1f} yrs")
        st.markdown(status_badge(status, color), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Smoking and Lung Metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("EpiSmoker Probability", f"{row.EpiSmoker_Prob:.2%}")
    m2.metric("DNAm Pack Years", f"{row.DNAm_PackYears:.1f}")
    m3.metric("Lung Peak Flow", f"{row.Lung_PeakFlow:.1f} L/min")

    st.markdown("---")
    overall, color = get_overall_risk(row.AgeAcceleration_Horvath, row.AgeAccelGrim)
    st.markdown(f"### Overall Assessment")
    st.markdown(status_badge(overall, color), unsafe_allow_html=True)

    st.markdown("### Personalized Action Plan")
    actions = get_actions(row.AgeAcceleration_Horvath, row.AgeAccelGrim, row.SmokingStatus)
    for i, action in enumerate(actions, 1):
        st.markdown(f"**{i}.** {action}")

# =====================
# COHORT OVERVIEW
# =====================
elif page == "Cohort Overview":
    st.markdown("## Cohort Overview")
    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Samples", len(merged))
    c2.metric("Acceleration", len(merged[merged.AgeCategory == "Acceleration"]))
    c3.metric("Normal Aging", len(merged[merged.AgeCategory == "Normal Aging"]))
    c4.metric("Deceleration", len(merged[merged.AgeCategory == "Deceleration"]))

    st.markdown("---")
    st.markdown("### Age Acceleration by Sample")
    chart_data = merged[["Sample_Name", "AgeAcceleration_Horvath", "AgeAccelGrim", "AgeAccelHannum"]].copy()
    chart_data.columns = ["Sample", "Horvath AA", "GrimAge AA", "Hannum AA"]
    chart_data = chart_data.set_index("Sample")
    st.bar_chart(chart_data)

    st.markdown("---")
    st.markdown("### Risk Stratification")
    high     = len(merged[merged.AgeAccelGrim > 3.6])
    moderate = len(merged[(merged.AgeAccelGrim > 0) & (merged.AgeAccelGrim <= 3.6)])
    low      = len(merged[merged.AgeAccelGrim <= 0])

    r1, r2, r3 = st.columns(3)
    r1.metric("High Risk", f"{high} samples")
    st.markdown(status_badge(f"{high/len(merged)*100:.0f}% of cohort", "red"), unsafe_allow_html=True)
    r2.metric("Moderate Risk", f"{moderate} samples")
    st.markdown(status_badge(f"{moderate/len(merged)*100:.0f}% of cohort", "yellow"), unsafe_allow_html=True)
    r3.metric("Low Risk", f"{low} samples")
    st.markdown(status_badge(f"{low/len(merged)*100:.0f}% of cohort", "green"), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Full Data Table")
    display_cols = ["Sample_Name", "Age", "Sex", "SmokingStatus",
                    "Horvath", "AgeAcceleration_Horvath", "AgeCategory",
                    "GrimAge", "AgeAccelGrim", "GrimAge_Category"]
    st.dataframe(merged[display_cols].rename(columns={
        "Sample_Name": "Sample", "SmokingStatus": "Smoking",
        "AgeAcceleration_Horvath": "Horvath AA", "AgeAccelGrim": "GrimAge AA"
    }), use_container_width=True)

# =====================
# PREDICTIVE ANALYSIS
# =====================
elif page == "Predictive Analysis":
    st.markdown("## Predictive Epigenetic Age Analysis")
    st.markdown("Enter your demographic details to receive a predicted epigenetic age profile.")
    st.markdown("---")

    model_path = os.path.join(os.path.dirname(__file__), "models", "model_bundle.pkl")
    with open(model_path, "rb") as f:
        bundle = pickle.load(f)

    # Model metrics
    with st.expander("Model Performance Summary"):
        m = bundle["metrics"]
        st.markdown(f"**Training samples:** {m['training_samples']} (24 real PGP UK + 500 synthetic)")
        st.markdown(f"**Algorithm:** Random Forest (scikit-learn) trained via PySpark pipeline")
        st.markdown(f"**Features:** Age, Sex, Smoking Status, Tissue Type")
        mc1, mc2, mc3 = st.columns(3)
        mc1.markdown("**Horvath Regressor**")
        mc1.metric("MAE", f"{m['horvath']['mae']} yrs")
        mc1.metric("R2 Score", str(m['horvath']['r2']))
        mc2.markdown("**GrimAge Regressor**")
        mc2.metric("MAE", f"{m['grimage']['mae']} yrs")
        mc2.metric("R2 Score", str(m['grimage']['r2']))
        mc3.markdown("**Age Category Classifier**")
        mc3.metric("Train Accuracy", f"{m['category']['accuracy']:.0%}")
        mc3.metric("CV Accuracy", f"{m['category']['cv_accuracy']:.0%}")
        st.markdown("""
        <div class="disclaimer">
        Note: Low R2 scores reflect the inherent limitation of predicting epigenetic age 
        from demographic features alone. Clinical-grade prediction requires DNA methylation 
        array data (485,512 CpG sites). This module demonstrates the ML pipeline architecture.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Enter Your Details")
    col1, col2 = st.columns(2)
    with col1:
        user_age     = st.number_input("Age", min_value=18, max_value=100, value=45)
        user_sex     = st.selectbox("Sex", bundle["sex_classes"])
    with col2:
        user_smoking = st.selectbox("Smoking Status", bundle["smoking_classes"])
        user_tissue  = st.selectbox("Tissue Type", bundle["tissue_classes"])

    if st.button("Generate Prediction"):
        X_input = [[
            float(user_age),
            bundle["le_sex"].transform([user_sex])[0],
            bundle["le_smoking"].transform([user_smoking])[0],
            bundle["le_tissue"].transform([user_tissue])[0]
        ]]

        horvath_aa   = bundle["rf_horvath"].predict(X_input)[0]
        grimage_aa   = bundle["rf_grimage"].predict(X_input)[0]
        category_idx = bundle["rf_category"].predict(X_input)[0]
        age_category = bundle["le_category"].inverse_transform([int(category_idx)])[0]
        horvath_age  = user_age + horvath_aa
        grimage_age  = user_age + grimage_aa

        st.markdown("---")
        st.markdown("### Predicted Results")

        c1, c2, c3 = st.columns(3)
        c1.metric("Predicted Horvath Age", f"{horvath_age:.1f} yrs", f"{horvath_aa:+.1f} yrs")
        c2.metric("Predicted GrimAge", f"{grimage_age:.1f} yrs", f"{grimage_aa:+.1f} yrs")
        c3.metric("Predicted Age Category", age_category)

        st.markdown("---")
        st.markdown("### Clock Status")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Horvath Clock — General Aging**")
            h_status, h_color = get_status(horvath_aa)
            st.markdown(status_badge(h_status, h_color), unsafe_allow_html=True)
            st.markdown(f"Age Acceleration: `{horvath_aa:+.1f} years`")
        with col2:
            st.markdown("**GrimAge Clock — Health and Mortality Risk**")
            g_status, g_color = get_status(grimage_aa)
            st.markdown(status_badge(g_status, g_color), unsafe_allow_html=True)
            st.markdown(f"Age Acceleration: `{grimage_aa:+.1f} years`")

        st.markdown("---")
        overall, color = get_overall_risk(horvath_aa, grimage_aa)
        st.markdown("### Overall Risk Assessment")
        st.markdown(status_badge(overall, color), unsafe_allow_html=True)

        st.markdown("### Recommended Actions")
        actions = get_actions(horvath_aa, grimage_aa, user_smoking)
        for i, action in enumerate(actions, 1):
            st.markdown(f"**{i}.** {action}")
