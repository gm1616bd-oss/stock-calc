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
if "total_asset" not in st.session_state: st.session_state.total_asset = 0

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

# --- 전광판 레이아웃 4단으로 수정 ---
head_col1, head_col2, head_col3, head_col4 = st.columns(4)
with head_col1: st.info(f"**📅 오늘 날짜**\n### {date_str}")
with head_col2: st.info(f"**💰 현재 총자산**\n### {st.session_state.total_asset:,.0f}원")
with head_col3: st.info(f"**⏰ 현재 시간 (KST)**\n### {time_str}")
with head_col4: 
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
            
            if i < 5: p_type = "ETF"
            elif p['country'] == 'US': p_type = "US"
            else: p_type = "KR"

            cat_cur[p_type] += my_amt
            cat_prev[p_type] += prev_amt_krw
            cat_prev2[p_type] += prev2_amt_krw
            
            stock_data_cache.append({
                "price_krw": price_krw, "price_usd": price_usd, "my_amt": my_amt, 
                "change_pct": change_pct, "today_profit": today_profit, "prev_change_pct": prev_change_pct,
                "ratio": p['ratio'], "type": p_type
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
        df_5m = yf.download(tickers, period="2d", interval="5m", progress=False)

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
            "US": [cat_cur["US"], cat_prev["US"], cat_prev2["US"]],
            "KR": [cat_cur["KR"], cat_prev["KR"], cat_prev2["KR"]],
            "ETF": [cat_cur["ETF"], cat_prev["ETF"], cat_prev2["ETF"]]
        }
        st.session_state.df_hist = df_hist
        st.session_state.df_5m = df_5m
        st.session_state.analyzed = True
        st.rerun()

# ==========================================
# 5. 화면 출력부
# ==========================================
if st.session_state.analyzed:
    st.success(f"**📊 현재 포트폴리오 총 자산:** {st.session_state.total_asset:,.0f}원")
    
    # 필터 버튼 추가
    st.write("🔎 **시장별 필터링**")
    f_c1, f_c2, f_c3, f_c4, _ = st.columns([1, 1, 1, 1, 6])
    if f_c1.button("🌐 전체", use_container_width=True): st.session_state.view_filter = "전체"
    if f_c2.button("🇰🇷 국장", use_container_width=True): st.session_state.view_filter = "KR"
    if f_c3.button("🇺🇸 미장", use_container_width=True): st.session_state.view_filter = "US"
    if f_c4.button("🛡️ 현금성", use_container_width=True): st.session_state.view_filter = "ETF"

    st.write("↕️ **정렬 기준 선택 (클릭 시 즉각 정렬)**")
    col_btn1, col_btn2, col_btn3, _ = st.columns([2.5, 2.5, 2.5, 2.5])
    if col_btn1.button("💰 실제금액 내림차순", use_container_width=True): st.session_state.sort_by = "실제금액숫자"
    if col_btn2.button("📈 등락률 내림차순", use_container_width=True): st.session_state.sort_by = "등락률숫자"
    if col_btn3.button("💸 오늘수익 내림차순", use_container_width=True): st.session_state.sort_by = "오늘수익숫자"

    stock_rows = []
    budget_invest = st.session_state.rebalance_budget * 0.63  

    # 삼성전자 (원본 로직 그대로)
    if st.session_state.view_filter in ["전체", "KR"]:
        stock_rows.append({
            "종목": get_brand("삼성전자")["name"], "현재가(₩)": f"{st.session_state.sam_price:,.0f}원", 
            "등락률": f"{st.session_state.sam_change:+.2f}%", "오늘수익": f"{st.session_state.sam_profit:+,.0f}원",
            "실제비중": f"{(st.session_state.sam_amt/st.session_state.total_asset):.1%}",
            "실제금액": f"{st.session_state.sam_amt:,.0f}원", "실행": "🔒 고정",
            "등락률숫자": st.session_state.sam_change, "실제금액숫자": st.session_state.sam_amt, "오늘수익숫자": st.session_state.sam_profit
        })

    for i, p in enumerate(all_stocks):
        cached = st.session_state.stock_data_cache[i]
        if st.session_state.view_filter != "전체" and cached['type'] != st.session_state.view_filter: continue

        my_qty = st.session_state.user_holdings[i]
        target_amt = st.session_state.rebalance_budget * cached['ratio'] if i < 5 else budget_invest * cached['ratio']
        target_qty = round(target_amt / cached['price_krw']) if cached['price_krw'] > 0 else 0
        diff = target_qty - my_qty
        action = f"🔴 {int(diff)}주 매수" if diff > 0 else (f"🔵 {int(abs(diff))}주 매도" if diff < 0 else "🟢 유지")

        stock_rows.append({
            "종목": get_brand(p['name'])["name"], "현재가(₩)": f"{cached['price_krw']:,.0f}원", 
            "등락률": f"{cached['change_pct']:+.2f}%", "오늘수익": f"{cached['today_profit']:+,.0f}원",
            "실제비중": f"{(cached['my_amt']/st.session_state.total_asset):.1%}",
            "실제금액": f"{cached['my_amt']:,.0f}원", "실행": action,
            "등락률숫자": cached['change_pct'], "실제금액숫자": cached['my_amt'], "오늘수익숫자": cached['today_profit']
        })

    df_main = pd.DataFrame(stock_rows).sort_values(by=st.session_state.sort_by, ascending=False)
    
    # 필터 합계 행 계산
    f_sum_p = df_main['오늘수익숫자'].sum()
    f_sum_a = df_main['실제금액숫자'].sum()
    summary_row = pd.DataFrame([{"종목": "✨ 선택 분류 합계", "오늘수익": f"{f_sum_p:+,.0f}원", "실제비중": f"{(f_sum_a/st.session_state.total_asset):.1%}", "실제금액": f"{f_sum_a:,.0f}원"}])
    df_final = pd.concat([df_main, summary_row], ignore_index=True)

    def color_v(val):
        c = '#2E7D32' if '+' in str(val) or '매수' in str(val) else ('#C2185B' if '-' in str(val) or '매도' in str(val) else 'black')
        return f'color: {c}; font-weight: bold;'

    st.dataframe(df_final.style.apply(lambda r: ['background-color: #F8F9FA' if r['종목'] == '✨ 선택 분류 합계' else '' for _ in r], axis=1).map(color_v, subset=['등락률','오늘수익','실행']),
                 column_order=["종목","현재가(₩)","등락률","오늘수익","실제비중","실제금액","실행"],
                 column_config={"종목": st.column_config.TextColumn("종목", width=160)},
                 hide_index=True, use_container_width=True, height=600)

    # --- 요약표 ---
    st.write("---")
    st.subheader("📋 전체 포트폴리오 요약")
    sum_rows = []
    for cd, lb in [("US","🌎 해외주식 총합"), ("KR","🇰🇷 국내주식 총합"), ("ETF","🛡️ 현금성ETF 총합")]:
        v = st.session_state.cat_stats[cd]; p = v[0]-v[1]
        sum_rows.append({"종목":lb, "등락률":f"{(p/v[1]*100):+.2f}%" if v[1]>0 else "0%", "오늘수익":f"{p:+,.0f}원", "실제비중":f"{v[0]/st.session_state.total_asset:.1%}", "실제금액":f"{v[0]:,.0f}원"})
    sum_rows.append({"종목":"📊 포트폴리오 총합", "등락률":f"{st.session_state.total_daily_return_pct:+.2f}%", "오늘수익":f"{st.session_state.total_today_profit:+,.0f}원", "실제비중":"100.0%", "실제금액":f"{st.session_state.total_asset:,.0f}원"})
    st.dataframe(pd.DataFrame(sum_rows).style.apply(lambda r: ['background-color: #EEEEEE' if '총합' in r['종목'] else '' for _ in r], axis=1).map(color_v, subset=['등락률','오늘수익']),
                 hide_index=True, use_container_width=True)

    # ==========================================
    # 6. 차트 센터
    # ==========================================
    st.write("---")
    st.subheader("📊 차트 분석 센터")
    
    def calc_ohlc(df, t_list):
        res = pd.DataFrame(0.0, index=df.index, columns=['Open','High','Low','Close'])
        for t in t_list:
            qty = SAMSUNG_QTY if t == SAMSUNG_TICKER else st.session_state.user_holdings[all_tickers.index(t)]
            r = exc_rate if (".KS" not in t and t != SAMSUNG_TICKER) else 1
            for col in res.columns: res[col] += df[col][t].ffill().bfill() * qty * r
        return res + st.session_state.input_cash

    tab1, tab2, tab3, tab4 = st.tabs(["🕒 2일 5분봉", "🇰🇷 국장 일봉", "🇺🇸 미장 일봉", "📈 전체 누적 영역"])

    def add_lines(fig, ohlc_df, title):
        ath = ohlc_df['High'].max(); ath_d = ohlc_df['High'].idxmax()
        low_3m = ohlc_df['Low'].tail(60).min(); low_d = ohlc_df['Low'].tail(60).idxmin()
        curr = st.session_state.total_asset if title=="전체" else ohlc_df['Close'].iloc[-1]
        fig.add_hline(y=ath, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_hline(y=low_3m, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_hline(y=curr, line_dash="dot", line_color="red", opacity=0.8)
        fig.add_annotation(x=ath_d, y=ath, text=f"🚩 전고점", showarrow=True)
        # 연/월 구분선 추가 (검정 실선)
        f_m = [g.index[0] for _, g in ohlc_df.groupby([ohlc_df.index.year, ohlc_df.index.month])]
        f_y = [g.index[0] for _, g in ohlc_df.groupby(ohlc_df.index.year)]
        for d in f_m:
            if d in f_y: fig.add_vline(x=d, line_dash="solid", line_color="black", line_width=2)
            else: fig.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)")
        fig.update_yaxes(tickformat=",.0f")
        return fig

    with tab1:
        w5 = calc_ohlc(st.session_state.df_5m, all_tickers[:-1])
        st.plotly_chart(add_lines(go.Figure(data=[go.Candlestick(x=w5.index, open=w5['Open'], high=w5['High'], low=w5['Low'], close=w5['Close'])]), w5, "전체"), use_container_width=True)
    with tab2:
        kr_tkrs = [SAMSUNG_TICKER] + [p['ticker'] for p in all_stocks if p['country']=='KR']
        w_kr = calc_ohlc(st.session_state.df_hist, kr_tkrs)
        st.plotly_chart(add_lines(go.Figure(data=[go.Candlestick(x=w_kr.index, open=w_kr['Open'], high=w_kr['High'], low=w_kr['Low'], close=w_kr['Close'])]), w_kr, "국장"), use_container_width=True)
    with tab3:
        us_tkrs = [p['ticker'] for p in all_stocks if p['country']=='US']
        w_us = calc_ohlc(st.session_state.df_hist, us_tkrs)
        st.plotly_chart(add_lines(go.Figure(data=[go.Candlestick(x=w_us.index, open=w_us['Open'], high=w_us['High'], low=w_us['Low'], close=w_us['Close'])]), w_us, "미장"), use_container_width=True)
    with tab4:
        dfh = st.session_state.df_hist; idx = dfh.index; s_ca = pd.Series(st.session_state.input_cash, index=idx)
        s_et = calc_ohlc(dfh, [p['ticker'] for p in fixed_portfolio])['Close'] - st.session_state.input_cash
        s_u = calc_ohlc(dfh, [p['ticker'] for p in invest_portfolio if p['country']=='US'])['Close'] - st.session_state.input_cash
        s_k = calc_ohlc(dfh, [SAMSUNG_TICKER]+[p['ticker'] for p in invest_portfolio if p['country']=='KR'])['Close'] - st.session_state.input_cash
        fa = go.Figure()
        fa.add_trace(go.Scatter(x=idx, y=s_ca, mode='none', fill='tozeroy', name='💵 예수금', stackgroup='one', fillcolor='#85BB65'))
        fa.add_trace(go.Scatter(x=idx, y=s_et, mode='none', fill='tonexty', name='🛡️ 현금성', stackgroup='one', fillcolor='#FFD54F'))
        fa.add_trace(go.Scatter(x=idx, y=s_u, mode='none', fill='tonexty', name='🌎 미장', stackgroup='one', fillcolor='#F06292'))
        fa.add_trace(go.Scatter(x=idx, y=s_k, mode='none', fill='tonexty', name='🇰🇷 국장', stackgroup='one', fillcolor='#64B5F6'))
        st.plotly_chart(add_lines(fa, calc_ohlc(dfh, all_tickers[:-1]), "전체"), use_container_width=True)
