import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 포트폴리오 정의 (순서 고정)
# ==========================================

# (A) 현금성 자산 ETF (목표: 총 자산의 20%)
fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.05, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.05, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.03, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.02, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.05, "country": "US"},
]

# (B) 투자 자산 (목표: 총 자산의 60%)
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

# 전체 리스트 (입력 순서용)
all_stocks = fixed_portfolio + invest_portfolio
all_names = [item['name'].split()[0] for item in all_stocks] 

# ==========================================
# 2. 앱 화면 구성
# ==========================================
st.set_page_config(page_title="내 포트폴리오", page_icon="🏦", layout="wide")
st.title("🏦 실전 자산배분 계산기")

# 1) 현재 자산 현황 입력 (3가지)
st.subheader("💰 현재 자산 현황 입력")
col1, col2, col3 = st.columns(3)

with col1:
    input_domestic = st.number_input("🇰🇷 국내주식 총액", min_value=0, value=0, step=1000000, format="%d")
with col2:
    input_foreign = st.number_input("🇺🇸 해외주식 총액 (원화)", min_value=0, value=0, step=1000000, format="%d")
with col3:
    input_cash = st.number_input("💵 보유 현금 (예수금)", min_value=0, value=100000000, step=1000000, format="%d")

# 총 자산 계산
total_asset = input_domestic + input_foreign + input_cash

if total_asset > 0:
    st.info(f"**📊 총 운용 자산:** {total_asset:,.0f}원 (이 금액을 기준으로 리밸런싱합니다)")
else:
    st.warning("위 칸에 현재 자산을 입력해주세요.")

st.write("---")

# 2) 보유 수량 입력
st.subheader("🔢 개별 종목 보유 수량")
st.caption(f"**입력 순서:** {' → '.join(all_names)}")

holdings_input = st.text_input(
    "보유수량 (띄어쓰기로 구분)", 
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
    
    if total_asset == 0:
        st.error("자산 금액을 먼저 입력해주세요.")
        st.stop()

    # 입력값 파싱
    try:
        if holdings_input.strip() == "":
            user_holdings = [0] * len(all_stocks)
        else:
            user_holdings = list(map(int, holdings_input.split()))
            
        if len(user_holdings) < len(all_stocks):
            user_holdings += [0] * (len(all_stocks) - len(user_holdings))
            
    except ValueError:
        st.error("숫자와 띄어쓰기만 입력해주세요!")
        st.stop()

    with st.spinner('실시간 시세 조회 및 계산 중...'):
        
        try:
            exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except:
            exchange_rate = 1400 
        
        st.success(f"💱 현재 환율: 1달러 = {exchange_rate:,.2f}원")

        # === 예산 배분 ===
        # 총 자산의 20%는 현금성 ETF, 60%는 투자주식에 배정 (총 80%)
        # 나머지 20%는 '남는 돈(현금)'이 됨
        
        fixed_budget = total_asset * 0.20
        invest_budget = total_asset * 0.60
        fixed_ratio_sum = 0.20 
        
        rows = []
        total_stock_cost = 0 # 주식 사는데 드는 총 비용

        # --- 주식 종목 계산 ---
        for i, p in enumerate(all_stocks):
            
            # 구분
            if i < 5:
                category = "현금성ETF" 
            elif p['country'] == "KR":
                category = "국장(투자)"   
            else:
                category = "미장(투자)"   

            # 목표 금액 배정
            if i < 5: 
                target_amt = (p['ratio'] / fixed_ratio_sum) * fixed_budget
            else: 
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
            
            # 수량 계산 (반올림)
            if price_krw > 0:
                target_qty = round(target_amt / price_krw)
            else:
                target_qty = 0
            
            # 실제 필요한 금액 (반올림된 수량 * 가격)
            actual_cost = target_qty * price_krw
            total_stock_cost += actual_cost

            # 내 현황
            my_qty = user_holdings[i]
            my_amt = my_qty * price_krw
            
            # 비중 계산
            target_ratio = (actual_cost / total_asset) * 100 # 실제 매수 금액 기준 비중
            current_ratio = (my_amt / total_asset) * 100

            # 실행 신호
            diff = target_qty - my_qty
            if diff > 0:
                action = f"🔴 {int(diff)}주 매수"
            elif diff < 0:
                action = f"🔵 {int(abs(diff))}주 매도"
            else:
                action = "🟢 유지"

            rows.append({
                "구분": category,
                "종목": p['name'],
                "현재가($)": price_display,
                "현재가(₩)": f"{price_krw:,.0f}원",
                "목표비중": target_ratio / 100,
                "실제비중": current_ratio / 100,
                "목표금액": actual_cost, # 반올림 반영된 실제 금액
                "목표금액(표시)": actual_cost,
                "목표수량": int(target_qty),
                "내보유": int(my_qty),
                "실행": action,
            })

        # --- 남는 현금 계산 ---
        # 총 자산 - 주식 사는데 쓴 돈 = 남는 현금
        remaining_cash = total_asset - total_stock_cost
        cash_ratio = (remaining_cash / total_asset) * 100

        # 현금 행 추가
        rows.append({
            "구분": "💵 잔여현금",
            "종목": "예수금 (KRW)",
            "현재가($)": "-",
            "현재가(₩)": "1원",
            "목표비중": cash_ratio / 100,
            "실제비중": (input_cash / total_asset) / 100, # 현재 내 현금 비중
            "목표금액": remaining_cash,
            "목표금액(표시)": remaining_cash,
            "목표수량": int(remaining_cash),
            "내보유": int(input_cash),
            "실행": f"약 {cash_ratio:.1f}% 보유", # 현금은 매수매도가 아니라 결과값
        })

        # 결과 DataFrame
        df = pd.DataFrame(rows)
        
        # 정렬: 목표금액 높은 순
        df = df.sort_values(by='목표금액', ascending=False)
        
        # 스타일링
        def style_dataframe(row):
            bg_color = 'white'
            if row['구분'] == '💵 잔여현금':
                bg_color = '#FFECB3' # 진한 노랑
            elif row['구분'] == '현금성ETF':
                bg_color = '#FFF9C4' # 연한 노랑
            elif row['구분'] == '국장(투자)':
                bg_color = '#E3F2FD' # 연한 파랑
            elif row['구분'] == '미장(투자)':
                bg_color = '#FCE4EC' # 연한 분홍
            return [f'background-color: {bg_color}'] * len(row)

        def style_text_color(val):
            color = 'black'
            if '매수' in str(val): color = '#D32F2F'
            elif '매도' in str(val): color = '#1976D2'
            return f'color: {color}; font-weight: bold;'

        st.dataframe(
            df.style.apply(style_dataframe, axis=1)
                    .applymap(style_text_color, subset=['실행'])
                    .format({"목표비중": "{:.1%}", "실제비중": "{:.1%}", "목표금액(표시)": "{:,.0f}원", "내보유": "{:,.0f}", "목표수량": "{:,.0f}"}),
            column_order=["구분", "종목", "현재가($)", "현재가(₩)", "목표비중", "실제비중", "목표금액(표시)", "목표수량", "내보유", "실행"],
            hide_index=True,
            use_container_width=True,
            height=900
        )
        
        st.success(f"✅ 리밸런싱 완료! 주식을 모두 사고 나면 약 **{remaining_cash:,.0f}원 ({cash_ratio:.1f}%)**의 현금이 남습니다.")
