import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone

# --- 앱 메모리(Session State) 초기화 ---
if "analyzed" not in st.session_state: st.session_state.analyzed = False
if "sort_by" not in st.session_state: st.session_state.sort_by = "실제금액숫자" 
if "filter_by" not in st.session_state: st.session_state.filter_by = "전체"

# ==========================================
# 🔑 구글 시트 연결 설정
# ==========================================
SHEET_CSV_URL = "여기에_시트_CSV_링크를_넣어주세요"
WEB_APP_URL = "여기에_웹앱_URL을_넣어주세요"

# ==========================================
# 1. 포트폴리오 정의 & 브랜드 메타데이터
# ==========================================
SAMSUNG_TICKER = "005930.KS"
SAMSUNG_QTY = 41

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
all_names = [item['name'] for item in all_stocks] 

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
# 2. 데이터 캐싱 함수
# ==========================================
@st.cache_data(ttl=600)
def get_current_exchange_rate():
    try: 
        hist = yf.Ticker("KRW=X").history(period="5d")
        return hist['Close'].dropna().iloc[-1]
    except: 
        return 1400.0

@st.cache_data(ttl=3600)
def get_exchange_trend():
    try:
        df = yf.download("KRW=X", period="1mo", progress=False)
        if isinstance(df.columns, pd.MultiIndex): return df['Close']['KRW=X']
        return df['Close']
    except: return None

def get_real_price_and_change(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")
        
        if len(hist) >= 3:
            d2_close = hist['Close'].iloc[-3]
            d1_close = hist['Close'].iloc[-2]
            prev_change_pct = ((d1_close - d2_close) / d2_close) * 100
        else:
            d2_close = 0
            d1_close = stock.fast_info.get('previous_close', 0)
            prev_change_pct = 0.0

        if country == "KR":
            try: current_price = stock.fast_info['last_price']
            except: current_price = hist['Close'].iloc[-1] if not hist.empty else 0
        else:
            df_intra = stock.history(period="1d", interval="1m", prepost=True)
            if not df_intra.empty: current_price = df_intra['Close'].iloc[-1]
            else: current_price = stock.fast_info.get('last_price', d1_close)

        if d1_close > 0 and current_price > 0: change_pct = ((current_price - d1_close) / d1_close) * 100
        else: change_pct = 0.0
        
        return current_price, change_pct, d1_close, prev_change_pct, d2_close
    except: return 0, 0.0, 0, 0.0, 0

# ==========================================
# 3. 최상단 UI (단일 입력 패널 ➔ 전광판 헤더)
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널")

st.subheader("⚙️ 포트폴리오 통합 데이터 입력")
st.markdown("**(입력순서) 현금[1개] + 보유수량(삼전제외)[15개] + 평단가(원화)[16개] + 실현손익(원화)[16개]**")
st.caption(f"※ 순서: 금 가치주 장기채권 중기채권 배당주 TSM NVDA TSLA MSFT AAPL GOOGL AMD AMZN 하이닉스 현대차 삼성전자")

master_input = st.text_input("🔢 아래 칸에 띄어쓰기로 구분하여 한 줄로 붙여넣어주세요 (총 48개 숫자)", 
                             placeholder="예: 10000000 10 5 0 2 10 5 ...", 
                             value=st.query_params.get("raw_data", ""))
execute_btn = st.button("분석 실행 및 시트에 기록 🚀", type="primary", use_container_width=True)

st.write("---")

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
weekdays = ["월", "화", "수", "목", "금", "토", "일"]
date_str = f"{now.strftime('%Y년 %m월 %d일')} ({weekdays[now.weekday()]})"
time_str = now.strftime("%p %I:%M").replace("AM", "오전").replace("PM", "오후")
exc_rate = get_current_exchange_rate()

head_col1, head_col2, head_col3, head_col4 = st.columns(4)
with head_col1: 
    st.info(f"**📅 오늘 날짜**\n### {date_str}")
with head_col2:
    if st.session_state.analyzed and "total_asset" in st.session_state:
        st.info(f"**💰 총 자산**\n### {st.session_state.total_asset:,.0f}원")
    else:
        st.info(f"**💰 총 자산**\n### 분석 전")
with head_col3: 
    st.info(f"**⏰ 현재 시간 (KST)**\n### {time_str}")
with head_col4: 
    st.info(f"**💵 실시간 환율 (KRW/USD)**\n### {exc_rate:,.1f}원")
    trend_df = get_exchange_trend()
    if trend_df is not None and not trend_df.empty:
        fig_spark = go.Figure(go.Scatter(x=trend_df.index, y=trend_df.values, mode='lines', line=dict(color='#2E7D32', width=3)))
        fig_spark.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=40, xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})

st.write("---")

