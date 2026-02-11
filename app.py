import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 포트폴리오 정의 (사용자 지정 순서 적용)
# ==========================================

# (A) 고정 자산 (총 자산의 25% 배정)
# 순서: 금 -> 가치주 -> 장기채 -> 중기채 -> 배당주
fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.05, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.05, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.03, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.02, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.05, "country": "US"},
]

# (B) 투자 자산 (총 자산의 75% 배정)
# 순서: TSM -> NVDA -> TSLA -> MSFT -> AAPL -> GOOGL -> AMD -> AMZN -> PLTR -> 하이닉스 -> 현대차
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
# 2. 앱 화면 구성
# ==========================================
st.set_page_config(page_title="내 포트폴리오", page_icon="📝")
st.title("📝 지정 순서 리밸런싱")

# 입력창
total_asset = st.number_input(
    "투입할 총 예산 입력 (원화)", 
    min_value=0, value=100000000, step=1000000, format="%d"
)

# 가격 조회 함수 (프리장/애프터마켓 반영)
def get_real_price(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        if country == "KR":
            return stock.fast_info['last_price']
        else:
            # 미국장은 프리/애프터 반영
            df = stock.history(period="1d", interval="1m", prepost=True)
            if not df.empty:
                return df['Close'].iloc[-1]
            else:
                return stock.fast_info['last_price']
    except:
        return 0

if st.button("계산 실행 🚀", type="primary"):
    
    with st.spinner('지정된 순서대로 시세 조회 중...'):
        
        # 1. 환율 조회
        try:
            exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except:
            exchange_rate = 1400 
        
        st.success(f"💵 현재 환율 적용: 1달러 = {exchange_rate:,.2f}원")

        # 2. 예산 배분 (고정 25% : 투자 75%)
        # 원래 비율이 고정(20) : 투자(60)이었으므로 이를 100%로 환산하면 1:3 비율입니다.
        fixed_budget_total = total_asset * 0.25 
        invest_budget_total = total_asset * 0.75

        rows = []

        # --- A. 고정 자산 계산 ---
        fixed_total_ratio_sum = 0.20 # 원래 입력 비율의 합
        
        for p in fixed_portfolio:
            target_amt = (p['ratio'] / fixed_total_ratio_sum) * fixed_budget_total
            
            price = get_real_price(p['ticker'], p['country'])
            
            if p['country'] == "US":
                price_usd = price
                price_krw = price * exchange_rate
                price_display = f"${price_usd:,.2f}"
            else:
                price_display = "-"
                price_krw = price
            
            if price_krw > 0:
                qty = round(target_amt / price_krw)
                rows.append({
                    "종목": p['name'],
                    "현재가($)": price_display,
                    "현재가(₩)": f"{price_krw:,.0f}원",
                    "목표수량": int(qty),
                    "배정금액": f"{int(target_amt):,.0f}원"
                })

        # --- B. 투자 자산 계산 ---
        for p in invest_portfolio:
            target_amt = invest_budget_total * p['ratio'] # 투자자산은 이미 그룹 내 비중(1.0)
            
            price = get_real_price(p['ticker'], p['country'])
            
            if p['country'] == "US":
                price_usd = price
                price_krw = price * exchange_rate
                price_display = f"${price_usd:,.2f}"
            else:
                price_display = "-"
                price_krw = price
            
            if price_krw > 0:
                qty = round(target_amt / price_krw)
                rows.append({
                    "종목": p['name'],
                    "현재가($)": price_display,
                    "현재가(₩)": f"{price_krw:,.0f}원",
                    "목표수량": int(qty),
                    "배정금액": f"{int(target_amt):,.0f}원"
                })

        # 3. 결과 출력 (정렬 없이 입력 순서 그대로 출력)
        df = pd.DataFrame(rows)
        
        # 컬럼 순서 지정
        display_df = df[["종목", "현재가($)", "현재가(₩)", "목표수량", "배정금액"]]

        st.dataframe(
            display_df, 
            column_config={
                "목표수량": st.column_config.TextColumn("📌 목표수량", help="반올림 기준"),
                "배정금액": st.column_config.TextColumn("배정된 금액"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        st.info("💡 요청하신 지정 순서대로 출력되었습니다.")
