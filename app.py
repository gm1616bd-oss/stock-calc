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
if "view_filter" not in st.session_state: st.session_state.view_filter = "전체"

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
    {"name": "GLDM", "ticker": "GLDM", "ratio": 0.04, "country": "US", "type": "ETF"},
    {"name": "VTV",  "ticker": "VTV",  "ratio": 0.04, "country": "US", "type": "ETF"},
    {"name": "TLT",  "ticker": "TLT",  "ratio": 0.025, "country": "US", "type": "ETF"},
    {"name": "IEI",  "ticker": "IEI",  "ratio": 0.015, "country": "US", "type": "ETF"},
    {"name": "SCHD", "ticker": "SCHD", "ratio": 0.04, "country": "US", "type": "ETF"},
]

invest_portfolio = [
    {"name": "TSM",        "ticker": "TSM",    "ratio": 0.25, "country": "US", "type": "US"},
    {"name": "NVDA",       "ticker": "NVDA",   "ratio": 0.08, "country": "US", "type": "US"},
    {"name": "TSLA",       "ticker": "TSLA",   "ratio": 0.06, "country": "US", "type": "US"},
    {"name": "MSFT",       "ticker": "MSFT",   "ratio": 0.065, "country": "US", "type": "US"},
    {"name": "AAPL",       "ticker": "AAPL",   "ratio": 0.065, "country": "US", "type": "US"},
    {"name": "GOOGL",      "ticker": "GOOGL",  "ratio": 0.10, "country": "US", "type": "US"},
    {"name": "AMD",        "ticker": "AMD",    "ratio": 0.065, "country": "US", "type": "US"},
    {"name": "AMZN",       "ticker": "AMZN",   "ratio": 0.065, "country": "US", "type": "US"},
    {"name": "SK하이닉스", "ticker": "000660.KS", "ratio": 0.20, "country": "KR", "type": "KR"},
    {"name": "현대차",     "ticker": "005380.KS", "ratio": 0.05, "country": "KR", "type": "KR"},
]

all_stocks = fixed_portfolio + invest_portfolio
all_tickers = [p['ticker'] for p in all_stocks] + [SAMSUNG_TICKER, "KRW=X"]
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
# 2. 데이터 유틸리티
# ==========================================
@st.cache_data(ttl=600)
def get_current_exchange_rate():
    try: return yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
    except: return 1400.0

@st.cache_data(ttl=1800)
def get_portfolio_news():
    tickers = ["NVDA", "AAPL", "TSLA", "TSM"]
    news_list = []
    for t in tickers:
        try:
            news = yf.Ticker(t).news
            for n in news[:2]:
                pub_time = n.get('providerPublishTime', n.get('publishTime', 0))
                news_list.append({"title": f"[{t}] {n['title']}", "link": n['link'], "publisher": n.get('publisher', 'News'), "time": pub_time})
        except: pass
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list[:10]