# ==========================================
# 4. 데이터 수집 엔진 & 입력 파싱 로직
# ==========================================
if execute_btn:
    st.query_params["raw_data"] = master_input
    
    values = []
    if master_input.strip() != "":
        try:
            values = list(map(float, master_input.replace(",", "").split()))
        except ValueError:
            st.error("숫자와 띄어쓰기만 입력해주세요!")
            st.stop()
            
    while len(values) < 48:
        values.append(0.0)
        
    input_cash = values[0]
    user_holdings = [int(v) for v in values[1:16]]
    user_avg_prices = values[16:31]
    sam_avg_price = values[31]
    user_realized_profits = values[32:47]
    sam_realized_profit = values[47]

    with st.spinner('실시간 시세 및 차트 로딩 중... (약 15초 소요)'):
        exchange_rate = get_current_exchange_rate()
        
        current_stock_assets = 0
        total_today_profit = 0
        total_prev_asset = input_cash 
        total_prev2_asset = input_cash 
        stock_data_cache = [] 
        
        cat_cur = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev2 = {"US": 0, "KR": 0, "ETF": 0}

        # 삼성전자 계산
        sam_price, sam_change, sam_prev, sam_prev_change, sam_d2 = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        sam_amt = sam_price * SAMSUNG_QTY
        sam_profit_today = sam_amt - (sam_prev * SAMSUNG_QTY)
        current_stock_assets += sam_amt
        total_today_profit += sam_profit_today
        total_prev_asset += (sam_prev * SAMSUNG_QTY)
        total_prev2_asset += (sam_d2 * SAMSUNG_QTY)
        cat_cur["KR"] += sam_amt
        cat_prev["KR"] += (sam_prev * SAMSUNG_QTY)
        cat_prev2["KR"] += (sam_d2 * SAMSUNG_QTY)
        
        sam_unreal_p = (sam_price - sam_avg_price) * SAMSUNG_QTY if sam_avg_price > 0 else 0
        sam_tot_p = sam_realized_profit + sam_unreal_p
        sam_actual_avg_p = sam_avg_price - (sam_realized_profit / SAMSUNG_QTY) if SAMSUNG_QTY > 0 else sam_avg_price
        sam_principal = sam_amt - sam_tot_p
        sam_return_pct = ((sam_price - sam_actual_avg_p) / sam_actual_avg_p * 100) if sam_actual_avg_p > 0 else 0

        # 나머지 15개 종목 순회
        for i, p in enumerate(all_stocks):
            price, change_pct, prev_close, prev_change_pct, d2_close = get_real_price_and_change(p['ticker'], p['country'])
            if p['country'] == "US":
                price_krw = price * exchange_rate
                price_usd = price
                prev_amt_krw = prev_close * exchange_rate * user_holdings[i]
                prev2_amt_krw = d2_close * exchange_rate * user_holdings[i]
            else:
                price_krw = price
                price_usd = 0
                prev_amt_krw = prev_close * user_holdings[i]
                prev2_amt_krw = d2_close * user_holdings[i]
            
            my_qty = user_holdings[i]
            my_amt = my_qty * price_krw
            today_profit = my_amt - prev_amt_krw
            
            avg_p = user_avg_prices[i]
            real_p = user_realized_profits[i]
            
            unreal_p = (price_krw - avg_p) * my_qty if avg_p > 0 else 0
            tot_p = real_p + unreal_p
            actual_avg_p = avg_p - (real_p / my_qty) if my_qty > 0 else avg_p
            principal = my_amt - tot_p
            return_pct = ((price_krw - actual_avg_p) / actual_avg_p * 100) if actual_avg_p > 0 else 0

            current_stock_assets += my_amt
            total_today_profit += today_profit
            total_prev_asset += prev_amt_krw
            total_prev2_asset += prev2_amt_krw
            
            if i < 5:
                cat_cur["ETF"] += my_amt
                cat_prev["ETF"] += prev_amt_krw
                cat_prev2["ETF"] += prev2_amt_krw
                cat_label = "현금성"
            elif p['country'] == 'US':
                cat_cur["US"] += my_amt
                cat_prev["US"] += prev_amt_krw
                cat_prev2["US"] += prev2_amt_krw
                cat_label = "미장"
            else:
                cat_cur["KR"] += my_amt
                cat_prev["KR"] += prev_amt_krw
                cat_prev2["KR"] += prev2_amt_krw
                cat_label = "국장"
            
            stock_data_cache.append({
                "price_krw": price_krw, "price_usd": price_usd, "my_amt": my_amt, 
                "change_pct": change_pct, "today_profit": today_profit, "prev_change_pct": prev_change_pct,
                "avg_p": avg_p, "actual_avg_p": actual_avg_p, "real_p": real_p, 
                "unreal_p": unreal_p, "tot_p": tot_p, "principal": principal, 
                "return_pct": return_pct, "cat_label": cat_label
            })

        total_asset = current_stock_assets + input_cash
        total_daily_return_pct = (total_today_profit / total_prev_asset) * 100 if total_prev_asset > 0 else 0
        total_d1_change_pct = ((total_prev_asset - total_prev2_asset) / total_prev2_asset) * 100 if total_prev2_asset > 0 else 0

        if total_asset == 0:
            st.error("총 자산이 0원입니다.")
            st.stop()

        if "script.google.com" in WEB_APP_URL:
            try: requests.post(WEB_APP_URL, data={"date": now.strftime("%Y-%m-%d"), "asset": int(total_asset)})
            except: pass

        tickers = [p['ticker'] for p in all_stocks] + ["KRW=X", SAMSUNG_TICKER]
        df_hist = yf.download(tickers, period="3y", progress=False)

        st.session_state.total_asset = total_asset
        st.session_state.rebalance_budget = total_asset - sam_amt
        st.session_state.total_today_profit = total_today_profit
        st.session_state.total_daily_return_pct = total_daily_return_pct
        st.session_state.total_d1_change_pct = total_d1_change_pct
        st.session_state.exc_rate = exchange_rate
        
        st.session_state.sam_amt = sam_amt
        st.session_state.sam_price = sam_price
        st.session_state.sam_change = sam_change
        st.session_state.sam_profit = sam_profit_today
        st.session_state.sam_prev_change = sam_prev_change
        st.session_state.sam_avg_price = sam_avg_price
        st.session_state.sam_actual_avg_p = sam_actual_avg_p
        st.session_state.sam_real_p = sam_realized_profit
        st.session_state.sam_unreal_p = sam_unreal_p
        st.session_state.sam_tot_p = sam_tot_p
        st.session_state.sam_principal = sam_principal
        st.session_state.sam_return_pct = sam_return_pct

        st.session_state.stock_data_cache = stock_data_cache
        st.session_state.user_holdings = user_holdings
        st.session_state.input_cash = input_cash
        st.session_state.cat_stats = {
            "US": cat_cur["US"], "US_P": cat_prev["US"], "US_P2": cat_prev2["US"],
            "KR": cat_cur["KR"], "KR_P": cat_prev["KR"], "KR_P2": cat_prev2["KR"],
            "ETF": cat_cur["ETF"], "ETF_P": cat_prev["ETF"], "ETF_P2": cat_prev2["ETF"]
        }
        st.session_state.df_hist = df_hist
        st.session_state.analyzed = True
        st.rerun()

# ==========================================
# 5. 화면 출력부 및 공통 설정
# ==========================================

