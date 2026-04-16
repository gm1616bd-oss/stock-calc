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
# 🔑 구글 시트 연결 설정 (사용자님 링크로 변경하세요!)
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
    except: return 1420.0

@st.cache_data(ttl=3600)
def get_exchange_trend():
    try:
        df = yf.download("KRW=X", period="1mo", progress=False)
        return df['Close']
    except: return None

@st.cache_data(ttl=1800)
def get_portfolio_news():
    tickers = ["NVDA", "AAPL", "TSLA", "TSM"]
    news_list = []
    for t in tickers:
        try:
            n_data = yf.Ticker(t).news
            for n in n_data[:2]:
                pub_time = n.get('providerPublishTime', n.get('publishTime', 0))
                news_list.append({"title": f"[{t}] {n['title']}", "link": n['link'], "time": pub_time})
        except: pass
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list[:10]

def get_real_price_and_change(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        d1_close = stock.fast_info.get('previous_close', 0)
        if country == "KR": current_price = stock.fast_info['last_price']
        else:
            df_intra = stock.history(period="1d", interval="1m", prepost=True)
            current_price = df_intra['Close'].iloc[-1] if not df_intra.empty else stock.fast_info.get('last_price', d1_close)
        change_pct = ((current_price - d1_close) / d1_close) * 100 if d1_close > 0 else 0.0
        return current_price, change_pct, d1_close
    except: return 0, 0.0, 0

# ==========================================
# 3. UI 구성
# ==========================================
st.set_page_config(page_title="퀀트 터미널 Pro", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널 Pro")

with st.container():
    st.subheader("⚙️ 자산 설정")
    params = st.query_params
    input_cash = st.number_input("💵 현재 예수금(원화)", min_value=0, value=int(params.get("cash", "10000000")), step=100000)
    holdings_input = st.text_input("🔢 보유 수량 (띄어쓰기 구분, 15종목)", value=params.get("holdings", ""))
    execute_btn = st.button("실시간 분석 실행 🚀", type="primary", use_container_width=True)

st.write("---")

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
exc_rate = get_current_exchange_rate()

# ★ 헤더 전광판 수정: 날짜 | 총자산 | 시간 | 환율
h_col1, h_col2, h_col3, h_col4 = st.columns(4)
with h_col1: st.info(f"**📅 날짜**\n### {now.strftime('%Y-%m-%d')}")
with h_col2: 
    t_val = f"{st.session_state.total_asset:,.0f}원" if st.session_state.analyzed else "분석 전"
    st.info(f"**💰 총자산**\n### {t_val}")
with h_col3: st.info(f"**⏰ 시간**\n### {now.strftime('%H:%M KST')}")
with h_col4: 
    st.info(f"**💵 환율**\n### {exc_rate:,.1f}원")
    trend = get_exchange_trend()
    if trend is not None:
        fig_s = go.Figure(go.Scatter(x=trend.index, y=trend.values, mode='lines', line=dict(color='#2E7D32', width=2)))
        fig_s.update_layout(margin=dict(l=0,r=0,t=0,b=0), height=40, xaxis=dict(visible=False), yaxis=dict(visible=False), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_s, use_container_width=True, config={'displayModeBar': False})

news_data = get_portfolio_news()
with st.expander("📰 글로벌 뉴스 피드", expanded=False):
    if news_data:
        for item in news_data: st.markdown(f"- [{item['title']}]({item['link']})")
    else: st.write("뉴스를 불러오는 중입니다...")

st.write("---")

# ==========================================
# 4. 분석 엔진
# ==========================================
if execute_btn:
    st.query_params["cash"] = str(input_cash)
    st.query_params["holdings"] = holdings_input
    try:
        user_h = list(map(int, holdings_input.split())) if holdings_input else [0]*len(all_stocks)
        if len(user_h) < len(all_stocks): user_h += [0]*(len(all_stocks)-len(user_h))
    except: st.error("수량 입력 오류"); st.stop()

    with st.spinner('🚀 실시간 시세 분석 중...'):
        curr_assets = 0; t_profit = 0; t_prev_a = input_cash; cache = []; cat_c = {"US":0,"KR":0,"ETF":0}; cat_p1 = {"US":0,"KR":0,"ETF":0}

        # 삼성전자
        sp, sc, s1 = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        s_amt = sp * SAMSUNG_QTY; s_p1 = s1 * SAMSUNG_QTY
        curr_assets += s_amt; t_profit += (s_amt - s_p1); t_prev_a += s_p1
        cat_c["KR"] += s_amt; cat_p1["KR"] += s_p1

        for i, p in enumerate(all_stocks):
            price, cp, p1 = get_real_price_and_change(p['ticker'], p['country'])
            rate = exc_rate if p['country'] == "US" else 1
            my_amt = user_h[i]*price*rate; my_p1 = user_h[i]*p1*rate
            curr_assets += my_amt; t_profit += (my_amt-my_p1); t_prev_a += my_p1
            tp = p['type']; cat_c[tp] += my_amt; cat_p1[tp] += my_p1
            cache.append({"price_krw": price*rate, "my_amt": my_amt, "cp": cp, "profit": my_amt-my_p1, "type": tp, "ticker": p['ticker'], "ratio": p['ratio']})

        total_asset = curr_assets + input_cash
        df_hist = yf.download(all_tickers, period="3y", threads=True, progress=False)
        df_5m = yf.download(all_tickers, period="2d", interval="5m", threads=True, progress=False)

        st.session_state.update({
            "total_asset": total_asset, "rebalance_budget": total_asset - s_amt,
            "t_profit": t_profit, "t_cp": (t_profit/t_prev_a*100) if t_prev_a>0 else 0,
            "sam_amt": s_amt, "sam_price": sp, "sam_cp": sc, "sam_profit": s_amt-s_p1,
            "cache": cache, "user_h": user_h, "input_cash": input_cash,
            "cat_stats": {"US": [cat_c["US"],cat_p1["US"]], "KR": [cat_c["KR"],cat_p1["KR"]], "ETF": [cat_c["ETF"],cat_p1["ETF"]]},
            "df_hist": df_hist, "df_5m": df_5m, "analyzed": True
        })
        st.rerun()

# ==========================================
# 5. 화면 출력 (표 및 정렬)
# ==========================================
if st.session_state.analyzed:
    st.subheader("📑 종목별 상세 현황")
    
    f1, f2, f3, f4, _ = st.columns([1,1,1,1,6])
    if f1.button("🌐 전체", use_container_width=True): st.session_state.view_filter = "전체"
    if f2.button("🇰🇷 국장", use_container_width=True): st.session_state.view_filter = "KR"
    if f3.button("🇺🇸 미장", use_container_width=True): st.session_state.view_filter = "US"
    if f4.button("🛡️ 현금성", use_container_width=True): st.session_state.view_filter = "ETF"

    st.markdown("**↕️ 정렬 기준**")
    s1, s2, s3, _ = st.columns([2, 2, 2, 6])
    if s1.button("💰 실제금액순", use_container_width=True): st.session_state.sort_by = "실제금액숫자"
    if s2.button("📈 등락률순", use_container_width=True): st.session_state.sort_by = "등락률숫자"
    if s3.button("💸 오늘수익순", use_container_width=True): st.session_state.sort_by = "오늘수익숫자"

    rows = []
    budget_invest = st.session_state.rebalance_budget * 0.63

    if st.session_state.view_filter in ["전체", "KR"]:
        rows.append({"종목": get_brand("삼성전자")["name"], "현재가(₩)": f"{st.session_state.sam_price:,.0f}원", "등락률": f"{st.session_state.sam_cp:+.2f}%", "오늘수익": f"{st.session_state.sam_profit:+,.0f}원", "실제비중": f"{(st.session_state.sam_amt/st.session_state.total_asset):.1%}", "실제금액": f"{st.session_state.sam_amt:,.0f}원", "실행": "🔒 고정", "등락률숫자": st.session_state.sam_cp, "실제금액숫자": st.session_state.sam_amt, "오늘수익숫자": st.session_state.sam_profit, "type": "KR"})

    for i, p in enumerate(all_stocks):
        c = st.session_state.cache[i]; my_qty = st.session_state.user_h[i]
        if st.session_state.view_filter != "전체" and c['type'] != st.session_state.view_filter: continue
        
        target_amt = st.session_state.rebalance_budget * c['ratio'] if i < 5 else budget_invest * c['ratio']
        target_qty = round(target_amt / c['price_krw']) if c['price_krw'] > 0 else 0
        diff = target_qty - my_qty
        if diff > 0: action = f"🔴 {int(diff)}주 매수"
        elif diff < 0: action = f"🔵 {int(abs(diff))}주 매도"
        else: action = "🟢 유지"

        rows.append({"종목": get_brand(p['name'])["name"], "현재가(₩)": f"{c['price_krw']:,.0f}원", "등락률": f"{c['cp']:+.2f}%", "오늘수익": f"{c['profit']:+,.0f}원", "실제비중": f"{(c['my_amt']/st.session_state.total_asset):.1%}", "실제금액": f"{c['my_amt']:,.0f}원", "실행": action, "등락률숫자": c['cp'], "실제금액숫자": c['my_amt'], "오늘수익숫자": c['profit'], "type": c['type']})

    df_main = pd.DataFrame(rows).sort_values(by=st.session_state.sort_by, ascending=False)
    
    sum_profit = df_main['오늘수익숫자'].sum()
    sum_asset = df_main['실제금액숫자'].sum()
    sum_ratio = (sum_asset / st.session_state.total_asset) * 100
    
    summary_row = pd.DataFrame([{
        "종목": "✨ 선택 분류 합계", "현재가(₩)": "-", "등락률": "-", 
        "오늘수익": f"{sum_profit:+,.0f}원", "실제비중": f"{sum_ratio:.1%}", 
        "실제금액": f"{sum_asset:,.0f}원", "실행": "-", "오늘수익숫자": sum_profit
    }])
    df_final = pd.concat([df_main, summary_row], ignore_index=True)

    def color_v(val):
        c = '#2E7D32' if '+' in str(val) or '매수' in str(val) else ('#C2185B' if '-' in str(val) or '매도' in str(val) else 'black')
        return f'color: {c}; font-weight: bold;'

    def style_row(row):
        bg = '#F5F5F5' if row['종목'] == '✨ 선택 분류 합계' else 'white'
        return [f'background-color: {bg}'] * len(row)

    st.dataframe(df_final.style.apply(style_row, axis=1).map(color_v, subset=['등락률','오늘수익','실행']).set_properties(**{'text-align': 'center'}),
                 column_order=["종목","현재가(₩)","등락률","오늘수익","실제비중","실제금액","실행"],
                 column_config={"종목": st.column_config.TextColumn("종목", width=160)},
                 hide_index=True, use_container_width=False, height=600)

    st.write("---")
    st.subheader("📋 포트폴리오 요약 (100% 기준)")
    sum_rows = []
    for cd, lb in [("US","🌎 해외주식"), ("KR","🇰🇷 국내주식"), ("ETF","🛡️ 현금성ETF")]:
        v = st.session_state.cat_stats[cd]; prof = v[0]-v[1]
        sum_rows.append({"종목":lb, "등락률":f"{prof/v[1]*100:+.2f}%" if v[1]>0 else "0%", "오늘수익":f"{prof:+,.0f}원", "실제비중":f"{v[0]/st.session_state.total_asset:.1%}", "실제금액":f"{v[0]:,.0f}원"})
    sum_rows.append({"종목":"💵 예수금", "등락률":"-", "오늘수익":"-", "실제비중":f"{st.session_state.input_cash/st.session_state.total_asset:.1%}", "실제금액":f"{st.session_state.input_cash:,.0f}원"})
    sum_rows.append({"종목":"📊 포트폴리오 총합", "등락률":f"{st.session_state.t_cp:+.2f}%", "오늘수익":f"{st.session_state.t_profit:+,.0f}원", "실제비중":"100.0%", "실제금액":f"{st.session_state.total_asset:,.0f}원"})
    
    st.dataframe(pd.DataFrame(sum_rows).style.map(color_v, subset=['등락률','오늘수익']).set_properties(**{'text-align': 'center'}),
                 hide_index=True, use_container_width=False, height=250)

    # ==========================================
    # 6. 차트 센터
    # ==========================================
    st.write("---")
    st.subheader("📊 차트 분석 센터")
    
    def calc_ohlc(df, t_list, q_dict):
        res = pd.DataFrame(0.0, index=df.index, columns=['Open','High','Low','Close'])
        for t in t_list:
            qty = q_dict.get(t, 0)
            if qty == 0: continue
            r = exc_rate if (".KS" not in t and t != SAMSUNG_TICKER) else 1
            for col in res.columns: res[col] += df[col][t].ffill().bfill() * qty * r
        return res + st.session_state.input_cash

    qtys = {SAMSUNG_TICKER: SAMSUNG_QTY}
    for i, p in enumerate(all_stocks): qtys[p['ticker']] = st.session_state.user_h[i]
    
    tab1, tab2, tab3, tab4 = st.tabs(["🕒 2일 5분봉", "🇰🇷 국장 일봉", "🇺🇸 미장 일봉", "📈 전체 누적 영역"])

    def add_lines(fig, ohlc_df, title):
        ath = ohlc_df['High'].max(); ath_d = ohlc_df['High'].idxmax()
        low_3m = ohlc_df['Low'].tail(60).min(); low_d = ohlc_df['Low'].tail(60).idxmin()
        curr = st.session_state.total_asset if title=="전체" else ohlc_df['Close'].iloc[-1]
        
        fig.add_hline(y=ath, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_hline(y=low_3m, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_hline(y=curr, line_dash="dot", line_color="red", opacity=0.8)
        fig.add_annotation(x=ath_d, y=ath, text=f"🚩 전고점: {ath/10000:,.0f}만", showarrow=True)
        fig.add_annotation(x=low_d, y=low_3m, text=f"📉 저점: {low_3m/10000:,.0f}만", ay=40)
        
        # 연/월 구분선
        f_days_month = [group.index[0] for _, group in ohlc_df.groupby([ohlc_df.index.year, ohlc_df.index.month])]
        f_days_year = [group.index[0] for _, group in ohlc_df.groupby(ohlc_df.index.year)]
        for d in f_days_month:
            if d in f_days_year: fig.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5)
            else: fig.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)")

        fig.update_yaxes(tickformat=",.0f", range=[max(0, low_3m*0.9), ath*1.1])
        fig.update_xaxes(tickformat="%Y-%m-%d", rangebreaks=[dict(bounds=["sat", "mon"])])
        return fig

    with tab1:
        w5 = calc_ohlc(st.session_state.df_5m, all_tickers, qtys)
        st.plotly_chart(add_lines(go.Figure(data=[go.Candlestick(x=w5.index, open=w5['Open'], high=w5['High'], low=w5['Low'], close=w5['Close'])]), w5, "전체"), use_container_width=True)
    with tab2:
        kr_tkrs = [SAMSUNG_TICKER] + [p['ticker'] for p in all_stocks if p['country']=='KR']
        w_kr = calc_ohlc(st.session_state.df_hist, kr_tkrs, qtys)
        st.plotly_chart(add_lines(go.Figure(data=[go.Candlestick(x=w_kr.index, open=w_kr['Open'], high=w_kr['High'], low=w_kr['Low'], close=w_kr['Close'])]), w_kr, "국장"), use_container_width=True)
    with tab3:
        us_tkrs = [p['ticker'] for p in all_stocks if p['country']=='US']
        w_us = calc_ohlc(st.session_state.df_hist, us_tkrs, qtys)
        st.plotly_chart(add_lines(go.Figure(data=[go.Candlestick(x=w_us.index, open=w_us['Open'], high=w_us['High'], low=w_us['Low'], close=w_us['Close'])]), w_us, "미장"), use_container_width=True)
    with tab4:
        dfh = st.session_state.df_hist; idx = dfh.index; s_ca = pd.Series(st.session_state.input_cash, index=idx)
        s_et = calc_ohlc(dfh, [p['ticker'] for p in fixed_portfolio], qtys)['Close'] - st.session_state.input_cash
        s_u = calc_ohlc(dfh, [p['ticker'] for p in invest_portfolio if p['country']=='US'], qtys)['Close'] - st.session_state.input_cash
        s_k = calc_ohlc(dfh, [SAMSUNG_TICKER]+[p['ticker'] for p in invest_portfolio if p['country']=='KR'], qtys)['Close'] - st.session_state.input_cash
        fa = go.Figure()
        fa.add_trace(go.Scatter(x=idx, y=s_ca, mode='none', fill='tozeroy', name='💵 예수금', stackgroup='one', fillcolor='#85BB65'))
        fa.add_trace(go.Scatter(x=idx, y=s_et, mode='none', fill='tonexty', name='🛡️ 현금성', stackgroup='one', fillcolor='#FFD54F'))
        fa.add_trace(go.Scatter(x=idx, y=s_u, mode='none', fill='tonexty', name='🌎 미장', stackgroup='one', fillcolor='#F06292'))
        fa.add_trace(go.Scatter(x=idx, y=s_k, mode='none', fill='tonexty', name='🇰🇷 국장', stackgroup='one', fillcolor='#64B5F6'))
        st.plotly_chart(add_lines(fa, calc_ohlc(dfh, all_tickers, qtys), "전체"), use_container_width=True)

    # 파이차트
    st.write("---")
    st.subheader("🍕 현재 자산 구성 비율")
    p_data = []
    if st.session_state.sam_amt > 0: p_data.append({"종목":get_brand("삼성전자")["name"], "금액":st.session_state.sam_amt})
    for i, p in enumerate(all_stocks):
        amt = st.session_state.cache[i]['my_amt']
        if amt > 0: p_data.append({"종목":get_brand(p['name'])["name"], "금액":amt})
    p_data.append({"종목":"💵 예수금", "금액":st.session_state.input_cash})
    st.plotly_chart(px.pie(pd.DataFrame(p_data), values='금액', names='종목', hole=0.4, color='종목',
                   color_discrete_map={v["name"]: v["color"] for v in brand_meta.values()}, height=600), use_container_width=True)
