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
# 1. 포트폴리오 정의 (팔란티어 삭제, 총 15종목)
# ==========================================
# (A) 현금성 자산 ETF (전체 자산의 16%)
fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.04, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.04, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.025, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.015, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.04, "country": "US"},
]

# (B) 투자 자산 (전체 자산의 63%, 내부 합계 100%)
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
# 2. 앱 화면 구성 & 차트 출력
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="📈", layout="wide")
st.title("📈 내 자산 성장 대시보드 (63:16:21)")

# --- 차트 그리기 영역 ---
try:
    if "export?format=csv" in SHEET_CSV_URL:
        history_df = pd.read_csv(SHEET_CSV_URL)
        if not history_df.empty:
            history_df.columns = ['날짜', '총자산']
            history_df = history_df.drop_duplicates(subset=['날짜'], keep='last')
            history_df['날짜'] = pd.to_datetime(history_df['날짜'])
            history_df = history_df.set_index('날짜')
            
            st.area_chart(history_df['총자산'])
            
            if len(history_df) >= 2:
                last_asset = history_df['총자산'].iloc[-1]
                prev_asset = history_df['총자산'].iloc[-2]
                diff = last_asset - prev_asset
                st.metric(label="최근 기록된 총 자산", value=f"{int(last_asset):,.0f}원", delta=f"{int(diff):,.0f}원")
except Exception as e:
    st.caption("※ 시트 링크가 설정되지 않았거나 아직 데이터가 부족하여 차트를 표시할 수 없습니다.")

st.write("---")

# --- 입력 영역 (URL 기억 기능 유지) ---
params = st.query_params
try: default_cash = int(params.get("cash", "10000000"))
except: default_cash = 10000000
default_holdings = params.get("holdings", "")

st.subheader("💵 보유 현금 입력")
input_cash = st.number_input(
    "현재 계좌에 있는 현금(예수금) 총액 (원화)", 
    min_value=0, value=default_cash, step=100000, format="%d"
)

st.write("---")
st.subheader("🔢 보유 수량 입력")
st.caption(f"**입력 순서 (총 15개):** {' → '.join(all_names)}")

holdings_input = st.text_input(
    "종목별 수량 (띄어쓰기로 구분)", 
    value=default_holdings,
    placeholder="예: 10 5 3 0 10 50 15 20 5 10 5 8 10 200 50" # 팔란티어 자리 삭제됨
)

def get_real_price(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        if country == "KR": return stock.fast_info['last_price']
        else:
            df = stock.history(period="1d", interval="1m", prepost=True)
            if not df.empty: return df['Close'].iloc[-1]
            else: return stock.fast_info['last_price']
    except: return 0

# --- 실행 버튼 ---
if st.button("분석 실행 및 시트에 기록 🚀", type="primary"):
    
    st.query_params["cash"] = str(input_cash)
    st.query_params["holdings"] = holdings_input
    
    try:
        if holdings_input.strip() == "": user_holdings = [0] * len(all_stocks)
        else: user_holdings = list(map(int, holdings_input.split()))
        if len(user_holdings) < len(all_stocks): user_holdings += [0] * (len(all_stocks) - len(user_holdings))
    except ValueError:
        st.error("숫자와 띄어쓰기만 입력해주세요!")
        st.stop()

    with st.spinner('실시간 데이터 분석 및 시트 기록 중...'):
        
        try: exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except: exchange_rate = 1400 
        
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
            stock_data_cache.append({"price_krw": price_krw, "price_usd": price_usd, "my_amt": my_amt})

        total_asset = current_stock_assets + input_cash

        if total_asset == 0:
            st.error("총 자산이 0원입니다.")
            st.stop()

        # 구글 시트 전송
        if "script.google.com" in WEB_APP_URL:
            try:
                kst = timezone(timedelta(hours=9))
                today_str = datetime.now(kst).strftime("%Y-%m-%d")
                requests.post(WEB_APP_URL, data={"date": today_str, "asset": int(total_asset)})
            except:
                pass

        st.success(f"**📊 총 자산:** {total_asset:,.0f}원 (구글 시트에 기록되었습니다!)")
        st.info("💡 주소창의 링크를 '홈 화면에 추가' 해두시면 다음에도 입력값이 유지됩니다.")
        st.write("---")

        rows = []
        total_buy_cost = 0 
        
        # ★ 예산 배분 업데이트 (투자 자산 63%)
        budget_invest = total_asset * 0.63  

        for i, p in enumerate(all_stocks):
            cached = stock_data_cache[i]
            price_krw = cached['price_krw']
            price_usd = cached['price_usd']
            my_amt = cached['my_amt']
            my_qty = user_holdings[i]

            if i < 5: 
                category = "현금성ETF"
                target_amt = total_asset * p['ratio']
                display_target_ratio = p['ratio']
            elif p['country'] == "KR": 
                category = "국장(투자)"
                target_amt = budget_invest * p['ratio']
                display_target_ratio = 0.63 * p['ratio']
            else: 
                category = "미장(투자)"
                target_amt = budget_invest * p['ratio']
                display_target_ratio = 0.63 * p['ratio']

            if price_krw > 0: target_qty = round(target_amt / price_krw)
            else: target_qty = 0
            
            actual_target_cost = target_qty * price_krw
            total_buy_cost += actual_target_cost
            current_ratio = my_amt / total_asset

            diff = target_qty - my_qty
            if diff > 0: action = f"🔴 {int(diff)}주 매수"
            elif diff < 0: action = f"🔵 {int(abs(diff))}주 매도"
            else: action = "🟢 유지"

            if p['country'] == "US": price_display = f"${price_usd:,.2f}"
            else: price_display = "-"

            rows.append({
                "구분": category, "종목": p['name'], "현재가($)": price_display, "현재가(₩)": f"{price_krw:,.0f}원",
                "목표비중(전체)": display_target_ratio, "실제비중": current_ratio,
                "목표금액": actual_target_cost, "목표금액(표시)": actual_target_cost,
                "목표수량": int(target_qty), "내보유": int(my_qty), "실행": action,
            })

        # ★ 잔여 현금 계산 (자연스럽게 약 21% 남음)
        remaining_cash = total_asset - total_buy_cost
        rows.append({
            "구분": "💵 잔여현금", "종목": "예수금 (KRW)", "현재가($)": "-", "현재가(₩)": "1원",
            "목표비중(전체)": 0.21, "실제비중": input_cash / total_asset,
            "목표금액": remaining_cash, "목표금액(표시)": remaining_cash,
            "목표수량": int(remaining_cash), "내보유": int(input_cash),
            "실행": f"예상잔고: {remaining_cash:,.0f}원",
        })

        df = pd.DataFrame(rows)
        df = df.sort_values(by='목표금액', ascending=False)
        
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
                    .format({"목표비중(전체)": "{:.1%}", "실제비중": "{:.1%}", "목표금액(표시)": "{:,.0f}원", "내보유": "{:,.0f}", "목표수량": "{:,.0f}"}),
            column_order=["구분", "종목", "현재가($)", "현재가(₩)", "목표비중(전체)", "실제비중", "목표금액(표시)", "목표수량", "내보유", "실행"],
            hide_index=True, use_container_width=True, height=900
        )