# 표 너비 및 정렬 공통 환경설정 (글자 씹힘 방지 및 통일감)
SHARED_COL_CONFIG = {
    "실행": st.column_config.TextColumn("실행", width=95),
    "종목": st.column_config.TextColumn("종목", width=120),
    "현재가($)": st.column_config.TextColumn("현재가($)", width=85),
    "현재가(₩)": st.column_config.TextColumn("현재가(₩)", width=95),
    "현재가": st.column_config.TextColumn("현재가", width=95),
    "실제평단가": st.column_config.TextColumn("실제평단가", width=95),
    "D-1": st.column_config.TextColumn("D-1", width=80),
    "등락률": st.column_config.TextColumn("등락률", width=80),
    "오늘수익": st.column_config.TextColumn("오늘수익", width=105),
    "목표비중": st.column_config.TextColumn("목표비중", width=75),
    "실제비중": st.column_config.TextColumn("실제비중", width=75),
    "목표금액": st.column_config.TextColumn("목표금액", width=105),
    "실제금액": st.column_config.TextColumn("실제금액", width=105),
    "목표수량": st.column_config.TextColumn("목표수량", width=75),
    "내보유": st.column_config.TextColumn("내보유", width=75),
    "실현수익": st.column_config.TextColumn("실현수익", width=110),
    "미실현수익": st.column_config.TextColumn("미실현수익", width=110),
    "총수익": st.column_config.TextColumn("총수익", width=110),
    "원금(투입분)": st.column_config.TextColumn("원금(투입분)", width=110),
    "수익률(%)": st.column_config.TextColumn("수익률(%)", width=85),
}

def fmt_pnl(val):
    if val > 0: return f"▲ {val:,.0f}원"
    elif val < 0: return f"▼ {abs(val):,.0f}원"
    return "0원"

def fmt_pct(val):
    if val > 0: return f"▲ {val:.2f}%"
    elif val < 0: return f"▼ {abs(val):.2f}%"
    return "0.00%"

