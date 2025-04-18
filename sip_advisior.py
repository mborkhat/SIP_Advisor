import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from transformers import pipeline
import math

# Load model for recommendations and chatbot
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

st.set_page_config(page_title="SIP Advisor", layout="wide")
st.title("\U0001F4B8 SIP (Systematic Investment Plan) Advisor - India")

st.markdown("""
Search mutual fund schemes by **AMC or Category**, calculate returns, get AI recommendations, and learn via an interactive chatbot.

*Powered by open data & Hugging Face models – No cost, 100% free.*
""")

# --- SIP RETURN CALCULATOR ---
st.header("\U0001F4C9 SIP Return Calculator")
sip_amount = st.number_input("Monthly SIP Amount (₹)", value=1000, min_value=100)
duration_years = st.slider("Investment Duration (years)", 1, 30, 5)
estimated_rate = st.slider("Expected Annual Return (%)", 1, 20, 12)

months = duration_years * 12
monthly_rate = estimated_rate / 12 / 100

final_value = sip_amount * (((1 + monthly_rate) ** months - 1) * (1 + monthly_rate)) / monthly_rate
investment = sip_amount * months
gain = final_value - investment

st.write(f"**Total Investment:** ₹{investment:,.0f}")
st.write(f"**Estimated Returns:** ₹{gain:,.0f}")
st.write(f"**Final Value:** ₹{final_value:,.0f}")

# Chart
fig = go.Figure()
fig.add_trace(go.Bar(name='Invested Amount', x=['SIP'], y=[investment]))
fig.add_trace(go.Bar(name='Estimated Gain', x=['SIP'], y=[gain]))
fig.update_layout(barmode='stack', title="SIP Investment vs Returns")
st.plotly_chart(fig, use_container_width=True)

# --- SCHEME SEARCH UI ---
st.header("\U0001F50D Search Mutual Funds")
search_type = st.radio("Search by:", ["AMC", "Category"], horizontal=True)
query = st.text_input(f"Enter {search_type} name:")

@st.cache_data
def fetch_schemes():
    url = "https://api.mfapi.in/mf"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

schemes = fetch_schemes()

filtered = []
if query:
    query_lower = query.lower()
    for s in schemes:
        name = s.get('schemeName', '').lower()
        if query_lower in name:
            filtered.append(s)

if filtered:
    selected = st.selectbox("Matching Schemes:", filtered, format_func=lambda x: x['schemeName'])

    # Fetch and display NAV history
    @st.cache_data
    def get_nav(scheme_code):
        url = f"https://api.mfapi.in/mf/{scheme_code}"
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        return {}

    data = get_nav(selected['schemeCode'])
    if data:
        navs = data.get('data', [])[:60][::-1]  # Last 60 entries
        df = pd.DataFrame(navs)
        df['date'] = pd.to_datetime(df['date'])
        df['nav'] = pd.to_numeric(df['nav'], errors='coerce')

        st.subheader("Recent NAV Trend")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df['date'], y=df['nav'], mode='lines+markers', name='NAV'))
        fig2.update_layout(title=f"{selected['schemeName']} - NAV Trend", xaxis_title='Date', yaxis_title='NAV')
        st.plotly_chart(fig2, use_container_width=True)

        # Recommendation
        prompt = f"Scheme: {selected['schemeName']}. Recent NAV trend shown. Should I buy, hold or sell?"
        result = classifier(prompt, ["Buy", "Hold", "Sell"])
        st.write(f"\U0001F4AC **AI Recommendation:** {result['labels'][0]}")
else:
    if query:
        st.warning("No matching schemes found.")

# --- Chatbot ---
st.header("\U0001F916 SIP Chatbot")
faq_responses = {
    "what is sip": "SIP stands for Systematic Investment Plan. It allows you to invest a fixed amount regularly in mutual funds.",
    "sip benefits": "SIPs offer rupee cost averaging, disciplined investing, and compounding over time.",
    "types of sip": "There are Flexi SIPs, Top-up SIPs, Perpetual SIPs and Trigger-based SIPs.",
    "how sip helps": "SIP helps by automating your investments, reducing timing risk, and building wealth long-term.",
    "calculate sip": "Use the SIP return calculator above by entering your monthly investment, duration and expected return rate."
}

user_query = st.text_input("Ask about SIPs (e.g., 'What is SIP?', 'Types of SIPs')")

if user_query:
    match = max(faq_responses.keys(), key=lambda k: classifier(user_query, [k])["scores"][0])
    st.write(f"\U0001F4AC **Chatbot:** {faq_responses[match]}")
