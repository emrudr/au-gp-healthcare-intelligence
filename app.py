import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(
    page_title="AU GP Healthcare Intelligence",
    page_icon="🩺",
    layout="wide"
)

@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

@st.cache_data(ttl=60)
def load_gp_data():
    client = get_supabase()
    all_data = []
    chunk = 1000
    start = 0
    while True:
        res = client.table("australian_gps").select("*").range(start, start + chunk - 1).execute()
        rows = res.data
        if not rows:
            break
        all_data.extend(rows)
        if len(rows) < chunk:
            break
        start += chunk
    return pd.DataFrame(all_data)

st.title("🩺 Australian General Practice Intelligence Portal")
st.caption("Automated Healthcare Directory & Practitioner Search System")

try:
    df = load_gp_data()
except Exception as e:
    st.error(f"Database error: {e}")
    st.stop()

if df.empty:
    st.info("Connected to database. Practitioner directory will populate once data is uploaded to Supabase.")
    st.stop()

st.sidebar.header("Filter Practitioners")
states = ["All"] + sorted(df["state"].dropna().unique().tolist())
selected_state = st.sidebar.selectbox("State / Territory", states)

if selected_state != "All":
    suburbs = ["All"] + sorted(df[df["state"] == selected_state]["suburb"].dropna().unique().tolist())
else:
    suburbs = ["All"] + sorted(df["suburb"].dropna().unique().tolist())
selected_suburb = st.sidebar.selectbox("Suburb", suburbs)

genders = ["All"] + sorted(df["gender"].dropna().unique().tolist())
selected_gender = st.sidebar.selectbox("Gender", genders)

search_q = st.sidebar.text_input("Search Doctor, Clinic, or Qualification", "")

filtered = df.copy()
if selected_state != "All":
    filtered = filtered[filtered["state"] == selected_state]
if selected_suburb != "All":
    filtered = filtered[filtered["suburb"] == selected_suburb]
if selected_gender != "All":
    filtered = filtered[filtered["gender"] == selected_gender]
if search_q:
    q = search_q.lower()
    filtered = filtered[
        filtered["doctor_name"].fillna("").str.lower().str.contains(q)
        | filtered["practice_name"].fillna("").str.lower().str.contains(q)
        | filtered["qualification_codes"].fillna("").str.lower().str.contains(q)
    ]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Practitioners", len(filtered))
col2.metric("Clinics", filtered["practice_name"].nunique())
col3.metric("Suburbs", filtered["suburb"].nunique())
col4.metric("States", filtered["state"].nunique())

st.divider()

cols = [
    "doctor_name", "role", "gender", "qualification_codes",
    "practice_name", "phone_number", "address", "suburb", "state", "postcode"
]
active_cols = [c for c in cols if c in filtered.columns]
st.dataframe(filtered[active_cols], use_container_width=True)

csv_export = filtered[active_cols].to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Download Filtered CSV",
    data=csv_export,
    file_name="australian_gps_filtered.csv",
    mime="text/csv"
)
