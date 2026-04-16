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
    {"name": "VTV",  "ticker": "VTV",  "ratio": 0.04, "country": "US"},
    {"name": "TLT",  "ticker": "TLT",  "ratio": 0.025, "country": "US"},
    {"name": "IEI",  "ticker": "IEI",  "ratio": 0.015, "country": "US"},
    {"name": "SCHD", "ticker": "SCHD", "ratio": 0.04, "country": "US"},
]

invest_portfolio = [
    {"name": "TSM",        "ticker": "TSM",    "ratio": 0.25, "country": "US"},
    {"name": "NVDA",       "ticker": "NVDA",   "ratio": 0.08, "country": "US"},
    {"name": "TSLA",       "ticker": "TSLA",   "ratio": 0.06, "country": "US"},
    {"name": "MSFT",       "ticker": "MSFT",   "ratio": 0.065, "country": "US"},
    {"name": "AAPL",       "ticker": "AAPL",   "ratio": 0.065, "country": "US"},
    {"name": "GOOGL",      "ticker": "GOOGL",  "ratio": 0.10, "country": "US"},
    {"name": "AMD",        "ticker": "AMD",    "ratio": 0.065, "country": "US"},
    {"name": "AMZN",       "ticker": "AMZN",   "ratio": 0.065, "country": "US"},
    {"name": "SK하이닉스", "ticker": "000660.KS", "ratio": 0.20, "country": "KR"},
    {"name": "현대차",     "ticker": "005380.KS", "ratio": 0.05, "country": "KR"},
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
    try: return yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
    except: return 1400.0

@st.cache_data(ttl=3600)
def get_exchange_trend():
    try:
        df = yf.download("KRW=X", period="1mo", progress=False)
        if isinstance(df.columns, pd.MultiIndex): return df['Close']['KRW=X']
        return df['Close']
    except: return None

@st.cache_data(ttl=1800)
def get_portfolio_news():
    tickers = ["NVDA", "AAPL", "TSLA", "TSM", "MSFT", "GOOGL"]
    news_list = []
    for t in tickers:
        try:
            news = yf.Ticker(t).news
            if isinstance(news, list):
                for n in news[:2]:
                    pub_time = n.get('providerPublishTime', n.get('publishTime', 0))
                    if n.get('title') and n.get('link'):
                        news_list.append({"title": f"[{t}] {n['title']}", "link": n['link'], "publisher": n.get('publisher', 'News'), "time": pub_time})
        except: pass
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list[:10]

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
# 3. 최상단 UI (입력 패널 ➔ 전광판 헤더)
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널")

st.subheader("⚙️ 자산 및 수량 세팅")
params = st.query_params
try: default_cash = int(params.get("cash", "10000000"))
except: default_cash = 10000000
default_holdings = params.get("holdings", "")

input_cash = st.number_input("💵 현재 계좌에 있는 현금(예수금) 총액 (원화)", min_value=0, value=default_cash, step=100000, format="%d")
st.caption(f"**입력 순서 (총 15개, 삼성전자 제외):** {' → '.join(all_names)}")
holdings_input = st.text_input("🔢 종목별 수량 (띄어쓰기로 구분)", value=default_holdings, placeholder="예: 10 5 3 0 10 50 15 20 5 10 5 8 10 200 50")
execute_btn = st.button("분석 실행 및 시트에 기록 🚀", type="primary", use_container_width=True)

st.write("---")

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
weekdays = ["월", "화", "수", "목", "금", "토", "일"]
date_str = f"{now.strftime('%Y년 %m월 %d일')} ({weekdays[now.weekday()]})"
time_str = now.strftime("%p %I:%M").replace("AM", "오전").replace("PM", "오후")
exc_rate = get_current_exchange_rate()

head_col1, head_col2, head_col3 = st.columns(3)
with head_col1: st.info(f"**📅 오늘 날짜**\n### {date_str}")
with head_col2: st.info(f"**⏰ 현재 시간 (KST)**\n### {time_str}")
with head_col3: 
    st.info(f"**💵 실시간 환율 (KRW/USD)**\n### {exc_rate:,.1f}원")
    trend_df = get_exchange_trend()
    if trend_df is not None and not trend_df.empty:
        fig_spark = go.Figure(go.Scatter(x=trend_df.index, y=trend_df.values, mode='lines', line=dict(color='#2E7D32', width=3)))
        fig_spark.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=40, xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_spark, use_container_width=True, config={'displayModeBar': False})

