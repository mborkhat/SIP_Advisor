import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from fuzzywuzzy import process
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

# --- Static FAQ Chatbot ---
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

# --- SIP Calculator ---
st.subheader("\U0001F4CA SIP Return Calculator")
sip_amt = st.number_input("Monthly SIP Amount (₹)", value=1000, step=500)
sip_years = st.slider("Investment Duration (years)", 1, 30, 10)
expected_return = st.slider("Expected Annual Return (%)", 1, 20, 12)

if st.button("Calculate SIP Return"):
    n_months = sip_years * 12
    monthly_rate = expected_return / 100 / 12
    future_value = sip_amt * (((1 + monthly_rate) ** n_months - 1) * (1 + monthly_rate)) / monthly_rate
    invested = sip_amt * n_months
    gain = future_value - invested

    st.success(f"Total Invested: ₹{invested:,.0f}")
    st.success(f"Expected Return: ₹{gain:,.0f}")
    st.success(f"Maturity Value: ₹{future_value:,.0f}")

# --- SIP Search ---
st.subheader("\U0001F50D Search SIP Mutual Funds")
st.markdown("Enter AMC Name, Fund Category (e.g., ELSS, Large Cap), or Scheme Name")
user_query = st.text_input("Search", "Large Cap")

@st.cache_data

def fetch_fund_data():
    url = "https://api.mfapi.in/mf"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame([])

def fetch_nifty_data():
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/download/^NSEI?period1=0&period2=9999999999&interval=1d&events=history"
        df = pd.read_csv(url)
        df = df[['Date', 'Close']].rename(columns={"Close": "Nifty_Close"})
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        return df
    except:
        return pd.DataFrame()

funds = fetch_fund_data()
nifty_df = fetch_nifty_data()

if not funds.empty:
    filtered = funds[funds.apply(lambda row: user_query.lower() in row['schemeName'].lower(), axis=1)]
    if not filtered.empty:
        selected_scheme = filtered.iloc[0]
        scheme_code = selected_scheme['schemeCode']
        scheme_name = selected_scheme['schemeName']

        st.subheader(f"Selected Scheme: {scheme_name}")

        detail_url = f"https://api.mfapi.in/mf/{scheme_code}"
        try:
            detail = requests.get(detail_url).json()
            if 'data' in detail and len(detail['data']) >= 250:
                navs = pd.DataFrame(detail['data'])
                navs['date'] = pd.to_datetime(navs['date'])
                navs['nav'] = navs['nav'].astype(float)
                navs = navs.sort_values('date')

                one_year_ago = navs['date'].max() - pd.DateOffset(years=1)
                navs_filtered = navs[navs['date'] >= one_year_ago]
                one_year_return = (navs_filtered.iloc[-1]['nav'] - navs_filtered.iloc[0]['nav']) / navs_filtered.iloc[0]['nav'] * 100

                if one_year_return > 14:
                    signal = "Buy"
                elif one_year_return > 10:
                    signal = "Hold"
                else:
                    signal = "Sell"

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=navs['date'], y=navs['nav'], mode='lines', name=scheme_name))

                if not nifty_df.empty:
                    merged = pd.merge(navs, nifty_df, left_on=navs['date'].dt.strftime('%Y-%m-%d'), right_on='Date', how='left')
                    fig.add_trace(go.Scatter(x=merged['date'], y=merged['Nifty_Close'], mode='lines', name='Nifty 50'))

                fig.update_layout(
                    title=f"NAV vs Nifty - {scheme_name}",
                    xaxis_title="Date",
                    yaxis_title="Value",
                    xaxis_rangeslider_visible=True
                )
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("Buy/Hold/Sell Signal")
                st.write(f"1-Year Return: {round(one_year_return, 2)}%")
                st.write(f"Recommendation: {signal}")
            else:
                st.warning("Not enough data to calculate signals.")
        except Exception as e:
            st.error(f"Error fetching data for {scheme_name}: {e}")
    else:
        st.warning("No schemes found matching your search.")
else:
    st.warning("Live fund list could not be loaded. Try again later.")
