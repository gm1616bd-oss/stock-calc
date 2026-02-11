import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 포트폴리오 정의 (순서 고정)
# ==========================================

# (A) 고정 자산 (총 자산의 25%) - 5개
fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.05, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.05, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.03, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.02, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.05, "country": "US"},
]

# (B) 투자 자산 (총 자산의 75%) - 11개
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

# 전체 리스트 합치기 (순서대로 입력받기 위함)
all_stocks = fixed_portfolio + invest_portfolio
all_names = [item['name'].split()[0] for item in all_stocks] # 이름만 추출

# ==========================================
# 2. 앱 화면 구성
# ==========================================
st.set_page_config(page_title="내 포트폴리오", page_icon="⚡️", layout="wide")
st.title("⚡️ 원클릭 리밸런싱 계산기")

# 1) 총 예산 입력
total_asset = st.number_input(
    "💰 투입할 총 예산 (현금+주식포함)", 
    min_value=0, value=100000000, step=1000000, format="%d"
)

st.write("---")

# 2) 보유 수량 입력 (한 줄)
st.subheader("📊 현재 보유 수량 입력")
st.info(f"아래 순서대로 **띄어쓰기**로 구분해서 숫자만 입력하세요 (총 {len(all_stocks)}개)")

# 순서 가이드 보여주기
order_guide = " → ".join(all_names)
st.caption(f"**순서:** {order_guide}")

# 입력창
holdings_input = st.text_input(
    "보유수량 (예: 10 5 3 0 ...)", 
    placeholder="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"
)

# 가격 조회 함수
def get_real_price(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        if country == "KR":
            return stock.fast_info['last_price']
        else:
            df = stock.history(period="1d", interval="1m", prepost=True)
            if not df.empty:
                return df['Close'].iloc[-1]
            else:
                return stock.fast_info['last_price']
    except:
        return 0

if st.button("계산 실행 🚀", type="primary"):
    
    # 입력값 파싱 (숫자로 변환)
    try:
        if holdings_input.strip() == "":
            user_holdings = [0] * len(all_stocks)
        else:
            user_holdings = list(map(int, holdings_input.split()))
            
        # 개수 안 맞으면 0으로 채우기
        if len(user_holdings) < len(all_stocks):
            user_holdings += [0] * (len(all_stocks) - len(user_holdings))
            st.warning(f"⚠️ 입력된 숫자가 부족하여 뒷부분은 0으로 처리했습니다.")
            
    except ValueError:
        st.error("숫자와 띄어쓰기만 입력해주세요!")
        st.stop()

    with st.spinner('실시간 시세와 환율을 조회 중입니다...'):
        
        # 환율 조회
        try:
            exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except:
            exchange_rate = 1400 
        
        st.success(f"💵 환율: 1달러 = {exchange_rate:,.2f}원")

        # 예산 배분
        fixed_budget = total_asset * 0.25
        invest_budget = total_asset * 0.75
        
        fixed_ratio_sum = 0.20 # 고정자산 원래 비율 합
        
        rows = []

        # 통합 루프 (입력 순서 = 리스트 순서)
        for i, p in enumerate(all_stocks):
            
            # 목표 금액 계산
            if i < 5: # 고정자산 그룹 (0~4)
                target_amt = (p['ratio'] / fixed_ratio_sum) * fixed_budget
            else: # 투자자산 그룹 (5~15)
                target_amt = invest_budget * p['ratio']

            # 가격 조회
            price = get_real_price(p['ticker'], p['country'])
            
            if p['country'] == "US":
                price_usd = price
                price_krw = price * exchange_rate
                price_display = f"${price_usd:,.2f}"
            else:
                price_display = "-"
                price_krw = price
            
            # 수량 계산
            if price_krw > 0:
                target_qty = round(target_amt / price_krw)
            else:
                target_qty = 0
            
            # 차이 계산 (내 보유량 - 목표량)
            my_qty = user_holdings[i]
            diff = target_qty - my_qty
            
            # 행동 가이드 (매수/매도/유지)
            if diff > 0:
                action = f"🔴 {int(diff)}주 매수"
            elif diff < 0:
                action = f"🔵 {int(abs(diff))}주 매도"
            else:
                action = "🟢 유지"

            rows.append({
                "종목": p['name'],
                "현재가($)": price_display,
                "현재가(₩)": f"{price_krw:,.0f}원",
                "목표": int(target_qty),
                "내보유": int(my_qty),
                "👉 실행": action,
                "금액": int(target_amt) # 내부 정렬용
            })

        # 결과 출력
        df = pd.DataFrame(rows)
        
        # 스타일링 함수 (매수=빨강, 매도=파랑)
        def highlight_action(val):
            color = 'black'
            bg_color = ''
            if '매수' in str(val):
                color = '#D32F2F' # 진한 빨강
                bg_color = '#FFEBEE' # 연한 빨강 배경
            elif '매도' in str(val):
                color = '#1976D2' # 진한 파랑
                bg_color = '#E3F2FD' # 연한 파랑 배경
            return f'color: {color}; background-color: {bg_color}; font-weight: bold;'

        # 표 보여주기
        st.dataframe(
            df.style.applymap(highlight_action, subset=['👉 실행']),
            column_order=["종목", "현재가($)", "현재가(₩)", "목표", "내보유", "👉 실행"],
            hide_index=True,
            use_container_width=True,
            height=600
        )
