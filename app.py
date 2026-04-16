import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone

# --- 앱 메모리(Session State) 초기화 ---
if "analyzed" not in st.session_state: st.session_state.analyzed = False
if "sort_by" not in st.session_state: st.session_state.sort_by = "등락률숫자"

# ==========================================
# 🔑 설정 및 포트폴리오 정의
# ==========================================
# (기존 WEB_APP_URL 등은 그대로 유지하세요)
WEB_APP_URL = "여기에_웹앱_URL을_넣어주세요"

SAMSUNG_TICKER = "005930.KS"

fixed_portfolio = [
    {"name": "GLDM", "ticker": "GLDM", "ratio": 0.04, "country": "US"},
    {"name": "VTV",  "ticker": "VTV",  "ratio": 0.04, "country": "US"},
    {"name": "TLT",  "ticker": "TLT",  "ratio": 0.025, "country": "US"},
    {"name": "IEI",  "ticker": "IEI",  "ratio": 0.015, "country": "US"},
    {"name": "SCHD", "ticker": "SCHD", "ratio": 0.04, "country": "US"},
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
brand_meta = {
    "TSM": {"name": "📱 TSM", "color": "#8A5A5A"},
    "NVDA": {"name": "🤖 NVDA", "color": "#76B900"},
    "TSLA": {"name": "🚗 TSLA", "color": "#E31937"},
    "MSFT": {"name": "🪟 MSFT", "color": "#F34F1C"},
    "AAPL": {"name": "🍎 AAPL", "color": "#A2AAAD"},
    "GOOGL": {"name": "🔍 GOOGL", "color": "#4285F4"},
    "AMD": {"name": "💻 AMD", "color": "#ED1C24"},
    "AMZN": {"name": "🛒 AMZN", "color": "#FF9900"},
    "SK하이닉스": {"name": "💾 SK하이닉스", "color": "#E60012"},
    "현대차": {"name": "🚙 현대차", "color": "#002C5F"},
    "삼성전자": {"name": "🔒 삼성전자", "color": "#1428A0"},
    "GLDM": {"name": "🥇 GLDM", "color": "#FFD700"},
    "VTV": {"name": "🏦 VTV", "color": "#00509E"},
    "TLT": {"name": "📜 TLT", "color": "#0076CE"},
    "IEI": {"name": "📄 IEI", "color": "#0093D0"},
    "SCHD": {"name": "💸 SCHD", "color": "#005A9C"},
    "예수금": {"name": "💵 예수금", "color": "#85BB65"}
}

def get_brand(raw_name):
    key = raw_name.split()[0]
    return brand_meta.get(key, {"name": raw_name, "color": "#9E9E9E"})

# ==========================================
# 📊 데이터 엔진 (Batch Processing)
# ==========================================
@st.cache_data(ttl=600)
def fetch_all_data(tickers):
    """모든 티커의 데이터를 한 번에 가져와서 속도 최적화"""
    data = yf.download(tickers, period="5d", interval="1d", progress=False)
    # MultiIndex 처리
    if isinstance(data.columns, pd.MultiIndex):
        return data
    return data

def calculate_stock_metrics(ticker, country, full_df, exc_rate):
    """Batch 데이터에서 특정 종목의 지표 추출"""
    try:
        hist = full_df.xs(ticker, axis=1, level=1) if isinstance(full_df.columns, pd.MultiIndex) else full_df
        
        # 최신 종가(실시간에 가까운)와 전일 종가 추출
        close_prices = hist['Close'].dropna()
        if len(close_prices) < 3: return 0, 0, 0, 0, 0
        
        curr_p = close_prices.iloc[-1]
        prev_p = close_prices.iloc[-2]
        d2_p = close_prices.iloc[-3]
        
        change_pct = ((curr_p - prev_p) / prev_p) * 100
        prev_change_pct = ((prev_p - d2_p) / d2_p) * 100
        
        return curr_p, change_pct, prev_p, prev_change_pct, d2_p
    except:
        return 0, 0, 0, 0, 0

# ==========================================
# 🖥️ UI 레이아웃
# ==========================================
st.set_page_config(page_title="P-Quant Terminal", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널 (V2.0)")

# 입력 사이드바 또는 상단 패널
with st.expander("⚙️ 자산 및 수량 세팅", expanded=not st.session_state.analyzed):
    col1, col2 = st.columns(2)
    with col1:
        input_cash = st.number_input("💵 원화 예수금 총액", value=10000000, step=100000)
    with col2:
        sam_qty = st.number_input("🔒 삼성전자 보유 수량", value=41, step=1)
    
    holdings_input = st.text_input("🔢 종목 수량 (공백 구분)", placeholder="예: 10 5 3 0 10 50 15 20 5 10 5 8 10 200 50")
    execute_btn = st.button("실시간 분석 및 시트 기록 🚀", type="primary", use_container_width=True)

# 환율 및 시간 정보 (기존 로직 유지)
exc_rate = yf.Ticker("KRW=X").fast_info['last_price']
st.write(f"현재 환율: **{exc_rate:,.1f}원** | KST: **{datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')}**")

# ==========================================
# ⚙️ 실행 로직
# ==========================================
if execute_btn:
    with st.spinner('데이터 일괄 로딩 중...'):
        all_tickers = [s['ticker'] for s in all_stocks] + [SAMSUNG_TICKER, "KRW=X"]
        full_data = fetch_all_data(all_tickers)
        
        # 결과 저장을 위한 리스트
        stock_results = []
        total_prev_asset = input_cash
        
        # 삼성전자 계산
        s_p, s_c, s_prev, s_prev_c, s_d2 = calculate_stock_metrics(SAMSUNG_TICKER, "KR", full_data, 1)
        sam_amt = s_p * sam_qty
        total_prev_asset += (s_prev * sam_qty)
        
        # 개별 종목 계산
        user_holdings = list(map(int, holdings_input.split())) if holdings_input else [0]*len(all_stocks)
        current_stock_assets = sam_amt
        
        for i, p in enumerate(all_stocks):
            price, pct, prev, prev_pct, d2 = calculate_stock_metrics(p['ticker'], p['country'], full_data, exc_rate)
            qty = user_holdings[i] if i < len(user_holdings) else 0
            
            p_krw = price * exc_rate if p['country'] == "US" else price
            my_amt = qty * p_krw
            current_stock_assets += my_amt
            total_prev_asset += (prev * (exc_rate if p['country']=="US" else 1) * qty)
            
            stock_results.append({
                "ticker": p['ticker'], "price_krw": p_krw, "price_usd": price if p['country']=="US" else 0,
                "my_amt": my_amt, "change_pct": pct, "prev_change_pct": prev_pct, "qty": qty
            })

        # 세션 상태 업데이트 (정리된 데이터 저장)
        st.session_state.total_asset = current_stock_assets + input_cash
        st.session_state.stock_data = stock_results
        st.session_state.sam_info = {"price": s_p, "amt": sam_amt, "change": s_c, "prev_change": s_prev_c, "qty": sam_qty}
        st.session_state.analyzed = True
        st.rerun()

# ==========================================
# 📊 출력부 (Dataframe Styling)
# ==========================================
if st.session_state.analyzed:
    st.subheader(f"📊 총 자산: {st.session_state.total_asset:,.0f}원")
    
    # 여기에 기존에 작성하신 정렬 버튼 및 df_stocks 생성 로직을 적용하시면 됩니다.
    # (코드 가독성을 위해 스타일링 함수와 테이블 출력은 기존 구조를 유지하시면 완벽합니다!)
    
    # [Tip] 엔지니어용 추가 차트 제안
    # st.line_chart(...) 등을 이용해 포트폴리오의 '변동성'이나 '섹터 비중'을 시각화하면 
    # Spotfire 대시보드 부럽지 않은 터미널이 됩니다.
