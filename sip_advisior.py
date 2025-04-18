import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
from fuzzywuzzy import process
torch_dtype = "float16"

st.set_page_config(page_title="SIP Advisor", layout="wide")
st.title("📈 SIP Advisor - AI Powered (Free)")

st.markdown("""
This app helps you:
- Understand SIPs and how they work
- Search SIP schemes by AMC or Fund Category (Large Cap, ELSS, etc.)
- Get Buy/Hold/Sell advice using AI
- Calculate returns
- Chat with an AI to learn about SIPs

Data source: Free Mutual Fund APIs
""")

# --- Dynamic Chatbot ---
st.subheader("🤖 Ask anything about SIPs")
chat_input = st.text_input("Ask your SIP-related question here", "What is SIP?")

@st.cache_resource
def load_chat_model():
    model_name = "microsoft/DialoGPT-medium"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    return tokenizer, model

if chat_input:
    tokenizer, model = load_chat_model()
    new_input_ids = tokenizer.encode(chat_input + tokenizer.eos_token, return_tensors='pt')

    chat_history_ids = model.generate(
        new_input_ids,
        max_length=200,
        pad_token_id=tokenizer.eos_token_id,
        do_sample=True,
        top_k=50,
        top_p=0.95,
        temperature=0.7
    )

    reply = tokenizer.decode(chat_history_ids[:, new_input_ids.shape[-1]:][0], skip_special_tokens=True)
    st.success(reply)

# --- SIP Calculator ---
st.subheader("📊 SIP Return Calculator")
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

# --- SIP Search & Comparison ---
st.subheader("🔍 Search SIP Mutual Funds (Demo)")
user_query = st.text_input("Search by AMC / Category / Fund Name", "Large Cap")

@st.cache_data
def fetch_demo_funds():
    return pd.DataFrame([
        {"Scheme": "Axis Bluechip Fund", "AMC": "Axis", "Category": "Large Cap", "1Y Return": 17.2, "3Y Return": 14.8},
        {"Scheme": "Mirae Asset ELSS", "AMC": "Mirae", "Category": "ELSS", "1Y Return": 19.5, "3Y Return": 15.3},
        {"Scheme": "HDFC Top 100", "AMC": "HDFC", "Category": "Large Cap", "1Y Return": 14.7, "3Y Return": 12.6},
        {"Scheme": "Quant Tax Plan", "AMC": "Quant", "Category": "ELSS", "1Y Return": 28.4, "3Y Return": 23.2},
    ])

funds = fetch_demo_funds()
filtered = funds[funds.apply(lambda row: user_query.lower() in row['Scheme'].lower() or user_query.lower() in row['AMC'].lower() or user_query.lower() in row['Category'].lower(), axis=1)]

if not filtered.empty:
    st.dataframe(filtered)
    st.subheader("📈 Compare NAV Performance (Mock)")
    fig = go.Figure()
    for _, row in filtered.iterrows():
        months = pd.date_range(end=pd.Timestamp.today(), periods=6, freq='M')
        navs = [100 * (1 + row['1Y Return'] / 100 / 12) ** i for i in range(6)]
        fig.add_trace(go.Scatter(x=months, y=navs, mode='lines+markers', name=row['Scheme']))
    fig.update_layout(title="NAV Trend (Simulated)", xaxis_title="Month", yaxis_title="NAV (₹)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No match found. Try with different keyword like 'ELSS' or 'Axis'")
