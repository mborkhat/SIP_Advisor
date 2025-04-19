import streamlit as st
import pandas as pd
import requests
from fuzzywuzzy import process
from datetime import datetime, timedelta
from transformers import pipeline

# Load Hugging Face's NLP model to extract financial details (amount, category, etc.)
nlp_model = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

# --- Function to extract entities from user query ---
def extract_entities(query):
    entities = nlp_model(query)
    return entities

# --- Function to fetch fund data ---
@st.cache_data
def fetch_fund_data():
    url = "https://api.mfapi.in/mf"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error fetching fund data: {e}")
        return pd.DataFrame([])

# --- Function to fetch Nifty data ---
def fetch_nifty_data():
    try:
        url = "https://query1.finance.yahoo.com/v7/finance/download/^NSEI?period1=0&period2=9999999999&interval=1d&events=history"
        df = pd.read_csv(url)
        df = df[['Date', 'Close']].rename(columns={"Close": "Nifty_Close"})
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        return df
    except Exception as e:
        st.error(f"Error fetching Nifty data: {e}")
        return pd.DataFrame()

# --- Main Streamlit App ---
st.title("SIP Advisor - AI Powered (Free)")

# User input for SIP details
st.subheader("Enter Your Investment Criteria:")
user_query = st.text_input("E.g., I want to invest ₹5000 monthly in Large Cap funds for 6 months expecting 12% return")

# Extract entities from user input using NLP
entities = extract_entities(user_query)

# Show extracted entities for debugging (optional)
st.write(entities)

# Process extracted entities
amount = None
category = None
duration = None
expected_return = None

for entity in entities:
    if entity['entity'] == 'MONEY':
        amount = entity['word']
    if entity['entity'] == 'ORG' and 'Large Cap' in entity['word']:
        category = "Large Cap"
    if entity['entity'] == 'DATE':
        duration = entity['word']
    if entity['entity'] == 'PERCENT':
        expected_return = entity['word']

# Assuming the amount is in ₹ and parsing duration as months
if amount:
    amount = int(amount.strip('₹').replace(',', ''))  # Remove ₹ and commas
if expected_return:
    expected_return = float(expected_return.strip('%'))

# Default values in case no entities were found
if not amount:
    amount = 5000  # Default ₹5000 if not specified
if not duration:
    duration = 6  # Default 6 months if not specified
if not expected_return:
    expected_return = 12  # Default 12% return if not specified

st.write(f"Selected Investment Criteria: ₹{amount} monthly, {category}, {duration} months, {expected_return}% return")

# Fetch fund data and Nifty data
funds = fetch_fund_data()
nifty_df = fetch_nifty_data()

# Filter funds based on user category (e.g., Large Cap)
if not funds.empty:
    filtered_funds = funds[funds['category'].str.contains(category, case=False, na=False)]

    if not filtered_funds.empty:
        # Simulate SIP return for selected funds
        selected_schemes = []

        for index, scheme in filtered_funds.iterrows():
            scheme_code = scheme['schemeCode']
            scheme_name = scheme['schemeName']
            
            # Fetch NAV data for scheme
            detail_url = f"https://api.mfapi.in/mf/{scheme_code}"
            try:
                detail = requests.get(detail_url).json()
                if 'data' in detail and len(detail['data']) >= 250:
                    navs = pd.DataFrame(detail['data'])
                    navs['date'] = pd.to_datetime(navs['date'])
                    navs['nav'] = navs['nav'].astype(float)
                    navs = navs.sort_values('date')

                    # Get NAV for the last 6 months
                    six_months_ago = navs['date'].max() - pd.DateOffset(months=6)
                    navs_filtered = navs[navs['date'] >= six_months_ago]
                    six_month_return = (navs_filtered.iloc[-1]['nav'] - navs_filtered.iloc[0]['nav']) / navs_filtered.iloc[0]['nav'] * 100

                    if six_month_return >= expected_return:
                        selected_schemes.append({
                            "scheme_name": scheme_name,
                            "six_month_return": six_month_return,
                            "nav_trend": navs_filtered
                        })

            except Exception as e:
                st.error(f"Error fetching data for {scheme_name}: {e}")

        # Sort schemes by return and display top 3
        selected_schemes = sorted(selected_schemes, key=lambda x: x['six_month_return'], reverse=True)[:3]

        if selected_schemes:
            st.subheader("Top 3 SIP Schemes Based on Your Criteria:")
            for scheme in selected_schemes:
                st.write(f"Scheme: {scheme['scheme_name']}")
                st.write(f"6-Month Return: {round(scheme['six_month_return'], 2)}%")
                st.write(f"View NAV Trend: {scheme['nav_trend']}")
        else:
            st.warning("No schemes found that match your criteria.")
    else:
        st.warning("No Large Cap funds found.")
else:
    st.warning("Live fund list could not be loaded. Try again later.")
