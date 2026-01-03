import os
import datetime
import json
import sys
import re
import math
import requests

# === 系統配置 ===
print("=== 啟動 Jason TV v11.6 (Design & Logic Integration) ===")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
YT_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = "UC_ObC9O0ZQ2FhW6u9_iFlZA"

DEBUG_LOGS = []
def log(msg):
    print(msg)
    DEBUG_LOGS.append(msg)

def get_market_data():
    log("Step 1: 連線 Yahoo Finance...")
    try:
        import yfinance as yf
        # 抓取 8 大數據
        tickers = ["2330.TW", "^TWII", "GC=F", "SI=F", "USDTWD=X", "JPYTWD=X", "BTC-USD", "ETH-USD", "^TNX", "^GSPC"]
        data = yf.Tickers(" ".join(tickers))
        
        def get_current_price(symbol):
            try:
                df = data.tickers[symbol].history(period="5d")
                if df.empty: return 0.0
                val = float(df['Close'].iloc[-1])
                return 0.0 if math.isnan(val) else val
            except: return 0.0

        def get_trend_data(symbol):
            try:
                hist = data.tickers[symbol].history(period="1y", interval="1mo")
                if hist.empty: return [0.0]*12
                prices = hist['Close'].dropna().tolist()
                if len(prices) < 2: return [0.0]*12
                start_price = prices[0]
                if start_price == 0: return [0.0]*12
                trend = [round(float((p - start_price) / start_price * 100), 2) for p in prices]
                result = trend[-12:]
                while len(