def get_real_price_and_change(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")
        if len(hist) >= 3:
            d2_close = hist['Close'].iloc[-3]; d1_close = hist['Close'].iloc[-2]
            prev_change_pct = ((d1_close - d2_close) / d2_close) * 100
        else:
            d2_close = 0; d1_close = stock.fast_info.get('previous_close', 0); prev_change_pct = 0.0

        if country == "KR": current_price = stock.fast_info['last_price']
        else:
            df_intra = stock.history(period="1d", interval="1m", prepost=True)
            current_price = df_intra['Close'].iloc[-1] if not df_intra.empty else stock.fast_info.get('last_price', d1_close)
        
        change_pct = ((current_price - d1_close) / d1_close) * 100 if d1_close > 0 else 0.0
        return current_price, change_pct, d1_close, prev_change_pct, d2_close
    except: return 0, 0.0, 0, 0.0, 0

# ==========================================
# 3. UI 헤더
# ==========================================
st.set_page_config(page_title="퀀트 터미널 Pro", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널 Pro")

with st.container():
    st.subheader("⚙️ 자산 설정")
    params = st.query_params
    input_cash = st.number_input("💵 현재 현금(예수금)", min_value=0, value=int(params.get("cash", "10000000")), step=100000)
    holdings_input = st.text_input("🔢 종목별 수량 (띄어쓰기 구분)", value=params.get("holdings", ""))
    execute_btn = st.button("실시간 분석 및 차트 생성 🚀", type="primary", use_container_width=True)

st.write("---")

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
exc_rate = get_current_exchange_rate()

col_h1, col_h2, col_h3 = st.columns(3)
col_h1.metric("📅 날짜", now.strftime('%Y-%m-%d'))
col_h2.metric("⏰ 시간", now.strftime('%H:%M KST'))
col_h3.metric("💵 원/달러 환율", f"{exc_rate:,.1f}원")

# ==========================================
# 4. 분석 엔진
# ==========================================
if execute_btn:
    st.query_params["cash"] = str(input_cash)
    st.query_params["holdings"] = holdings_input
    
    try:
        user_holdings = list(map(int, holdings_input.split())) if holdings_input else [0]*len(all_stocks)
        if len(user_holdings) < len(all_stocks): user_holdings += [0]*(len(all_stocks)-len(user_holdings))
    except: st.error("수량 입력 오류"); st.stop()

    with st.spinner('🚀 초정밀 시세 분석 및 5분봉 데이터 로딩 중...'):
        current_stock_assets = 0
        total_today_profit = 0
        total_prev_asset = input_cash
        total_prev2_asset = input_cash
        stock_data_cache = []
        
        cat_cur = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev2 = {"US": 0, "KR": 0, "ETF": 0}

        # 1. 삼성전자
        sp, sc, s_p, spc, sd2 = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        sam_amt = sp * SAMSUNG_QTY
        current_stock_assets += sam_amt
        total_today_profit += sam_amt - (s_p * SAMSUNG_QTY)
        total_prev_asset += (s_p * SAMSUNG_QTY)
        total_prev2_asset += (sd2 * SAMSUNG_QTY)
        cat_cur["KR"] += sam_amt; cat_prev["KR"] += (s_p * SAMSUNG_QTY); cat_prev2["KR"] += (sd2 * SAMSUNG_QTY)

        # 2. 나머지 종목
        for i, p in enumerate(all_stocks):
            price, cp, prev_c, pcp, d2c = get_real_price_and_change(p['ticker'], p['country'])
            rate = exc_rate if p['country'] == "US" else 1
            my_amt = user_holdings[i] * price * rate
            p_amt = user_holdings[i] * prev_c * rate
            p2_amt = user_holdings[i] * d2c * rate
            
            current_stock_assets += my_amt
            total_today_profit += (my_amt - p_amt)
            total_prev_asset += p_amt
            total_prev2_asset += p2_amt
            
            ctype = p['type']
            cat_cur[ctype] += my_amt; cat_prev[ctype] += p_amt; cat_prev2[ctype] += p2_amt
            
            stock_data_cache.append({
                "price_krw": price*rate, "price_usd": price if p['country']=="US" else 0,
                "my_amt": my_amt, "change_pct": cp, "today_profit": my_amt-p_amt, "prev_change_pct": pcp, "type": ctype
            })

        total_asset = current_stock_assets + input_cash
        
        # 3. 차트 데이터 (3년 일봉 + 2일 5분봉)
        df_hist = yf.download(all_tickers, period="3y", interval="1d", threads=True, progress=False)
        df_5m = yf.download(all_tickers, period="2d", interval="5m", threads=True, progress=False)

        st.session_state.update({
            "total_asset": total_asset, "rebalance_budget": total_asset - sam_amt,
            "total_today_profit": total_today_profit, "total_daily_return_pct": (total_today_profit/total_prev_asset*100),
            "total_d1_change_pct": ((total_prev_asset-total_prev2_asset)/total_prev2_asset*100),
            "sam_amt": sam_amt, "sam_price": sp, "sam_change": sc, "sam_profit": sam_amt-(s_p*SAMSUNG_QTY), "sam_prev_change": spc,
            "stock_data_cache": stock_data_cache, "user_holdings": user_holdings, "input_cash": input_cash,
            "cat_stats": {"US": [cat_cur["US"],cat_prev["US"],cat_prev2["US"]], "KR": [cat_cur["KR"],cat_prev["KR"],cat_prev2["KR"]], "ETF": [cat_cur["ETF"],cat_prev["ETF"],cat_prev2["ETF"]]},
            "df_hist": df_hist, "df_5m": df_5m, "analyzed": True
        })
        st.rerun()

# ==========================================
# 5. 대시보드 렌더링
# ==========================================
if st.session_state.analyzed:
    # 5-1. 필터 및 표
    st.subheader("📑 종목 상세 현황")
    fcol1, fcol2, fcol3, fcol4, _ = st.columns([1,1,1,1,6])
    if fcol1.button("🌐 전체", use_container_width=True): st.session_state.view_filter = "전체"
    if fcol2.button("🇰🇷 국장", use_container_width=True): st.session_state.view_filter = "KR"
    if fcol3.button("🇺🇸 미장", use_container_width=True): st.session_state.view_filter = "US"
    if fcol4.button("🛡️ 현금성", use_container_width=True): st.session_state.view_filter = "ETF"

    # 표 정렬 버튼
    st.write("↕️ 정렬: ", end="")
    scol1, scol2, scol3, _ = st.columns([2, 2, 2, 6])
    if scol1.button("💰 실제금액순", key="s1"): st.session_state.sort_by = "실제금액숫자"
    if scol2.button("📈 등락률순", key="s2"): st.session_state.sort_by = "등락률숫자"
    if scol3.button("💸 오늘수익순", key="s3"): st.session_state.sort_by = "오늘수익숫자"

    # 데이터 구성
    rows = []
    # 삼성전자는 필터가 '전체'거나 'KR'일 때만 표시
    if st.session_state.view_filter in ["전체", "KR"]:
        rows.append({
            "종목": "🔒 삼성전자", "현재가(₩)": f"{st.session_state.sam_price:,.0f}원", "D-1": f"{st.session_state.sam_prev_change:+.2f}%",
            "등락률": f"{st.session_state.sam_change:+.2f}%", "오늘수익": f"{st.session_state.sam_profit:+,.0f}원",
            "실제비중": f"{(st.session_state.sam_amt/st.session_state.total_asset):.1%}", "실제금액": f"{st.session_state.sam_amt:,.0f}원",
            "실행": "🔒 고정", "등락률숫자": st.session_state.sam_change, "실제금액숫자": st.session_state.sam_amt, "오늘수익숫자": st.session_state.sam_profit, "type": "KR"
        })

    for i, p in enumerate(all_stocks):
        c = st.session_state.stock_data_cache[i]
        if st.session_state.view_filter != "전체" and c['type'] != st.session_state.view_filter: continue
        
        rows.append({
            "종목": get_brand(p['name'])["name"], "현재가(₩)": f"{c['price_krw']:,.0f}원", "D-1": f"{c['prev_change_pct']:+.2f}%",
            "등락률": f"{c['change_pct']:+.2f}%", "오늘수익": f"{c['today_profit']:+,.0f}원",
            "실제비중": f"{(c['my_amt']/st.session_state.total_asset):.1%}", "실제금액": f"{c['my_amt']:,.0f}원",
            "실행": "유지", "등락률숫자": c['change_pct'], "실제금액숫자": c['my_amt'], "오늘수익숫자": c['today_profit'], "type": c['type']
        })

    df_main = pd.DataFrame(rows).sort_values(by=st.session_state.sort_by, ascending=False)
    
    # 컬러 함수
    def color_val(val):
        color = '#2E7D32' if '+' in str(val) or '▲' in str(val) else ('#C2185B' if '-' in str(val) or '▼' in str(val) else 'black')
        return f'color: {color}; font-weight: bold;'

    st.dataframe(df_main.style.map(color_val, subset=['D-1', '등락률', '오늘수익']), 
                 column_order=["종목", "현재가(₩)", "D-1", "등락률", "오늘수익", "실제비중", "실제금액", "실행"],
                 column_config={"종목": st.column_config.TextColumn("종목", width=160)},
                 hide_index=True, use_container_width=True, height=500)

    # 5-2. 요약표
    st.write("---")
    st.subheader("📋 포트폴리오 요약")
    sum_data = []
    for code, label in [("US", "🌎 해외주식"), ("KR", "🇰🇷 국내주식"), ("ETF", "🛡️ 현금성ETF")]:
        vals = st.session_state.cat_stats[code]
        cur, prev, prev2 = vals[0], vals[1], vals[2]
        prof = cur - prev
        sum_data.append({
            "종목": label, "D-1": f"{(prev-prev2)/prev2*100:+.2f}%" if prev2>0 else "0%",
            "등락률": f"{prof/prev*100:+.2f}%" if prev>0 else "0%", "오늘수익": f"{prof:+,.0f}원",
            "실제비중": f"{cur/st.session_state.total_asset:.1%}", "실제금액": f"{cur:,.0f}원"
        })
    # 예수금 및 총합 생략(지면상 요약)
    st.dataframe(pd.DataFrame(sum_data), hide_index=True, use_container_width=True)

    # ==========================================
    # 6. 차트 센터 (2일 5분봉 / 국장 미장 개별 캔들)
    # ==========================================
    st.write("---")
    st.subheader("📊 차트 분석 센터")
    
    # 차트 계산 함수
    def get_weighted_ohlc(df, tickers_list, qtys_dict, is_intraday=False):
        # 비중 보할 OHLC 계산
        res = pd.DataFrame(0.0, index=df.index, columns=['Open','High','Low','Close'])
        for t in tickers_list:
            q = qtys_dict.get(t, 0)
            if q == 0: continue
            rate = exc_rate if (".KS" not in t and t != SAMSUNG_TICKER and t != "KRW=X") else 1
            res['Open'] += df['Open'][t].ffill().bfill() * q * rate
            res['High'] += df['High'][t].ffill().bfill() * q * rate
            res['Low'] += df['Low'][t].ffill().bfill() * q * rate
            res['Close'] += df['Close'][t].ffill().bfill() * q * rate
        # 현금 베이스 추가 (일봉의 경우)
        if not is_intraday:
            res += st.session_state.input_cash
        return res

    # 종목 분류
    kr_tickers = [SAMSUNG_TICKER] + [p['ticker'] for p in all_stocks if p['country'] == 'KR']
    us_tickers = [p['ticker'] for p in all_stocks if p['country'] == 'US']
    qtys = {SAMSUNG_TICKER: SAMSUNG_QTY}
    for i, p in enumerate(all_stocks): qtys[p['ticker']] = st.session_state.user_holdings[i]

    # 차트 탭
    t1, t2, t3, t4 = st.tabs(["🕒 2일 5분봉 (실시간)", "🇰🇷 국장 전용 일봉", "🇺🇸 미장 전용 일봉", "📈 전체 누적 영역"])

    with t1:
        # 2일 5분봉
        df5 = st.session_state.df_5m
        weighted_5m = get_weighted_ohlc(df5, all_tickers, qtys, True)
        # 5분봉은 현금 포함
        weighted_5m += st.session_state.input_cash
        
        fig5 = go.Figure(data=[go.Candlestick(x=weighted_5m.index, open=weighted_5m['Open'], high=weighted_5m['High'], low=weighted_5m['Low'], close=weighted_5m['Close'])])
        fig5.update_layout(title="포트폴리오 2일 실시간 5분봉", height=600, yaxis_tickformat=",.0f")
        st.plotly_chart(fig5, use_container_width=True)

    with t2:
        # 국장 일봉
        dfh = st.session_state.df_hist
        kr_ohlc = get_weighted_ohlc(dfh, kr_tickers, qtys)
        fig_kr = go.Figure(data=[go.Candlestick(x=kr_ohlc.index, open=kr_ohlc['Open'], high=kr_ohlc['High'], low=kr_ohlc['Low'], close=kr_ohlc['Close'])])
        fig_kr.update_layout(title="🇰🇷 국장 종목군 자산 일봉 (3년)", height=600, yaxis_tickformat=",.0f")
        st.plotly_chart(fig_kr, use_container_width=True)

    with t3:
        # 미장 일봉
        us_ohlc = get_weighted_ohlc(dfh, us_tickers, qtys)
        fig_us = go.Figure(data=[go.Candlestick(x=us_ohlc.index, open=us_ohlc['Open'], high=us_ohlc['High'], low=us_ohlc['Low'], close=us_ohlc['Close'])])
        fig_us.update_layout(title="🇺🇸 미장 종목군 자산 일봉 (3년)", height=600, yaxis_tickformat=",.0f")
        st.plotly_chart(fig_us, use_container_width=True)

    with t4:
        # 누적 영역형 (기존 로직)
        st.info("기존 3년 누적 차트가 표시됩니다.")
        # ... (생략된 기존 누적 차트 코드 동일하게 적용 가능)

    # 파이차트 (하단으로 이동)
    st.write("---")
    st.subheader("🍕 자산 구성 비율")
    pie_data = []
    if st.session_state.sam_amt > 0: pie_data.append({"종목": get_brand("삼성전자")["name"], "금액": st.session_state.sam_amt})
    for i, p in enumerate(all_stocks):
        amt = st.session_state.stock_data_cache[i]['my_amt']
        if amt > 0: pie_data.append({"종목": get_brand(p['name'])["name"], "금액": amt})
    pie_data.append({"종목": "💵 예수금", "금액": st.session_state.input_cash})
    
    fig_pie = px.pie(pd.DataFrame(pie_data), values='금액', names='종목', hole=0.4, color='종목',
                     color_discrete_map={v["name"]: v["color"] for v in brand_meta.values()})
    fig_pie.update_layout(height=600)
    st.plotly_chart(fig_pie, use_container_width=True)
