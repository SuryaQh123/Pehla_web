import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- Scraping ---

def get_indian_stocks_under_200():
    url = "https://www.tickertape.in/stocks/collections/stocks-under-200"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    tickers = []

    for tag in soup.find_all("a", href=True):
        if "/stocks/" in tag["href"] and "-share-price" in tag["href"]:
            ticker = tag["href"].split("/")[-1].split("-")[0].upper()
            if len(ticker) <= 6:
                tickers.append(ticker + ".NS")  # NSE format
    return list(set(tickers))

def get_us_penny_stocks():
    url = "https://toppennystocks.org/stocks-under-3.php"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("table tr")
    tickers = []

    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            ticker = cols[0].text.strip()
            if ticker.isalpha():
                tickers.append(ticker)
    return list(set(tickers))

# --- Streamlit App ---

st.set_page_config("📊 Cheap Growth Stocks", layout="wide")
st.title("📈 Cheap Stocks Finder (₹100–₹200 / <$3) - India + Global")

@st.cache_data
def load_tickers():
    india = get_indian_stocks_under_200()
    us = get_us_penny_stocks()
    return india + us

tickers = load_tickers()
st.success(f"✅ Fetched {len(tickers)} tickers")

@st.cache_data
def fetch_prices(tickers):
    data = yf.download(tickers, period="1d", group_by="ticker", threads=True, progress=False)
    result = []
    for t in tickers:
        try:
            price = data[t]["Close"].iloc[-1]
            result.append((t, price))
        except:
            continue
    return pd.DataFrame(result, columns=["Ticker", "Price"])

def to_inr(price, ticker):
    return price * 83 if not ticker.endswith(".NS") else price

df = fetch_prices(tickers)
df["Price_INR"] = df.apply(lambda r: to_inr(r.Price, r.Ticker), axis=1)
df = df[(df.Price_INR >= 100) & (df.Price_INR <= 200)]

st.subheader("🔍 Filtered Stocks in ₹100–₹200 Range")
st.dataframe(df)

# --- Growth Scoring ---

def growth_score(ticker):
    try:
        info = yf.Ticker(ticker).info
        score = (
            -(info.get("trailingPE", 999) or 999) * 0.3 +
            (info.get("returnOnEquity", 0) or 0) * 100 * 0.4 +
            (info.get("earningsQuarterlyGrowth", 0) or 0) * 0.3
        )
        return round(score, 2)
    except:
        return 0

st.info("⚙️ Scoring stocks based on valuation and growth...")
df["Score"] = df["Ticker"].apply(growth_score)

top5 = df.sort_values("Score", ascending=False).head(5)
st.subheader("🏆 Top 5 High-Growth Potential Stocks")
st.table(top5[["Ticker", "Price", "Price_INR", "Score"]])
