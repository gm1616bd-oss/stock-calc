import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 포트폴리오 정의 (현금 제외, 100% 주식 비중으로 재조정)
# ==========================================

# 기존 비율 (고정 20 : 투자 60) -> (고정 25% : 투자 75%)로 자동 비례 배분
# 비율이 1:3 이므로, 총 자산의 25%는 고정, 75%는 투자자산 그룹에 배정됩니다.

# (A) 고정 자산 (입력하신 5개 종목)
# 기존 0.05(5%) -> 재조정 후 약 6.25%
fixed_portfolio = [
    {"name": "GLDM (금)",   "ticker": "GLDM", "ratio": 0.05, "country": "US"},
    {"name": "VTV (가치주)", "ticker": "VTV",  "ratio": 0.05, "country": "US"},
    {"name": "SCHD (배당)",  "ticker": "SCHD", "ratio": 0.05, "country": "US"},
    {"name": "TLT (장기채)", "ticker": "TLT",  "ratio": 0.03, "country": "US"},
    {"name": "IEI (중기채)", "ticker": "IEI",  "ratio": 0.02, "country": "US"},
]
# 원래 고정자산 합계(0.20)

# (B) 투자 자산 (나머지 종목들)
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
# 원래 투자자산 예산 내 비중 합계(1.0)

# ==========================================
# 2. 앱 화면 구성
# ==========================================
st.set_page_config(page_title="리밸런싱 계산기", page_icon="💰")
st.title("💰 실시간 주식 리밸런싱 (Full Invest)")

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
    
    with st.spinner('환율 및 실시간 시세(프리/애프터) 조회 중...'):
        
        # 1. 환율 조회
        try:
            exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except:
            exchange_rate = 1400 
        
        st.success(f"💵 현재 환율 적용: 1달러 = {exchange_rate:,.2f}원")

        # 2. 예산 배분 (현금 없이 100% 주식)
        # 기존 20:60 비율을 유지하면서 100%로 확장 -> 25% : 75%
        # 고정자산 그룹 예산 = 총액 * (20/80)
        fixed_budget_total = total_asset * (20/80) 
        # 투자자산 그룹 예산 = 총액 * (60/80)
        invest_budget_total = total_asset * (60/80)

        rows = []

        # --- A. 고정 자산 계산 ---
        # 기존 비율(0.20) 내에서의 비중을 재계산
        fixed_total_ratio_sum = 0.20 # 원래 입력한 비율의 합
        
        for p in fixed_portfolio:
            # 개별 종목의 배정 금액 = (해당종목비율 / 전체고정비율합) * 고정자산예산
            target_amt = (p['ratio'] / fixed_total_ratio_sum) * fixed_budget_total
            
            # 가격 조회
            price = get_real_price(p['ticker'], p['country'])
            
            # 화폐 단위 구분
            if p['country'] == "US":
                price_usd = price
                price_krw = price * exchange_rate
                price_display = f"${price_usd:,.2f}"
            else:
                price_usd = 0
                price_krw = price
                price_display = "-"
            
            if price_krw > 0:
                qty = round(target_amt / price_krw)
                rows.append({
                    "종목": p['name'],
                    "현재가($)": price_display,
                    "현재가(₩)": f"{price_krw:,.0f}원",
                    "목표수량": int(qty),
                    "배정금액": int(target_amt), # 정렬용 숫자
                    "배정금액(표시)": f"{int(target_amt):,.0f}원"
                })

        # --- B. 투자 자산 계산 ---
        for p in invest_portfolio:
            # 투자자산은 이미 그룹 내 비중(%)으로 되어있으므로 바로 곱함
            target_amt = invest_budget_total * p['ratio']
            
            # 가격 조회
            price = get_real_price(p['ticker'], p['country'])
            
            # 화폐 단위 구분
            if p['country'] == "US":
                price_usd = price
                price_krw = price * exchange_rate
                price_display = f"${price_usd:,.2f}"
            else:
                price_usd = 0
                price_krw = price
                price_display = "-"
            
            if price_krw > 0:
                qty = round(target_amt / price_krw)
                rows.append({
                    "종목": p['name'],
                    "현재가($)": price_display,
                    "현재가(₩)": f"{price_krw:,.0f}원",
                    "목표수량": int(qty),
                    "배정금액": int(target_amt), # 정렬용 숫자
                    "배정금액(표시)": f"{int(target_amt):,.0f}원"
                })

        # 3. 결과 출력 (금액 큰 순서대로 정렬)
        df = pd.DataFrame(rows)
        
        # 정렬: 배정금액 기준 내림차순
        df = df.sort_values(by='배정금액', ascending=False)
        
        # 화면에 보여줄 컬럼만 선택
        display_df = df[["종목", "현재가($)", "현재가(₩)", "목표수량", "배정금액(표시)"]]

        st.dataframe(
            display_df, 
            column_config={
                "목표수량": st.column_config.TextColumn("📌 목표수량", help="반올림 기준"),
                "배정금액(표시)": st.column_config.TextColumn("배정된 금액"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        st.info("💡 현금 비중 없이 입력하신 예산 100%를 주식에 배분했습니다.")