if st.session_state.analyzed:
    # --- 매수/매도 액션 요약을 띄우기 위한 Placeholder ---
    action_placeholder = st.empty()
    st.success(f"**📊 현재 포트폴리오 총 자산:** {st.session_state.total_asset:,.0f}원")
    
    st.write("🔍 **종목 필터링 (아래 리밸런싱 표에만 적용됩니다)**")
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    if col_f1.button("📋 전체 보기", use_container_width=True): st.session_state.filter_by = "전체"
    if col_f2.button("🇰🇷 국장", use_container_width=True): st.session_state.filter_by = "국장"
    if col_f3.button("🌎 미장", use_container_width=True): st.session_state.filter_by = "미장"
    if col_f4.button("🛡️ 현금성(ETF)", use_container_width=True): st.session_state.filter_by = "현금성"
    
    st.write("↕️ **정렬 기준 선택**")
    col_btn1, col_btn2, col_btn3, _ = st.columns([2.5, 2.5, 2.5, 2.5])
    if col_btn1.button("💰 실제금액 내림차순", use_container_width=True): st.session_state.sort_by = "실제금액숫자"
    if col_btn2.button("📈 등락률 내림차순", use_container_width=True): st.session_state.sort_by = "등락률숫자"
    if col_btn3.button("💸 오늘수익 내림차순", use_container_width=True): st.session_state.sort_by = "오늘수익숫자"

    # --- 5-1. 개별 종목표 생성 ---
    stock_rows = []
    pnl_rows = [] 
    actions_needed = [] 
    total_buy_cost = 0  # <--- 필수 변수 선언!
    
    reb_budget = st.session_state.rebalance_budget
    budget_invest = reb_budget * 0.63  
    exc_rate = st.session_state.exc_rate

    sam_change_str = f"▲ {st.session_state.sam_change:.2f}%" if st.session_state.sam_change > 0 else (f"▼ {abs(st.session_state.sam_change):.2f}%" if st.session_state.sam_change < 0 else "-")
    sam_prev_change_str = f"▲ {st.session_state.sam_prev_change:.2f}%" if st.session_state.sam_prev_change > 0 else (f"▼ {abs(st.session_state.sam_prev_change):.2f}%" if st.session_state.sam_prev_change < 0 else "-")
    sam_profit_str = f"▲ {st.session_state.sam_profit:,.0f}원" if st.session_state.sam_profit > 0 else (f"▼ {abs(st.session_state.sam_profit):,.0f}원" if st.session_state.sam_profit < 0 else "-")
    
    sam_actual_ratio_num = (st.session_state.sam_amt / st.session_state.total_asset) if st.session_state.total_asset > 0 else 0.0

    stock_rows.append({
        "실행": "매매불가",
        "종목": get_brand("삼성전자")["name"], "현재가($)": "-", "현재가(₩)": f"{st.session_state.sam_price:,.0f}원", 
        "D-1": sam_prev_change_str, "등락률": sam_change_str, "오늘수익": sam_profit_str,
        "목표비중": "-", "실제비중": f"{sam_actual_ratio_num:.1%}",
        "목표금액": "-", "실제금액": f"{st.session_state.sam_amt:,.0f}원",
        "목표수량": "-", "내보유": str(SAMSUNG_QTY),
        "등락률숫자": st.session_state.sam_change, "실제금액숫자": st.session_state.sam_amt, "오늘수익숫자": st.session_state.sam_profit,
        "목표비중숫자": 0.0, "실제비중숫자": sam_actual_ratio_num, "목표금액숫자": 0.0,
        "카테고리": "국장" 
    })
    
    pnl_rows.append({
        "카테고리": "국장",
        "종목": get_brand("삼성전자")["name"],
        "현재가": f"₩{st.session_state.sam_price:,.0f}",
        "실제평단가": f"₩{st.session_state.sam_actual_avg_p:,.0f}",
        "실현수익": fmt_pnl(st.session_state.sam_real_p),
        "미실현수익": fmt_pnl(st.session_state.sam_unreal_p),
        "총수익": fmt_pnl(st.session_state.sam_tot_p),
        "원금(투입분)": f"{st.session_state.sam_principal:,.0f}원",
        "수익률(%)": fmt_pct(st.session_state.sam_return_pct),
        "수익률숫자": st.session_state.sam_return_pct,
        "real_num": st.session_state.sam_real_p,
        "unreal_num": st.session_state.sam_unreal_p,
        "tot_num": st.session_state.sam_tot_p,
        "prin_num": st.session_state.sam_principal
    })

    for i, p in enumerate(all_stocks):
        cached = st.session_state.stock_data_cache[i]
        price_krw = cached['price_krw']
        price_usd = cached['price_usd']
        my_amt = cached['my_amt']
        change_pct = cached['change_pct']
        prev_change_pct = cached['prev_change_pct']
        today_profit = cached['today_profit']
        my_qty = st.session_state.user_holdings[i]

        if i < 5: 
            exact_target_cost = reb_budget * p['ratio']
            target_ratio_num = p['ratio']
            category = "현금성"
        else: 
            exact_target_cost = budget_invest * p['ratio']
            target_ratio_num = 0.63 * p['ratio']
            category = "미장" if p['country'] == 'US' else "국장"

        display_target_ratio = f"{target_ratio_num:.1%}"

        if price_krw > 0: target_qty = round(exact_target_cost / price_krw)
        else: target_qty = 0
        total_buy_cost += (target_qty * price_krw)
        
        actual_ratio_num = my_amt / st.session_state.total_asset if st.session_state.total_asset > 0 else 0.0
        current_ratio = f"{actual_ratio_num:.1%}"
        
        diff = target_qty - my_qty
        raw_name = p['name'] # 이모티콘 제외된 순수 종목명
        if diff > 0: 
            action = f"{int(diff)}주 매수"
            actions_needed.append(f"**{raw_name}** <span style='color:#2E7D32; font-weight:bold;'>🟢 {int(diff)}주 매수</span>")
        elif diff < 0: 
            action = f"{int(abs(diff))}주 매도"
            actions_needed.append(f"**{raw_name}** <span style='color:#D32F2F; font-weight:bold;'>🔴 {int(abs(diff))}주 매도</span>")
        else: 
            action = "유지"

        price_display = f"${price_usd:,.2f}" if p['country'] == "US" else "-"
        change_str = f"▲ {change_pct:.2f}%" if change_pct > 0 else (f"▼ {abs(change_pct):.2f}%" if change_pct < 0 else "-")
        prev_change_str = f"▲ {prev_change_pct:.2f}%" if prev_change_pct > 0 else (f"▼ {abs(prev_change_pct):.2f}%" if prev_change_pct < 0 else "-")
        profit_str = f"▲ {today_profit:,.0f}원" if today_profit > 0 else (f"▼ {abs(today_profit):,.0f}원" if today_profit < 0 else "-")

        stock_rows.append({
            "실행": action,
            "종목": get_brand(p['name'])["name"], "현재가($)": price_display, "현재가(₩)": f"{price_krw:,.0f}원", 
            "D-1": prev_change_str, "등락률": change_str, "오늘수익": profit_str,
            "목표비중": display_target_ratio, "실제비중": current_ratio,
            "목표금액": f"{exact_target_cost:,.0f}원", "실제금액": f"{my_amt:,.0f}원",
            "목표수량": str(int(target_qty)), "내보유": str(int(my_qty)),
            "등락률숫자": change_pct, "실제금액숫자": my_amt, "오늘수익숫자": today_profit,
            "목표비중숫자": target_ratio_num, "실제비중숫자": actual_ratio_num, "목표금액숫자": exact_target_cost,
            "카테고리": category
        })
        
        if category in ["미장", "현금성"]:
            cur_price_str = f"${price_usd:,.2f}"
            act_avg_usd = cached['actual_avg_p'] / exc_rate if exc_rate > 0 else 0
            act_avg_str = f"${act_avg_usd:,.2f}"
        else:
            cur_price_str = f"₩{price_krw:,.0f}"
            act_avg_str = f"₩{cached['actual_avg_p']:,.0f}"

        pnl_rows.append({
            "카테고리": category,
            "종목": get_brand(p['name'])["name"],
            "현재가": cur_price_str,
            "실제평단가": act_avg_str,
            "실현수익": fmt_pnl(cached['real_p']),
            "미실현수익": fmt_pnl(cached['unreal_p']),
            "총수익": fmt_pnl(cached['tot_p']),
            "원금(투입분)": f"{cached['principal']:,.0f}원",
            "수익률(%)": fmt_pct(cached['return_pct']),
            "수익률숫자": cached['return_pct'],
            "real_num": cached['real_p'],
            "unreal_num": cached['unreal_p'],
            "tot_num": cached['tot_p'],
            "prin_num": cached['principal']
        })

    # --- 최상단 알림(Placeholder) 업데이트 ---
    if actions_needed:
        summary_html = f"""
        <div style='background-color: #FFFDE7; padding: 15px; border-radius: 8px; border: 2px solid #FBC02D; margin-bottom: 20px;'>
            <h5 style='margin-top: 0; color: #F57F17; margin-bottom: 10px;'>🛒 필요 매수/매도 요약</h5>
            <div style='font-size: 15px;'>{' &nbsp;|&nbsp; '.join(actions_needed)}</div>
        </div>
        """
        action_placeholder.markdown(summary_html, unsafe_allow_html=True)
    else:
        summary_html = """
        <div style='background-color: #F1F8E9; padding: 15px; border-radius: 8px; border: 2px solid #66BB6A; margin-bottom: 20px;'>
            <h5 style='margin-top: 0; color: #2E7D32; margin-bottom: 0;'>🟢 매수/매도 신호 없음 (현재 목표 비중 유지중)</h5>
        </div>
        """
        action_placeholder.markdown(summary_html, unsafe_allow_html=True)

    # [리밸런싱 뷰] 데이터프레임
    df_stocks = pd.DataFrame(stock_rows)
    if st.session_state.filter_by != "전체":
        df_stocks = df_stocks[df_stocks['카테고리'] == st.session_state.filter_by]
    
    sum_actual_amt = df_stocks['실제금액숫자'].sum()
    sum_today_profit = df_stocks['오늘수익숫자'].sum()
    sum_target_ratio = df_stocks['목표비중숫자'].sum()
    sum_actual_ratio = df_stocks['실제비중숫자'].sum()
    sum_target_amt = df_stocks['목표금액숫자'].sum()

    prof_str = f"▲ {sum_today_profit:,.0f}원" if sum_today_profit > 0 else (f"▼ {abs(sum_today_profit):,.0f}원" if sum_today_profit < 0 else "-")
    
    summary_row = {
        "실행": "-", "종목": f"📊 [{st.session_state.filter_by}] 요약",
        "현재가($)": "-", "현재가(₩)": "-", "D-1": "-", "등락률": "-",
        "오늘수익": prof_str,
        "목표비중": f"{sum_target_ratio:.1%}",
        "실제비중": f"{sum_actual_ratio:.1%}",
        "목표금액": f"{sum_target_amt:,.0f}원",
        "실제금액": f"{sum_actual_amt:,.0f}원",
        "목표수량": "-", "내보유": "-"
    }

    df_stocks = df_stocks.sort_values(by=st.session_state.sort_by, ascending=False).drop(columns=['등락률숫자', '실제금액숫자', '오늘수익숫자', '목표비중숫자', '실제비중숫자', '목표금액숫자', '카테고리'])
    df_stocks = pd.concat([df_stocks, pd.DataFrame([summary_row])], ignore_index=True)
    
    # [상세 손익 뷰] 카테고리별 정렬 및 요약행 삽입
    cat_summary = {"국장": {"real":0, "unreal":0, "tot":0, "prin":0},
                   "미장": {"real":0, "unreal":0, "tot":0, "prin":0},
                   "현금성": {"real":0, "unreal":0, "tot":0, "prin":0}}
                   
    for row in pnl_rows:
        c = row['카테고리']
        cat_summary[c]["real"] += row["real_num"]
        cat_summary[c]["unreal"] += row["unreal_num"]
        cat_summary[c]["tot"] += row["tot_num"]
        cat_summary[c]["prin"] += row["prin_num"]
        
    combined_pnl_rows = []
    for cat in ["국장", "미장", "현금성"]:
        cat_items = [row for row in pnl_rows if row["카테고리"] == cat]
        cat_items.sort(key=lambda x: x["수익률숫자"], reverse=True)
        
        for item in cat_items:
            del item["수익률숫자"]
            del item["real_num"]
            del item["unreal_num"]
            del item["tot_num"]
            del item["prin_num"]
            combined_pnl_rows.append(item)
            
        s = cat_summary[cat]
        pct = (s["tot"] / s["prin"] * 100) if s["prin"] > 0 else 0
        combined_pnl_rows.append({
            "종목": f"📊 [{cat}] 요약",
            "현재가": "-", "실제평단가": "-",
            "실현수익": fmt_pnl(s['real']),
            "미실현수익": fmt_pnl(s['unreal']),
            "총수익": fmt_pnl(s['tot']),
            "원금(투입분)": f"{s['prin']:,.0f}원",
            "수익률(%)": fmt_pct(pct)
        })
        
    tot_s = {k: sum(cat_summary[cat][k] for cat in ["국장", "미장", "현금성"]) for k in ["real", "unreal", "tot", "prin"]}
    tot_pct = (tot_s["tot"] / tot_s["prin"] * 100) if tot_s["prin"] > 0 else 0
    combined_pnl_rows.append({
        "종목": "📊 전체 자산 총합 요약",
        "현재가": "-", "실제평단가": "-",
        "실현수익": fmt_pnl(tot_s['real']),
        "미실현수익": fmt_pnl(tot_s['unreal']),
        "총수익": fmt_pnl(tot_s['tot']),
        "원금(투입분)": f"{tot_s['prin']:,.0f}원",
        "수익률(%)": fmt_pct(tot_pct)
    })
    
    df_pnl = pd.DataFrame(combined_pnl_rows)
    if '카테고리' in df_pnl.columns:
        df_pnl = df_pnl.drop(columns=['카테고리'])

    # --- 기존 포트폴리오 자산군별 현황 요약표 ---
    tgt_US = reb_budget * 0.63 * 0.75
    tgt_KR_inv = reb_budget * 0.63 * 0.25
    tgt_KR_tot = tgt_KR_inv + st.session_state.sam_amt
    tgt_ETF = reb_budget * 0.16
    tgt_Cash = reb_budget * 0.21
    
    sum_rows = []
    target_data = [
        ("US", "🌎 해외주식 총합", tgt_US),
        ("KR", "🇰🇷 국내주식 총합", tgt_KR_tot),
        ("ETF", "🛡️ 현금성ETF 총합", tgt_ETF)
    ]
    
    for code, label, t_amt in target_data:
        c_cur = st.session_state.cat_stats[code]
        c_prev = st.session_state.cat_stats[code + "_P"]
        c_prev2 = st.session_state.cat_stats[code + "_P2"]
        
        c_prof = c_cur - c_prev
        c_pct = (c_prof / c_prev * 100) if c_prev > 0 else 0
        c_d1_pct = ((c_prev - c_prev2) / c_prev2 * 100) if c_prev2 > 0 else 0

        c_pct_str = f"▲ {c_pct:.2f}%" if c_pct > 0 else (f"▼ {abs(c_pct):.2f}%" if c_pct < 0 else "-")
        c_d1_pct_str = f"▲ {c_d1_pct:.2f}%" if c_d1_pct > 0 else (f"▼ {abs(c_d1_pct):.2f}%" if c_d1_pct < 0 else "-")
        c_prof_str = f"▲ {c_prof:,.0f}원" if c_prof > 0 else (f"▼ {abs(c_prof):,.0f}원" if c_prof < 0 else "-")
        
        sum_rows.append({
            "종목": label, "D-1": c_d1_pct_str, "등락률": c_pct_str, "오늘수익": c_prof_str,
            "목표비중": f"{(t_amt / st.session_state.total_asset):.1%}" if st.session_state.total_asset > 0 else "0%", 
            "실제비중": f"{(c_cur / st.session_state.total_asset):.1%}",
            "목표금액": f"{t_amt:,.0f}원", "실제금액": f"{c_cur:,.0f}원"
        })
    
    sum_rows.append({
        "종목": get_brand("예수금")["name"], "D-1": "-", "등락률": "-", "오늘수익": "-",
        "목표비중": "21.0%", "실제비중": f"{(st.session_state.input_cash / st.session_state.total_asset):.1%}",
        "목표금액": f"{tgt_Cash:,.0f}원", "실제금액": f"{st.session_state.input_cash:,.0f}원"
    })

    tot_pct_daily = st.session_state.total_daily_return_pct
    tot_d1_pct = st.session_state.total_d1_change_pct
    tot_prof_daily = st.session_state.total_today_profit
    
    tot_pct_str = f"▲ {tot_pct_daily:.2f}%" if tot_pct_daily > 0 else (f"▼ {abs(tot_pct_daily):.2f}%" if tot_pct_daily < 0 else "-")
    tot_d1_pct_str = f"▲ {tot_d1_pct:.2f}%" if tot_d1_pct > 0 else (f"▼ {abs(tot_d1_pct):.2f}%" if tot_d1_pct < 0 else "-")
    tot_profit_str = f"▲ {tot_prof_daily:,.0f}원" if tot_prof_daily > 0 else (f"▼ {abs(tot_prof_daily):,.0f}원" if tot_prof_daily < 0 else "-")
    
    sum_rows.append({
        "종목": "📊 포트폴리오 총합", "D-1": tot_d1_pct_str, "등락률": tot_pct_str, "오늘수익": tot_profit_str,
        "목표비중": "100.0%", "실제비중": "100.0%", "목표금액": f"{st.session_state.total_asset:,.0f}원", "실제금액": f"{st.session_state.total_asset:,.0f}원"
    })
    df_summary = pd.DataFrame(sum_rows)

    # --- 표 렌더링 스타일 ---
    def style_change_color(val):
        val_str = str(val)
        if '▲' in val_str: return 'background-color: #CCFFCC; color: #2E7D32; font-weight: bold;'
        elif '▼' in val_str: return 'background-color: #FFD1DC; color: #C2185B; font-weight: bold;'
        return ''

    def style_d1_color(val):
        val_str = str(val)
        if '▲' in val_str: return 'color: #2E7D32; font-weight: bold;'
        elif '▼' in val_str: return 'color: #C2185B; font-weight: bold;'
        return ''

    def style_text_color(val):
        if '매수' in str(val): return 'color: #2E7D32; font-weight: bold;'  # Green
        elif '매도' in str(val): return 'color: #D32F2F; font-weight: bold;' # Red
        return 'color: #757575;'

    def style_profit_val(val):
        val_str = str(val)
        if '▲' in val_str: return 'color: #2E7D32; font-weight: bold;'
        elif '▼' in val_str: return 'color: #C2185B; font-weight: bold;'
        return ''

    def style_stock_dataframe(row):
        if '총합 요약' in str(row.get('종목', '')):
            return ['background-color: #FFF59D; color: #212121; font-weight: bold; font-size: 15px;'] * len(row)
        elif '요약' in str(row.get('종목', '')):
            return ['background-color: #EEEEEE; font-weight: bold;'] * len(row)
        return [''] * len(row)

    def style_summary_dataframe(row):
        col_name = '종목' if '종목' in row else '구분'
        bg_color = 'white'
        if '해외' in row[col_name] or '미장' in row[col_name]: bg_color = '#FCE4EC'
        elif '국내' in row[col_name] or '국장' in row[col_name]: bg_color = '#E3F2FD'
        elif 'ETF' in row[col_name] or '현금성' in row[col_name]: bg_color = '#FFF9C4'
        elif '예수금' in row[col_name]: bg_color = '#F1F8E9' 
        elif '전체' in row[col_name] or '총합' in row[col_name]: bg_color = '#EEEEEE'
        return [f'background-color: {bg_color}'] * len(row)

    st.subheader(f"📑 개별 종목 상세 리밸런싱 현황 (현재 필터: {st.session_state.filter_by})")
    st.dataframe(
        df_stocks.style.apply(style_stock_dataframe, axis=1)
                 .map(style_text_color, subset=['실행'])
                 .map(style_change_color, subset=['등락률', '오늘수익'])
                 .map(style_d1_color, subset=['D-1'])
                 .set_properties(**{'text-align': 'center'}),
        column_order=["실행", "종목", "현재가($)", "현재가(₩)", "D-1", "등락률", "오늘수익", "목표비중", "실제비중", "목표금액", "실제금액", "목표수량", "내보유"],
        column_config=SHARED_COL_CONFIG,
        hide_index=True, use_container_width=False, height=650 
    )
    
    st.write("---")
    st.subheader("📋 포트폴리오 자산군별 현황 요약 (이론적 목표비중 기준)")
    st.dataframe(
        df_summary.style.apply(style_summary_dataframe, axis=1)
                  .map(style_change_color, subset=['등락률', '오늘수익'])
                  .map(style_d1_color, subset=['D-1'])
                  .set_properties(**{'text-align': 'center'}),
        column_order=["종목", "D-1", "등락률", "오늘수익", "목표비중", "실제비중", "목표금액", "실제금액"],
        column_config=SHARED_COL_CONFIG,
        hide_index=True, use_container_width=False, height=250 
    )

    st.write("---")
    st.subheader("💰 종목별 손익 및 실제 평단가 현황 (카테고리별 수익률 정렬)")
    st.caption("※ **실제평단가** = 평균단가 - (실현수익 / 보유수량) | **원금** = 현재가치 - 총수익")
    st.dataframe(
        df_pnl.style.apply(style_stock_dataframe, axis=1)
              .map(style_profit_val, subset=['실현수익', '미실현수익', '총수익', '수익률(%)'])
              .set_properties(**{'text-align': 'center'}),
        column_order=["종목", "현재가", "실제평단가", "실현수익", "미실현수익", "총수익", "원금(투입분)", "수익률(%)"],
        column_config=SHARED_COL_CONFIG,
        hide_index=True, use_container_width=False, height=750 
    )

    # ==========================================
    # 6. 전문가 레이아웃 차트 구역
    # ==========================================
    st.write("---")
    col_chart, col_pie = st.columns([6, 4])
    
    with col_chart:
        st.subheader("📉 자산 성장 시뮬레이션 (3년)")
        tab1, tab2, tab3, tab4 = st.tabs(["🕯️ 총자산 캔들형", "📊 층별 누적 영역형", "🇰🇷 국장 캔들형", "🌎 미장 캔들형"])
        
        try:
            df_hist = st.session_state.df_hist
            first_days_month = [group.index[0] for _, group in df_hist.groupby([df_hist.index.year, df_hist.index.month])]
            first_days_year = [group.index[0] for _, group in df_hist.groupby(df_hist.index.year)]

            def create_candle_fig(O_series, H_series, L_series, C_series, name, real_time_val):
                if len(C_series) > 0:
                    C_series.iloc[-1] = real_time_val
                    if H_series.iloc[-1] < real_time_val: H_series.iloc[-1] = real_time_val
                    if L_series.iloc[-1] > real_time_val: L_series.iloc[-1] = real_time_val

                ath_val = H_series.max()
                ath_date = H_series.idxmax()
                last_date = C_series.index[-1]
                zoom_start = last_date - pd.Timedelta(days=90)
                
                mask = (C_series.index >= zoom_start)
                if mask.any():
                    low_3m_val = L_series[mask].min()
                    low_3m_date = L_series[mask].idxmin()
                else:
                    low_3m_val = L_series.min()
                    low_3m_date = L_series.idxmin()

                curr_val = C_series.iloc[-1]
                curr_date = C_series.index[-1]

                fig = go.Figure(data=[go.Candlestick(x=C_series.index,
                                open=O_series.values, high=H_series.values,
                                low=L_series.values, close=C_series.values, name=name)])
                
                fig.add_hline(y=ath_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig.add_hline(y=low_3m_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig.add_hline(y=curr_val, line_dash="dash", line_color="red", opacity=0.7)

                fig.add_annotation(x=ath_date, y=ath_val, text=f"📅 {ath_date.strftime('%y년 %m월 %d일')}<br>🚩 전고점: {ath_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=-45, bgcolor="white", bordercolor="gray")
                fig.add_annotation(x=low_3m_date, y=low_3m_val, text=f"📅 {low_3m_date.strftime('%y년 %m월 %d일')}<br>📉 3개월 저점: {low_3m_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=45, bgcolor="white", bordercolor="gray")
                fig.add_annotation(x=curr_date, y=curr_val, text=f"🔴 현재가: {curr_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=70, ay=0, bgcolor="white", bordercolor="red", xanchor="left")

                fig.update_yaxes(tickformat=",.0f", autorange=True, fixedrange=False) 
                fig.update_xaxes(tickformat="%Y년 %m월 %d일", hoverformat="%Y년 %m월 %d일", rangeslider_visible=True, rangebreaks=[dict(bounds=["sat", "mon"])]) 
                fig.update_layout(xaxis_range=[zoom_start, last_date + pd.Timedelta(days=15)], margin=dict(l=0, r=0, t=30, b=0), height=500)
                
                for d in first_days_month: 
                    if d in first_days_year:
                        fig.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                    else:
                        fig.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                
                return fig

            def get_series(col):
                s = pd.Series(st.session_state.input_cash, index=df_hist.index) 
                s += df_hist[col][SAMSUNG_TICKER].ffill().bfill() * SAMSUNG_QTY
                for i, p in enumerate(all_stocks):
                    qty = st.session_state.user_holdings[i]
                    if qty > 0:
                        tkr = p['ticker']
                        if p['country'] == 'US': s += df_hist[col][tkr].ffill().bfill() * df_hist[col]['KRW=X'].ffill().bfill() * qty
                        else: s += df_hist[col][tkr].ffill().bfill() * qty
                return s

            hist_O = get_series('Open')
            hist_H = get_series('High')
            hist_L = get_series('Low')
            hist_C = get_series('Close')

            def get_market_series(col, market):
                s = pd.Series(0, index=df_hist.index)
                if market == 'KR':
                    s += df_hist[col][SAMSUNG_TICKER].ffill().bfill() * SAMSUNG_QTY
                for i, p in enumerate(all_stocks):
                    qty = st.session_state.user_holdings[i]
                    if qty > 0 and p['country'] == market:
                        tkr = p['ticker']
                        if market == 'US': s += df_hist[col][tkr].ffill().bfill() * df_hist[col]['KRW=X'].ffill().bfill() * qty
                        else: s += df_hist[col][tkr].ffill().bfill() * qty
                return s

            kr_O = get_market_series('Open', 'KR')
            kr_H = get_market_series('High', 'KR')
            kr_L = get_market_series('Low', 'KR')
            kr_C = get_market_series('Close', 'KR')

            us_O = get_market_series('Open', 'US')
            us_H = get_market_series('High', 'US')
            us_L = get_market_series('Low', 'US')
            us_C = get_market_series('Close', 'US')

            with tab1:
                fig_total = create_candle_fig(hist_O, hist_H, hist_L, hist_C, '총자산 캔들', st.session_state.total_asset)
                st.plotly_chart(fig_total, use_container_width=True)

            with tab2:
                s_cash = pd.Series(st.session_state.input_cash, index=df_hist.index) 
                s_etf = pd.Series(0, index=df_hist.index)
                s_us = pd.Series(0, index=df_hist.index)
                s_kr = pd.Series(0, index=df_hist.index)
                s_kr += df_hist['Close'][SAMSUNG_TICKER].ffill().bfill() * SAMSUNG_QTY
                
                for i, p in enumerate(all_stocks):
                    qty = st.session_state.user_holdings[i]
                    if qty > 0:
                        tkr = p['ticker']
                        if p['country'] == 'US': val = df_hist['Close'][tkr].ffill().bfill() * df_hist['Close']['KRW=X'].ffill().bfill() * qty
                        else: val = df_hist['Close'][tkr].ffill().bfill() * qty
                        if i < 5: s_etf += val
                        elif p['country'] == 'US': s_us += val
                        else: s_kr += val

                real_time_total = st.session_state.total_asset
                if len(hist_C) > 0: hist_C.iloc[-1] = real_time_total

                ath_val = hist_H.max()
                ath_date = hist_H.idxmax()
                last_date = df_hist.index[-1]
                zoom_start = last_date - pd.Timedelta(days=90)
                
                mask = (df_hist.index >= zoom_start)
                if mask.any():
                    low_3m_val = hist_L[mask].min()
                    low_3m_date = hist_L[mask].idxmin()
                else:
                    low_3m_val = hist_L.min()
                    low_3m_date = hist_L.idxmin()

                curr_val = hist_C.iloc[-1]
                curr_date = hist_C.index[-1]

                fig_area = go.Figure()
                fig_area.add_trace(go.Scatter(x=df_hist.index, y=s_cash, mode='none', fill='tozeroy', name='💵 예수금', stackgroup='one', fillcolor='#85BB65'))
                fig_area.add_trace(go.Scatter(x=df_hist.index, y=s_etf, mode='none', fill='tonexty', name='🛡️ 현금성ETF', stackgroup='one', fillcolor='#FFD54F'))
                fig_area.add_trace(go.Scatter(x=df_hist.index, y=s_us, mode='none', fill='tonexty', name='🌎 해외주식', stackgroup='one', fillcolor='#F06292'))
                fig_area.add_trace(go.Scatter(x=df_hist.index, y=s_kr, mode='none', fill='tonexty', name='🇰🇷 국내주식', stackgroup='one', fillcolor='#64B5F6'))
                fig_area.add_trace(go.Scatter(x=df_hist.index, y=hist_C, mode='lines', name='📈 총자산 흐름', line=dict(color='#222222', width=2)))
                
                fig_area.add_hline(y=ath_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig_area.add_hline(y=low_3m_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig_area.add_hline(y=curr_val, line_dash="dash", line_color="red", opacity=0.7)

                fig_area.add_annotation(x=ath_date, y=ath_val, text=f"📅 {ath_date.strftime('%y년 %m월 %d일')}<br>🚩 전고점: {ath_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=-45, bgcolor="white", bordercolor="gray")
                fig_area.add_annotation(x=low_3m_date, y=low_3m_val, text=f"📅 {low_3m_date.strftime('%y년 %m월 %d일')}<br>📉 3개월 저점: {low_3m_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=45, bgcolor="white", bordercolor="gray")
                fig_area.add_annotation(x=curr_date, y=curr_val, text=f"🔴 현재가: {curr_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=70, ay=0, bgcolor="white", bordercolor="red", xanchor="left")

                fig_area.update_yaxes(tickformat=",.0f", autorange=True, fixedrange=False)
                fig_area.update_xaxes(tickformat="%Y년 %m월 %d일", hoverformat="%Y년 %m월 %d일", rangeslider_visible=True, rangebreaks=[dict(bounds=["sat", "mon"])])
                fig_area.update_layout(xaxis_range=[zoom_start, last_date + pd.Timedelta(days=15)], margin=dict(l=0, r=0, t=30, b=0), height=500, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                
                for d in first_days_month: 
                    if d in first_days_year:
                        fig_area.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                    else:
                        fig_area.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                st.plotly_chart(fig_area, use_container_width=True)

            with tab3:
                kr_real_time_val = st.session_state.cat_stats["KR"]
                fig_kr = create_candle_fig(kr_O, kr_H, kr_L, kr_C, '국장 캔들', kr_real_time_val)
                st.plotly_chart(fig_kr, use_container_width=True)

            with tab4:
                us_real_time_val = st.session_state.cat_stats["US"] + st.session_state.cat_stats["ETF"]
                fig_us = create_candle_fig(us_O, us_H, us_L, us_C, '미장 캔들', us_real_time_val)
                st.plotly_chart(fig_us, use_container_width=True)

        except Exception as e:
            st.warning("차트 데이터를 불러오는 데 일시적인 문제가 발생했습니다.")

    with col_pie:
        st.subheader("🍕 자산 구성 비율")
        tab_pie_current, tab_pie_target = st.tabs(["📊 현재 비율", "🎯 목표 비율"])
        
        try:
            custom_colors = {v["name"]: v["color"] for v in brand_meta.values()}
            
            # --- 현재 비율 ---
            with tab_pie_current:
                pie_data_cur = []
                if st.session_state.sam_amt > 0: 
                    pie_data_cur.append({"종목": get_brand("삼성전자")["name"], "금액": st.session_state.sam_amt})
                for i, p in enumerate(all_stocks):
                    if st.session_state.stock_data_cache[i]['my_amt'] > 0:
                        pie_data_cur.append({"종목": get_brand(p['name'])["name"], "금액": st.session_state.stock_data_cache[i]['my_amt']})
                if st.session_state.input_cash > 0: 
                    pie_data_cur.append({"종목": get_brand("예수금")["name"], "금액": st.session_state.input_cash})

                df_pie_cur = pd.DataFrame(pie_data_cur)
                fig_pie_cur = px.pie(df_pie_cur, values='금액', names='종목', color='종목', color_discrete_map=custom_colors, hole=0.4)
                fig_pie_cur.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie_cur.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=500, showlegend=False) 
                st.plotly_chart(fig_pie_cur, use_container_width=True)
            
            # --- 목표 비율 ---
            with tab_pie_target:
                pie_data_tgt = []
                
                if st.session_state.sam_amt > 0: 
                    pie_data_tgt.append({"종목": get_brand("삼성전자")["name"], "금액": st.session_state.sam_amt})
                
                for i, p in enumerate(all_stocks):
                    if i < 5:
                        tgt_amt = reb_budget * p['ratio']
                    else:
                        tgt_amt = budget_invest * p['ratio']
                    if tgt_amt > 0:
                        pie_data_tgt.append({"종목": get_brand(p['name'])["name"], "금액": tgt_amt})
                
                tgt_cash = reb_budget * 0.21
                if tgt_cash > 0:
                    pie_data_tgt.append({"종목": get_brand("예수금")["name"], "금액": tgt_cash})
                
                df_pie_tgt = pd.DataFrame(pie_data_tgt)
                fig_pie_tgt = px.pie(df_pie_tgt, values='금액', names='종목', color='종목', color_discrete_map=custom_colors, hole=0.4)
                fig_pie_tgt.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie_tgt.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=500, showlegend=False) 
                st.plotly_chart(fig_pie_tgt, use_container_width=True)
                
        except Exception as e:
            st.warning("비율 데이터를 표시할 수 없습니다.")
