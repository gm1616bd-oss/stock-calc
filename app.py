import streamlit as st
import yfinance as yf
import pandas as pd
import extra_streamlit_components as stx
import datetime

# ==========================================
# 1. 포트폴리오 정의
# ==========================================
fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.05, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.05, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.03, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.02, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.05, "country": "US"},
]

invest_portfolio = [
    {"name": "TSM",        "ticker": "TSM",    "ratio": 0.22, "country": "US"},
    {"name": "NVDA",       "ticker": "NVDA",   "ratio": 0.08, "country": "US"},
    {"name": "TSLA",       "ticker": "TSLA",   "ratio": 0.06, "country": "US"},
    {"name": "MSFT",       "ticker": "MSFT",   "ratio": 0.08, "country": "US"},
    {"name": "AAPL",       "ticker": "AAPL",   "ratio": 0.06, "country": "US"},
    {"name": "GOOGL",      "ticker": "GOOGL",  "ratio": 0.14, "country": "US"},
    {"name": "AMD",        "ticker": "AMD",    "ratio": 0.07, "country": "US"},
    {"name": "AMZN",       "ticker": "AMZN",   "ratio": 0.07, "country": "US"},
    {"name": "PLTR",       "ticker": "PLTR",   "ratio": 0.02, "country": "US"},
    {"name": "SK하이닉스", "ticker": "000660.KS", "ratio": 0.15, "country": "KR"},
    {"name": "현대차",     "ticker": "005380.KS", "ratio": 0.05, "country": "KR"},
]

all_stocks = fixed_portfolio + invest_portfolio
all_names = [item['name'].split()[0] for item in all_stocks] 

# ==========================================
# 2. 앱 화면 구성 & 자동 저장(쿠키) 설정
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="💾", layout="wide")
st.title("💾 스마트 리밸런싱 (자동 저장판)")

# 쿠키 매니저 실행 (중복 에러 방지를 위해 key 명시)
cookie_manager = stx.CookieManager(key="cookie_manager_main")

# 아이패드에 저장된 이전 기록 읽어오기
saved_cash = cookie_manager.get("my_cash")
saved_holdings = cookie_manager.get("my_holdings")

# 저장된 값이 없으면 기본값 세팅
try:
    default_cash = int(saved_cash) if saved_cash is not None else 10000000
except:
    default_
