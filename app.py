import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 사용자 포트폴리오 설정 (수정 금지)
# ==========================================
# 1. 고정 자산 (전체 자산의 20%)
fixed_portfolio = [
    {"name": "GLDM (금)",   "ticker": "GLDM", "ratio": 0.05, "country": "US"},
    {"name": "VTV (가치주)", "ticker": "VTV",  "ratio": 0.05, "country": "US"},
    {"name": "SCHD (배당)",  "ticker": "SCHD", "ratio": 0.05, "country": "US"},
    {"name": "TLT (장기채)", "ticker": "TLT",  "ratio": 0.03, "country": "US"},
    {"name": "IEI (중기채)", "ticker": "IEI",  "ratio": 0.02, "country": "US"},
]

# 2. 투자 자산 (나머지 60% 예산 내에서의 비중)
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

# ==========================================
# 앱 화면 구성
# ==========================================
st.set_page_config(page_title="리밸런싱 계산기", page_icon="💰")
st.title("💰 주식 리밸런싱 계산기")

# 입력창 (숫자만 입력)
total_asset = st.number_input(
    "내 총 자산 입력 (주식 평가액 + 현금)", 
    min_value=0, value=100000000, step=1000000, format="%d"
)

if st.button("몇 주 가지고 있어야 해? 🔍", type="primary"):
    with st.spinner('실시간 시세 조회 중...'):
        try:
            exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except:
            exchange_rate = 1400 
        
        st.info(f"💵 환율 적용: {exchange_rate:,.2f}원")

        cash_budget = total_asset * 0.20
        invest_budget_total = total_asset * 0.60
        
        rows = []

        # 고정자산 계산
        for p in fixed_portfolio:
            target_amt = total_asset * p['ratio']
            price = yf.Ticker(p['ticker']).fast_info['last_price']
            qty = round(target_amt / (price * exchange_rate))
            rows.append({"구분": "고정", "종목": p['name'], "📌 목표수량": f"{int(qty)}주"})

        # 투자자산 계산
        for p in invest_portfolio:
            target_amt = invest_budget_total * p['ratio']
            try:
                if p['country'] == "KR":
                    price_krw = yf.Ticker(p['ticker']).fast_info['last_price']
                else:
                    price_krw = yf.Ticker(p['ticker']).fast_info['last_price'] * exchange_rate
            except: price_krw = 1
            
            qty = round(target_amt / price_krw)
            rows.append({"구분": "투자", "종목": p['name'], "📌 목표수량": f"{int(qty)}주"})

        # 결과 출력
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.success(f"💰 현금 목표: {cash_budget:,.0f}원 (20%)")
