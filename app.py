
import streamlit as st
import pandas as pd
import pymssql
from sqlalchemy import create_engine, text


# --- Page Config ---
st.set_page_config(
    page_title="NovaGene Epigenetic Age Intelligence",
    page_icon="🧬",
    layout="wide"
)

# --- DB Connection ---
server = "bigdata-sql-123.database.windows.net"
database = "bigdata-db"
username = "sql-admin123"
password = "Amlingroupw@tch67-2"

connection_string = f"mssql+pymssql://{st.secrets["db_username"]}:{st.secrets["db_password"]}@{st.secrets["db_server"]}/{st.secrets["db_name"]}"
engine = create_engine(connection_string)

@st.cache_data(ttl=300)
def load_data():
    with engine.connect() as conn:
        epigenetic = pd.read_sql(text("SELECT * FROM epigenetic_results"), conn)
        grimage = pd.read_sql(text("SELECT * FROM grimage_results"), conn)
    merged = pd.merge(epigenetic, grimage, on="Sentrix_ID", suffixes=("", "_grim"))
    return epigenetic, grimage, merged

epigenetic, grimage, merged = load_data()

# --- Helper Functions ---
def get_status(aa, thresholds=(-3.6, 3.6)):
    if aa < thresholds[0]: return "🟢 EXCELLENT", "green"
    elif aa < 1: return "🟢 GOOD", "green"
    elif aa < thresholds[1]: return "🟡 MODERATE", "orange"
    else: return "🔴 CRITICAL", "red"

def get_overall_risk(horvath_aa, grim_aa):
    score = 0
    if abs(horvath_aa) > 3.6: score += 1
    if abs(grim_aa) > 3.6: score += 2
    if score >= 2: return "🔴 HIGH RISK", "red"
    elif score == 1: return "🟡 MODERATE RISK", "orange"
    else: return "🟢 LOW RISK", "green"

def get_actions(horvath_aa, grim_aa, lung_pf, smoking):
    actions = []
    if grim_aa > 3.6:
        actions.append("🫀 **Priority 1:** Metabolic health intervention — Mediterranean diet, 150 min/week aerobic exercise")
    if lung_pf and lung_pf < 400:
        actions.append("🫁 **Priority 2:** Pulmonary rehabilitation — Schedule spirometry, enroll in 8-12 week rehab program")
    if "current" in str(smoking).lower():
        actions.append("🚭 **Priority 3:** Smoking cessation program IMMEDIATELY")
    if horvath_aa > 3.6:
        actions.append("🧬 **Priority 4:** General aging intervention — Sleep optimization (7-9 hrs), stress management")
    if not actions:
        actions.append("✅ Keep up current healthy habits — all clocks within normal range")
    return actions

# --- Sidebar ---
st.sidebar.image("https://img.icons8.com/color/96/dna-helix.png", width=80)
st.sidebar.title("NovaGene")
st.sidebar.markdown("**Epigenetic Age Intelligence**")
page = st.sidebar.radio("Navigation", ["👤 Individual Report", "📊 Cohort Overview"])

