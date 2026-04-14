import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

# ==========================================
# 🔑 구글 시트 연결 설정 (사용자님 링크로 변경하세요!)
# ==========================================
SHEET_CSV_URL = "여기에_시트_CSV_링크를_넣어주세요"
WEB_APP_URL = "여기에_웹앱_URL을_넣어주세요"

# ==========================================
# 1. 포트폴리오 정의 (총 15종목)
# ==========================================
fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.04, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.04, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.025, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.015, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.04, "country": "US"},
]

invest_portfolio = [
    {"name": "TSM",        "ticker": "TSM",    "ratio": 0.25, "country": "US"},
    {"name": "NVDA",       "ticker": "NVDA",   "ratio": 0.08, "country": "US"},
    {"name": "TSLA",       "ticker": "TSLA",   "ratio": 0.06, "country": "US"},
    {"name": "MSFT",       "ticker": "MSFT",   "ratio": 0.065, "country": "US"},
    {"name": "AAPL",       "ticker": "AAPL",   "ratio": 0.065, "country": "US"},
    {"name": "GOOGL",      "ticker": "GOOGL",  "ratio": 0.10, "country": "US"},
    {"name": "AMD",        "ticker": "AMD",    "ratio": 0.065, "country": "US"},
    {"name": "AMZN",       "ticker": "AMZN",   "ratio": 0.065, "country": "US"},
    {"name": "SK하이닉스", "ticker": "000660.KS", "ratio": 0.20, "country": "KR"},
    {"name": "현대차",     "ticker": "005380.KS", "ratio": 0.05, "country": "KR"},
]

all_stocks = fixed_portfolio + invest_portfolio
all_names = [item['name'].split()[0] for item in all_stocks] 

# ==========================================
# 2. 앱 화면 구성 & 상단 구글시트 차트
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="📈", layout="wide")
st.title("📈 내 자산 성장 대시보드 (63:16:21)")

try:
    if "export?
