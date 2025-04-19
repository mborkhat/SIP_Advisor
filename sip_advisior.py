import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from fuzzywuzzy import process
from transformers import pipeline
from datetime import datetime, timedelta

st.set_page_config(page_title="SIP Advisor", layout="wide")
st.title("\U0001F4C8 SIP Advisor - AI Powered (Free)")

st.markdown("""
This app helps you:
- Understand SIPs and how they work
- Search SIP schemes by AMC or Fund Category (Large Cap, ELSS, etc.)
- Get Buy/Hold/Sell advice using AI
- Compare fund performance with Nifty50 and benchmark returns
- View historical NAV charts
- Calculate returns
- Chat with an AI to learn about SIPs

Data source: Free Mutual Fund APIs (MFAPI.in)
""")

st.subheader("\U0001F916 SIP Assistant (FAQs)")
faq_input = st.text_input("Ask your SIP-related question", "What is SIP?")

faq_answers = {
    "what is sip": "A SIP or Systematic Investment Plan is a way to invest in mutual funds regularly.",
    "benefits of sip": "SIPs help inculcate financial discipline, average out costs via rupee cost averaging, and harness power of compounding.",
    "types of sip": "There are types like Regular SIP, Top-up SIP, Flexible SIP, and Perpetual SIP.",
    "how sip works": "You invest a fixed amount at regular intervals (monthly/weekly), which gets invested in mutual fund units.",
    "what is top-up sip": "Top-up SIP allows you to increase your SIP amount automatically at regular intervals.",
    "investment planning help": "Start by setting a goal, choosing right fund category, and staying consistent with SIPs.",
    "how to choose sip": "Consider your goals, risk tolerance, past performance, and fund house reputation before choosing a SIP.",
    "difference between sip and lump sum": "SIP invests regularly over time, while lump sum invests all at once. SIP reduces timing risk.",
    "can i stop sip anytime": "Yes, SIPs are flexible and can be paused or stopped anytime without penalty.",
    "is sip safe": "SIPs invest in mutual funds, which have market risks, but SIP reduces volatility risk via cost averaging.",
    "how much should i invest": "You should invest as per your financial goals and monthly saving capability.",
    "which sip is best": "There is no one-size-fits-all. Best SIP depends on your investment horizon and risk appetite.",
    "is sip tax free": "Returns from SIPs in equity funds are taxed as per capital gains tax rules. ELSS offers tax benefits under 80C."
}

matched = process.extractOne(faq_input.lower(), faq_answers.keys())
if matched and matched[1] > 70:
    st.success(faq_answers[matched[0]])
else:
    st.info("I'm here to help with SIPs! Try asking: 'What is SIP?', 'Benefits of SIP', or 'Types of SIPs'")

st.subheader("\U0001F4CA SIP Return Calculator")
sip_amt = st.number_input("Monthly SIP Amount (₹)", value=5000, step=500)
sip_years = st.slider("Investment Duration (years)", 1, 30, 1)
expected_return = st.slider("Expected Annual Return (%)", 1, 25, 12)

if st.button("Calculate SIP Return"):
    n_months = sip_years * 12
    monthly_rate = expected_return / 100 / 12
    future_value = sip_amt * (((1 + monthly_rate) ** n_months - 1) * (1 + monthly_rate)) / monthly_rate
    invested = sip_amt * n_months
    gain = future_value - invested

    st.success(f"Total Invested: ₹{invested:,.0f}")
    st.success(f"Expected Return: ₹{gain:,.0f}")
    st.success(f"Maturity Value: ₹{future_value:,.0f}")

    st.markdown("### \U0001F4A1 Top 3 Suggested SIP Schemes Based on Your Input")

    try:
        funds = pd.read_json("https://api.mfapi.in/mf")
        filtered_funds = funds[funds["schemeName"].str.contains("(large cap|flexi|elss)", case=False, regex=True)]

        # Fetch NAV data and calculate 3-year return
        top_returns = []
        for i, row in filtered_funds.iterrows():
            try:
                nav_data = requests.get(f"https://api.mfapi.in/mf/{row['schemeCode']}").json()
                data = nav_data['data']
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'], dayfirst=True)
                df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
                df = df.sort_values('date')

                three_years_ago = datetime.now() - timedelta(days=3*365)
                df = df[df['date'] >= three_years_ago]

                if len(df) < 2:
                    continue

                start_nav = df.iloc[0]['nav']
                end_nav = df.iloc[-1]['nav']
                return_3y = ((end_nav - start_nav) / start_nav) * 100
                top_returns.append((row['schemeCode'], row['schemeName'], return_3y))
            except:
                continue

        if top_returns:
            top_returns = sorted(top_returns, key=lambda x: x[2], reverse=True)[:3]
            df_top = pd.DataFrame(top_returns, columns=["schemeCode", "schemeName", "3Y Return (%)"])
            st.dataframe(df_top)

            st.markdown("---")
            st.markdown("### \U0001F4A1 Based on your inputs: ₹{} monthly for {} years expecting {}% return, here are top 3 schemes (last 3Y performance):".format(sip_amt, sip_years, expected_return))
            st.dataframe(df_top[["schemeName", "3Y Return (%)"]])
        else:
            st.warning("No top schemes found at the moment. Please try again later.")

    except Exception as e:
        st.error("Smart suggestion failed to load. Reason: {}".format(e))