# --- Individual Report Page ---
if page == "👤 Individual Report":
    st.title("🧬 Personalized Epigenetic Age Report")
    st.markdown("---")

    sample_options = merged["Sentrix_ID"].tolist()
    selected = st.selectbox("Select Sample", sample_options,
                            format_func=lambda x: f"{merged[merged.Sentrix_ID==x].Sample_Name.values[0]} ({x})")

    row = merged[merged["Sentrix_ID"] == selected].iloc[0]

    # Demographics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Chronological Age", f"{row.Age} yrs")
    col2.metric("Sex", row.Sex)
    col3.metric("Tissue", row.Tissue)
    col4.metric("Smoking Status", row.SmokingStatus)

    st.markdown("---")
    st.subheader("Epigenetic Clock Assessment")

    # Clock Cards
    c1, c2, c3 = st.columns(3)

    with c1:
        status, color = get_status(row.AgeAcceleration_Horvath)
        st.markdown(f"### 🧠 Horvath Clock")
        st.markdown(f"**General Aging**")
        st.metric("Biological Age", f"{row.Horvath:.1f} yrs", f"{row.AgeAcceleration_Horvath:+.1f} yrs")
        st.markdown(f"**Status: {status}**")
        st.markdown(f"Age Category: `{row.AgeCategory}`")

    with c2:
        status, color = get_status(row.AgeAccelGrim)
        st.markdown(f"### ❤️ GrimAge Clock")
        st.markdown(f"**Health & Mortality Risk**")
        st.metric("GrimAge", f"{row.GrimAge:.1f} yrs", f"{row.AgeAccelGrim:+.1f} yrs")
        st.markdown(f"**Status: {status}**")
        st.markdown(f"GrimAge Category: `{row.GrimAge_Category}`")

    with c3:
        status, color = get_status(row.AgeAccelHannum)
        st.markdown(f"### 🫁 Hannum Clock")
        st.markdown(f"**Alternative Aging Estimate**")
        st.metric("Hannum Age", f"{row.Hannum_DNAmAge:.1f} yrs", f"{row.AgeAccelHannum:+.1f} yrs")
        st.markdown(f"**Status: {status}**")

    st.markdown("---")

    # Smoking & Lung Metrics
    st.subheader("Smoking & Lung Metrics")
    m1, m2, m3 = st.columns(3)
    m1.metric("EpiSmoker Probability", f"{row.EpiSmoker_Prob:.2%}")
    m2.metric("DNAm Pack Years", f"{row.DNAm_PackYears:.1f}")
    m3.metric("Lung Peak Flow", f"{row.Lung_PeakFlow:.1f}")

    st.markdown("---")

    # Overall Risk
    overall, color = get_overall_risk(row.AgeAcceleration_Horvath, row.AgeAccelGrim)
    st.subheader(f"Overall Assessment: {overall}")

    # Action Plan
    st.subheader("📋 Personalized Action Plan")
    actions = get_actions(row.AgeAcceleration_Horvath, row.AgeAccelGrim,
                          row.Lung_PeakFlow, row.SmokingStatus)
    for action in actions:
        st.markdown(action)

# --- Cohort Overview Page ---
elif page == "📊 Cohort Overview":
    st.title("📊 Cohort Overview")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Samples", len(merged))
    col2.metric("Acceleration", len(merged[merged.AgeCategory == "Acceleration"]))
    col3.metric("Normal Aging", len(merged[merged.AgeCategory == "Normal Aging"]))
    col4.metric("Deceleration", len(merged[merged.AgeCategory == "Deceleration"]))

    st.markdown("---")
    st.subheader("Age Acceleration Distribution")

    chart_data = merged[["Sample_Name", "AgeAcceleration_Horvath", "AgeAccelGrim", "AgeAccelHannum"]].copy()
    chart_data.columns = ["Sample", "Horvath AA", "GrimAge AA", "Hannum AA"]
    chart_data = chart_data.set_index("Sample")
    st.bar_chart(chart_data)

    st.markdown("---")
    st.subheader("Risk Stratification")
    high = len(merged[(merged.AgeAccelGrim > 3.6)])
    moderate = len(merged[(merged.AgeAccelGrim > 0) & (merged.AgeAccelGrim <= 3.6)])
    low = len(merged[merged.AgeAccelGrim <= 0])

    r1, r2, r3 = st.columns(3)
    r1.metric("🔴 High Risk", f"{high} samples", f"{high/len(merged)*100:.0f}%")
    r2.metric("🟡 Moderate Risk", f"{moderate} samples", f"{moderate/len(merged)*100:.0f}%")
    r3.metric("🟢 Low Risk", f"{low} samples", f"{low/len(merged)*100:.0f}%")

    st.markdown("---")
    st.subheader("Full Data Table")
    display_cols = ["Sample_Name", "Age", "Sex", "SmokingStatus",
                    "Horvath", "AgeAcceleration_Horvath", "AgeCategory",
                    "GrimAge", "AgeAccelGrim", "GrimAge_Category"]
    st.dataframe(merged[display_cols].rename(columns={
        "Sample_Name": "Sample", "Age": "Age", "Sex": "Sex",
        "SmokingStatus": "Smoking", "AgeAcceleration_Horvath": "Horvath AA",
        "AgeAccelGrim": "GrimAge AA"
    }))
