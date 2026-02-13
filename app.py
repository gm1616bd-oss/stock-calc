import streamlit as st
import yfinance as yf
import pandas as pd

# ==========================================
# 1. 포트폴리오 정의 (순서 고정)
# ==========================================

# (A) 현금성 자산 ETF (20%)
fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.05, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.05, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.03, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.02, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.05, "country": "US"},
]

# (B) 투자 자산 (60%)
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
# 2. 앱 화면 구성
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="⚖️", layout="wide")
st.title("⚖️ 스마트 리밸런싱 (정밀 보정판)")

# 1) 현금 입력
st.subheader("💵 보유 현금 입력")
input_cash = st.number_input(
    "현재 계좌에 있는 현금(예수금) 총액 (원화)", 
    min_value=0, value=10000000, step=100000, format="%d"
)

st.write("---")

# 2) 보유 수량 입력
st.subheader("🔢 보유 수량 입력")
st.caption(f"**입력 순서:** {' → '.join(all_names)}")

holdings_input = st.text_input(
    "종목별 수량 (띄어쓰기로 구분)", 
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

if st.button("자산 분석 및 리밸런싱 🚀", type="primary"):
    
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

    with st.spinner('1단계: 실시간 주가로 내 총 자산 계산 중...'):
        
        # 환율 조회
        try:
            exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except:
            exchange_rate = 1400 
        
        # 1. 내 보유 주식의 현재 평가액 계산
        current_stock_assets = 0
        stock_data_cache = [] 

        for i, p in enumerate(all_stocks):
            price = get_real_price(p['ticker'], p['country'])
            
            if p['country'] == "US":
                price_krw = price * exchange_rate
                price_usd = price
            else:
                price_krw = price
                price_usd = 0
            
            my_qty = user_holdings[i]
            my_amt = my_qty * price_krw
            current_stock_assets += my_amt
            
            stock_data_cache.append({
                "price_krw": price_krw,
                "price_usd": price_usd,
                "my_amt": my_amt
            })

        # 2. 총 자산 확정
        total_asset = current_stock_assets + input_cash

        if total_asset == 0:
            st.error("총 자산이 0원입니다. 현금이나 보유 수량을 입력해주세요.")
            st.stop()

        st.success(f"**📊 총 자산:** {total_asset:,.0f}원 (주식: {current_stock_assets:,.0f}원 + 현금: {input_cash:,.0f}원)")
        st.write("---")

    with st.spinner('2단계: 리밸런싱 목표 수량 계산 중...'):

        rows = []
        total_buy_cost = 0 # 목표대로 샀을 때 주식 총 비용

        for i, p in enumerate(all_stocks):
            
            # 저장해둔 가격 정보
            cached = stock_data_cache[i]
            price_krw = cached['price_krw']
            price_usd = cached['price_usd']
            my_amt = cached['my_amt']
            my_qty = user_holdings[i]

            # 구분
            if i < 5: category = "현금성ETF"
            elif p['country'] == "KR": category = "국장(투자)"
            else: category = "미장(투자)"

            # ★ 목표 금액 (총 자산 대비 정해진 비율)
            # 5.1% 등으로 변하지 않게 고정 비율 사용
            target_amt = total_asset * p['ratio']

            # 목표 수량 (반올림)
            if price_krw > 0:
                target_qty = round(target_amt / price_krw)
            else:
                target_qty = 0
            
            # 반올림으로 인해 실제 투입되는 금액
            actual_target_cost = target_qty * price_krw
            total_buy_cost += actual_target_cost

            # 비중 계산 (0.2 -> 20%)
            # 목표비중: 반올림 전 '이론상 비중'을 보여줌 (깔끔하게 5%, 22%)
            theoretical_ratio = p['ratio'] 
            
            # 실제비중: 현재 내 자산 기준
            current_ratio = my_amt / total_asset

            # 실행 신호
            diff = target_qty - my_qty
            if diff > 0:
                action = f"🔴 {int(diff)}주 매수"
            elif diff < 0:
                action = f"🔵 {int(abs(diff))}주 매도"
            else:
                action = "🟢 유지"

            if p['country'] == "US":
                price_display = f"${price_usd:,.2f}"
            else:
                price_display = "-"

            rows.append({
                "구분": category,
                "종목": p['name'],
                "현재가($)": price_display,
                "현재가(₩)": f"{price_krw:,.0f}원",
                "목표비중": theoretical_ratio, # 5.0% 고정
                "실제비중": current_ratio,
                "목표금액": actual_target_cost, # 반올림 반영된 금액
                "목표금액(표시)": actual_target_cost,
                "목표수량": int(target_qty),
                "내보유": int(my_qty),
                "실행": action,
            })

        # === 잔여 현금 계산 ===
        # 총 자산 - 주식 사는데 들어가는 돈(반올림 반영) = 남는 현금
        remaining_cash = total_asset - total_buy_cost
        
        # 현금 비중
        cash_ratio_theoretical = 0.20 # 목표는 무조건 20%
        current_cash_ratio = input_cash / total_asset # 현재 내 실제 비중

        rows.append({
            "구분": "💵 잔여현금",
            "종목": "예수금 (KRW)",
            "현재가($)": "-",
            "현재가(₩)": "1원",
            "목표비중": cash_ratio_theoretical, # 20.0% 고정
            "실제비중": current_cash_ratio,
            "목표금액": remaining_cash,
            "목표금액(표시)": remaining_cash,
            "목표수량": int(remaining_cash),
            "내보유": int(input_cash),
            "실행": f"예상잔고: {remaining_cash:,.0f}원",
        })

        # DataFrame
        df = pd.DataFrame(rows)
        df = df.sort_values(by='목표금액', ascending=False)
        
        # 스타일링
        def style_dataframe(row):
            bg_color = 'white'
            if row['구분'] == '💵 잔여현금': bg_color = '#FFECB3'
            elif row['구분'] == '현금성ETF': bg_color = '#FFF9C4'
            elif row['구분'] == '국장(투자)': bg_color = '#E3F2FD'
            elif row['구분'] == '미장(투자)': bg_color = '#FCE4EC'
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