news_data = get_portfolio_news()
with st.expander("📰 내 포트폴리오 글로벌 주요 뉴스 (최신 10건)", expanded=False):
    if news_data:
        for item in news_data: st.markdown(f"- [{item['title']}]({item['link']}) *(출처: {item['publisher']})*")
    else: st.write("일시적인 API 지연으로 현재 뉴스를 불러올 수 없습니다.")

st.write("---")

# ==========================================
# 4. 데이터 수집 엔진
# ==========================================
if execute_btn:
    st.query_params["cash"] = str(input_cash)
    st.query_params["holdings"] = holdings_input
    
    try:
        if holdings_input.strip() == "": user_holdings = [0] * len(all_stocks)
        else: user_holdings = list(map(int, holdings_input.split()))
        if len(user_holdings) < len(all_stocks): user_holdings += [0] * (len(all_stocks) - len(user_holdings))
    except ValueError:
        st.error("숫자와 띄어쓰기만 입력해주세요!")
        st.stop()

    with st.spinner('실시간 시세 및 3년치 글로벌 차트 로딩 중... (약 15초 소요)'):
        try: exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except: exchange_rate = 1400 
        
        current_stock_assets = 0
        total_today_profit = 0
        total_prev_asset = input_cash 
        total_prev2_asset = input_cash 
        stock_data_cache = [] 
        
        cat_cur = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev2 = {"US": 0, "KR": 0, "ETF": 0}

        sam_price, sam_change, sam_prev, sam_prev_change, sam_d2 = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        sam_amt = sam_price * SAMSUNG_QTY
        sam_profit = sam_amt - (sam_prev * SAMSUNG_QTY)
        current_stock_assets += sam_amt
        total_today_profit += sam_profit
        total_prev_asset += (sam_prev * SAMSUNG_QTY)
        total_prev2_asset += (sam_d2 * SAMSUNG_QTY)
        cat_cur["KR"] += sam_amt
        cat_prev["KR"] += (sam_prev * SAMSUNG_QTY)
        cat_prev2["KR"] += (sam_d2 * SAMSUNG_QTY)

        for i, p in enumerate(all_stocks):
            price, change_pct, prev_close, prev_change_pct, d2_close = get_real_price_and_change(p['ticker'], p['country'])
            if p['country'] == "US":
                price_krw = price * exc_rate
                price_usd = price
                prev_amt_krw = prev_close * exc_rate * user_holdings[i]
                prev2_amt_krw = d2_close * exc_rate * user_holdings[i]
            else:
                price_krw = price
                price_usd = 0
                prev_amt_krw = prev_close * user_holdings[i]
                prev2_amt_krw = d2_close * user_holdings[i]
            
            my_qty = user_holdings[i]
            my_amt = my_qty * price_krw
            today_profit = my_amt - prev_amt_krw
            
            current_stock_assets += my_amt
            total_today_profit += today_profit
            total_prev_asset += prev_amt_krw
            total_prev2_asset += prev2_amt_krw
            
            if i < 5:
                cat_cur["ETF"] += my_amt
                cat_prev["ETF"] += prev_amt_krw
                cat_prev2["ETF"] += prev2_amt_krw
            elif p['country'] == 'US':
                cat_cur["US"] += my_amt
                cat_prev["US"] += prev_amt_krw
                cat_prev2["US"] += prev2_amt_krw
            else:
                cat_cur["KR"] += my_amt
                cat_prev["KR"] += prev_amt_krw
                cat_prev2["KR"] += prev2_amt_krw
            
            stock_data_cache.append({
                "price_krw": price_krw, "price_usd": price_usd, "my_amt": my_amt, 
                "change_pct": change_pct, "today_profit": today_profit, "prev_change_pct": prev_change_pct
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
        st.session_state.sam_amt = sam_amt
        st.session_state.sam_price = sam_price
        st.session_state.sam_change = sam_change
        st.session_state.sam_profit = sam_profit
        st.session_state.sam_prev_change = sam_prev_change
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
# 5. 화면 출력부 (표 분리, D-1 열 추가, UI개선)
# ==========================================
if st.session_state.analyzed:
    st.success(f"**📊 현재 포트폴리오 총 자산:** {st.session_state.total_asset:,.0f}원")
    
    st.write("↕️ **정렬 기준 선택 (클릭 시 즉각 정렬)**")
    col_btn1, col_btn2, col_btn3, _ = st.columns([2.5, 2.5, 2.5, 2.5])
    if col_btn1.button("💰 실제금액 내림차순", use_container_width=True): st.session_state.sort_by = "실제금액숫자"
    if col_btn2.button("📈 등락률 내림차순", use_container_width=True): st.session_state.sort_by = "등락률숫자"
    if col_btn3.button("💸 오늘수익 내림차순", use_container_width=True): st.session_state.sort_by = "오늘수익숫자"

    # --- 5-1. 개별 종목표 생성 ---
    stock_rows = []
    total_buy_cost = 0 
    budget_invest = st.session_state.rebalance_budget * 0.63  

    sam_change_str = f"▲ {st.session_state.sam_change:.2f}%" if st.session_state.sam_change > 0 else (f"▼ {abs(st.session_state.sam_change):.2f}%" if st.session_state.sam_change < 0 else "-")
    sam_prev_change_str = f"▲ {st.session_state.sam_prev_change:.2f}%" if st.session_state.sam_prev_change > 0 else (f"▼ {abs(st.session_state.sam_prev_change):.2f}%" if st.session_state.sam_prev_change < 0 else "-")
    sam_profit_str = f"▲ {st.session_state.sam_profit:,.0f}원" if st.session_state.sam_profit > 0 else (f"▼ {abs(st.session_state.sam_profit):,.0f}원" if st.session_state.sam_profit < 0 else "-")
    
    stock_rows.append({
        "종목": get_brand("삼성전자")["name"], "현재가($)": "-", "현재가(₩)": f"{st.session_state.sam_price:,.0f}원", 
        "D-1": sam_prev_change_str, "등락률": sam_change_str, "오늘수익": sam_profit_str,
        "목표비중": "-", "실제비중": f"{(st.session_state.sam_amt/st.session_state.total_asset):.1%}",
        "목표금액": "-", "실제금액": f"{st.session_state.sam_amt:,.0f}원",
        "목표수량": "-", "내보유": str(SAMSUNG_QTY), "실행": "🔒 매매불가",
        "등락률숫자": st.session_state.sam_change, "실제금액숫자": st.session_state.sam_amt, "오늘수익숫자": st.session_state.sam_profit
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
            target_amt = st.session_state.rebalance_budget * p['ratio']
            display_target_ratio = f"{p['ratio']:.1%}"
        else: 
            target_amt = budget_invest * p['ratio']
            display_target_ratio = f"{(0.63 * p['ratio']):.1%}"

        if price_krw > 0: target_qty = round(target_amt / price_krw)
        else: target_qty = 0
        actual_target_cost = target_qty * price_krw
        total_buy_cost += actual_target_cost
        
        current_ratio = f"{(my_amt / st.session_state.total_asset):.1%}" if st.session_state.total_asset > 0 else "0.0%"
        diff = target_qty - my_qty
        if diff > 0: action = f"🔴 {int(diff)}주 매수"
        elif diff < 0: action = f"🔵 {int(abs(diff))}주 매도"
        else: action = "🟢 유지"

        price_display = f"${price_usd:,.2f}" if p['country'] == "US" else "-"
        change_str = f"▲ {change_pct:.2f}%" if change_pct > 0 else (f"▼ {abs(change_pct):.2f}%" if change_pct < 0 else "-")
        prev_change_str = f"▲ {prev_change_pct:.2f}%" if prev_change_pct > 0 else (f"▼ {abs(prev_change_pct):.2f}%" if prev_change_pct < 0 else "-")
        profit_str = f"▲ {today_profit:,.0f}원" if today_profit > 0 else (f"▼ {abs(today_profit):,.0f}원" if today_profit < 0 else "-")

        stock_rows.append({
            "종목": get_brand(p['name'])["name"], "현재가($)": price_display, "현재가(₩)": f"{price_krw:,.0f}원", 
            "D-1": prev_change_str, "등락률": change_str, "오늘수익": profit_str,
            "목표비중": display_target_ratio, "실제비중": current_ratio,
            "목표금액": f"{actual_target_cost:,.0f}원", "실제금액": f"{my_amt:,.0f}원",
            "목표수량": str(int(target_qty)), "내보유": str(int(my_qty)), "실행": action,
            "등락률숫자": change_pct, "실제금액숫자": my_amt, "오늘수익숫자": today_profit
        })

    df_stocks = pd.DataFrame(stock_rows).sort_values(by=st.session_state.sort_by, ascending=False).drop(columns=['등락률숫자', '실제금액숫자', '오늘수익숫자'])

    # --- 5-2. 요약표 생성 ---
    sum_rows = []
    for code, label in [("US", "🌎 해외주식 총합"), ("KR", "🇰🇷 국내주식 총합"), ("ETF", "🛡️ 현금성ETF 총합")]:
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
            "종목": label, "현재가($)": "-", "현재가(₩)": "-", "D-1": c_d1_pct_str, "등락률": c_pct_str, "오늘수익": c_prof_str,
            "목표비중": "-", "실제비중": f"{(c_cur / st.session_state.total_asset):.1%}",
            "목표금액": "-", "실제금액": f"{c_cur:,.0f}원", "목표수량": "-", "내보유": "-", "실행": "-"
        })
    
    remaining_cash = st.session_state.rebalance_budget - total_buy_cost
    sum_rows.append({
        "종목": get_brand("예수금")["name"], "현재가($)": "-", "현재가(₩)": "-", "D-1": "-", "등락률": "-", "오늘수익": "-",
        "목표비중": "21.0%", "실제비중": f"{(st.session_state.input_cash / st.session_state.total_asset):.1%}",
        "목표금액": f"{remaining_cash:,.0f}원", "실제금액": f"{st.session_state.input_cash:,.0f}원",
        "목표수량": "-", "내보유": "-", "실행": "-"
    })

    tot_pct = st.session_state.total_daily_return_pct
    tot_d1_pct = st.session_state.total_d1_change_pct
    tot_prof = st.session_state.total_today_profit
    
    tot_pct_str = f"▲ {tot_pct:.2f}%" if tot_pct > 0 else (f"▼ {abs(tot_pct):.2f}%" if tot_pct < 0 else "-")
    tot_d1_pct_str = f"▲ {tot_d1_pct:.2f}%" if tot_d1_pct > 0 else (f"▼ {abs(tot_d1_pct):.2f}%" if tot_d1_pct < 0 else "-")
    tot_profit_str = f"▲ {tot_prof:,.0f}원" if tot_prof > 0 else (f"▼ {abs(tot_prof):,.0f}원" if tot_prof < 0 else "-")
    
    sum_rows.append({
        "종목": "📊 포트폴리오 총합", "현재가($)": "-", "현재가(₩)": "-", "D-1": tot_d1_pct_str, "등락률": tot_pct_str, "오늘수익": tot_profit_str,
        "목표비중": "100.0%", "실제비중": "100.0%", "목표금액": "-", "실제금액": f"{st.session_state.total_asset:,.0f}원",
        "목표수량": "-", "내보유": "-", "실행": "-"
    })
    
    df_summary = pd.DataFrame(sum_rows)

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
        color = 'black'
        if '매수' in str(val): color = '#D32F2F'
        elif '매도' in str(val): color = '#1976D2'
        return f'color: {color}; font-weight: bold;'

    def style_summary_dataframe(row):
        bg_color = 'white'
        if '해외주식' in row['종목']: bg_color = '#FCE4EC'
        elif '국내주식' in row['종목']: bg_color = '#E3F2FD'
        elif '현금성ETF' in row['종목']: bg_color = '#FFF9C4'
        elif '예수금' in row['종목']: bg_color = '#F1F8E9' 
        elif '포트폴리오 총합' in row['종목']: bg_color = '#EEEEEE'
        return [f'background-color: {bg_color}'] * len(row)

    st.subheader("📑 개별 종목 상세 현황")
    st.dataframe(
        df_stocks.style.map(style_text_color, subset=['실행'])
                 .map(style_change_color, subset=['등락률', '오늘수익'])
                 .map(style_d1_color, subset=['D-1'])
                 .set_properties(**{'text-align': 'center'}),
        column_order=["종목", "현재가($)", "현재가(₩)", "D-1", "등락률", "오늘수익", "목표비중", "실제비중", "목표금액", "실제금액", "목표수량", "내보유", "실행"],
        column_config={"종목": st.column_config.TextColumn("종목", width=160)},
        hide_index=True, use_container_width=False, height=650 
    )

    st.write("---")
    st.subheader("📋 포트폴리오 요약표")
    st.caption("※ 실제비중은 전체 포트폴리오(100%) 대비 차지하는 정확한 비율입니다.")
    st.dataframe(
        df_summary.style.apply(style_summary_dataframe, axis=1)
                  .map(style_change_color, subset=['등락률', '오늘수익'])
                  .map(style_d1_color, subset=['D-1'])
                  .set_properties(**{'text-align': 'center'}),
        column_order=["종목", "현재가($)", "현재가(₩)", "D-1", "등락률", "오늘수익", "목표비중", "실제비중", "목표금액", "실제금액", "목표수량", "내보유", "실행"],
        column_config={"종목": st.column_config.TextColumn("종목", width=160)},
        hide_index=True, use_container_width=False, height=250 
    )

    # ==========================================
    # 6. 전문가 레이아웃 차트 구역
    # ==========================================
    st.write("---")
    col_chart, col_pie = st.columns([6, 4])
    
    with col_chart:
        st.subheader("📉 자산 성장 시뮬레이션 (3년)")
        tab1, tab2 = st.tabs(["🕯️ 총자산 캔들형", "📊 층별 누적 영역형"])
        
        try:
            df_hist = st.session_state.df_hist
            
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

            real_time_total = st.session_state.total_asset
            if len(hist_C) > 0:
                hist_C.iloc[-1] = real_time_total
                if hist_H.iloc[-1] < real_time_total: hist_H.iloc[-1] = real_time_total
                if hist_L.iloc[-1] > real_time_total: hist_L.iloc[-1] = real_time_total

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

            ath_val = hist_H.max()
            ath_date = hist_H.idxmax()
            last_date = df_hist.index[-1]
            zoom_start = last_date - pd.Timedelta(days=90)
            
            mask = (df_hist.index >= zoom_start)
            if mask.any():
                low_3m_val = hist_L[mask].min()
                low_3m_date = hist_L[mask].idxmin()
                max_y = hist_H[mask].max() * 1.10
            else:
                low_3m_val = hist_L.min()
                low_3m_date = hist_L.idxmin()
                max_y = hist_H.max() * 1.10

            min_y = max(0, low_3m_val * 0.98) 
            curr_val = hist_C.iloc[-1]
            curr_date = hist_C.index[-1]

            # ★ 월 구분선과 연 구분선 분리!
            first_days_month = [group.index[0] for _, group in df_hist.groupby([df_hist.index.year, df_hist.index.month])]
            first_days_year = [group.index[0] for _, group in df_hist.groupby(df_hist.index.year)]

            with tab1:
                fig_candle = go.Figure(data=[go.Candlestick(x=hist_C.index,
                                open=hist_O.values, high=hist_H.values,
                                low=hist_L.values, close=hist_C.values, name='총자산 캔들')])
                
                fig_candle.add_hline(y=ath_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig_candle.add_hline(y=low_3m_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig_candle.add_hline(y=curr_val, line_dash="dash", line_color="red", opacity=0.7)

                fig_candle.add_annotation(x=ath_date, y=ath_val, text=f"📅 {ath_date.strftime('%y년 %m월 %d일')}<br>🚩 전고점: {ath_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=-45, bgcolor="white", bordercolor="gray")
                fig_candle.add_annotation(x=low_3m_date, y=low_3m_val, text=f"📅 {low_3m_date.strftime('%y년 %m월 %d일')}<br>📉 3개월 저점: {low_3m_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=45, bgcolor="white", bordercolor="gray")
                fig_candle.add_annotation(x=curr_date, y=curr_val, text=f"🔴 현재가: {curr_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=-70, ay=0, bgcolor="white", bordercolor="red")

                fig_candle.update_yaxes(tickformat=",.0f")
                fig_candle.update_xaxes(tickformat="%Y년 %m월 %d일", hoverformat="%Y년 %m월 %d일", rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])]) 
                fig_candle.update_layout(xaxis_range=[zoom_start, last_date], yaxis_range=[min_y, max_y], margin=dict(l=0, r=0, t=30, b=0), height=500)
                
                # ★ 연 구분선은 수직 굵은 검정 실선, 월 구분선은 옅은 점선
                for d in first_days_month: 
                    if d in first_days_year:
                        fig_candle.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                    else:
                        fig_candle.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                st.plotly_chart(fig_candle, use_container_width=True)

            with tab2:
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
                fig_area.add_annotation(x=curr_date, y=curr_val, text=f"🔴 현재가: {curr_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=-70, ay=0, bgcolor="white", bordercolor="red")

                fig_area.update_yaxes(tickformat=",.0f")
                fig_area.update_xaxes(tickformat="%Y년 %m월 %d일", hoverformat="%Y년 %m월 %d일", rangebreaks=[dict(bounds=["sat", "mon"])])
                fig_area.update_layout(xaxis_range=[zoom_start, last_date], yaxis_range=[min_y, max_y], margin=dict(l=0, r=0, t=30, b=0), height=500, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                
                # ★ 연 구분선은 수직 굵은 검정 실선, 월 구분선은 옅은 점선
                for d in first_days_month: 
                    if d in first_days_year:
                        fig_area.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                    else:
                        fig_area.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                st.plotly_chart(fig_area, use_container_width=True)

        except Exception as e:
            st.warning("차트 데이터를 불러오는 데 일시적인 문제가 발생했습니다.")

    with col_pie:
        st.subheader("🍕 현재 자산 구성 비율")
        try:
            pie_data = []
            if st.session_state.sam_amt > 0: 
                pie_data.append({"종목": get_brand("삼성전자")["name"], "금액": st.session_state.sam_amt})
            for i, p in enumerate(all_stocks):
                if st.session_state.stock_data_cache[i]['my_amt'] > 0:
                    pie_data.append({"종목": get_brand(p['name'])["name"], "금액": st.session_state.stock_data_cache[i]['my_amt']})
            if st.session_state.input_cash > 0: 
                pie_data.append({"종목": get_brand("예수금")["name"], "금액": st.session_state.input_cash})

            df_pie = pd.DataFrame(pie_data)
            custom_colors = {v["name"]: v["color"] for v in brand_meta.values()}

            fig_pie = px.pie(df_pie, values='금액', names='종목', color='종목', color_discrete_map=custom_colors, hole=0.4)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=530, showlegend=False) 
            st.plotly_chart(fig_pie, use_container_width=True)
        except Exception as e:
            st.warning("비율 데이터를 표시할 수 없습니다.")
