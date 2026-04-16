import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone

# --- 0. 앱 메모리(Session State) 초기화 (에러 방지) ---
if "analyzed" not in st.session_state: st.session_state.analyzed = False
if "sort_by" not in st.session_state: st.session_state.sort_by = "등락률숫자" 
if "view_filter" not in st.session_state: st.session_state.view_filter = "전체"
if "total_asset" not in st.session_state: st.session_state.total_asset = 0

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
    "TSM": {"name": "📱 TSM", "color": "#8A5A5A"}, "NVDA": {"name": "🤖 NVDA", "color": "#76B900"},
    "TSLA": {"name": "🚗 TSLA", "color": "#E31937"}, "MSFT": {"name": "🪟 MSFT", "color": "#F34F1C"},
    "AAPL": {"name": "🍎 AAPL", "color": "#A2AAAD"}, "GOOGL": {"name": "🔍 GOOGL", "color": "#4285F4"},
    "AMD": {"name": "💻 AMD", "color": "#ED1C24"}, "AMZN": {"name": "🛒 AMZN", "color": "#FF9900"},
    "SK하이닉스": {"name": "💾 SK하이닉스", "color": "#E60012"}, "현대차": {"name": "🚙 현대차", "color": "#002C5F"},
    "삼성전자": {"name": "🔒 삼성전자", "color": "#1428A0"}, "GLDM": {"name": "🥇 GLDM", "color": "#FFD700"},
    "VTV": {"name": "🏦 VTV", "color": "#00509E"}, "TLT": {"name": "📜 TLT", "color": "#0076CE"},
    "IEI": {"name": "📄 IEI", "color": "#0093D0"}, "SCHD": {"name": "💸 SCHD", "color": "#005A9C"},
    "예수금": {"name": "💵 예수금", "color": "#85BB65"}
}

def get_brand(raw_name):
    key = raw_name.split()[0]
    return brand_meta.get(key, {"name": raw_name, "color": "#9E9E9E"})

# ==========================================
# 2. UI 구성 (입력 패널 ➔ 헤더)
# ==========================================
st.set_page_config(page_title="퀀트 터미널 Pro", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널 Pro")

st.subheader("⚙️ 자산 및 수량 세팅")
params = st.query_params
input_cash = st.number_input("💵 현재 예수금(원화)", min_value=0, value=int(params.get("cash", "10000000")), step=100000)
holdings_input = st.text_input("🔢 보유 수량 (띄어쓰기 구분, 15종목)", value=params.get("holdings", ""))
execute_btn = st.button("실시간 분석 실행 🚀", type="primary", use_container_width=True)

st.write("---")

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
try: exc_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
except: exc_rate = 1420.0

# 4단 헤더 구성
h1, h2, h3, h4 = st.columns(4)
with h1: st.info(f"**📅 날짜**\n### {now.strftime('%Y-%m-%d')}")
with h2: st.info(f"**💰 현재 총자산**\n### {st.session_state.total_asset:,.0f}원")
with h3: st.info(f"**⏰ 시간**\n### {now.strftime('%H:%M KST')}")
with h4: st.info(f"**💵 환율**\n### {exc_rate:,.1f}원")

# ==========================================
# 3. 데이터 분석 (오리지널 로직 보존)
# ==========================================
def get_real_price_and_change(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")
        d1_close = hist['Close'].iloc[-2] if len(hist) >= 2 else stock.fast_info.get('previous_close', 0)
        if country == "KR": current_price = stock.fast_info['last_price']
        else:
            df_intra = stock.history(period="1d", interval="1m", prepost=True)
            current_price = df_intra['Close'].iloc[-1] if not df_intra.empty else stock.fast_info.get('last_price', d1_close)
        return current_price, ((current_price - d1_close) / d1_close * 100) if d1_close > 0 else 0, d1_close
    except: return 0, 0, 0

if execute_btn:
    st.query_params["cash"] = str(input_cash)
    st.query_params["holdings"] = holdings_input
    user_h = list(map(int, holdings_input.split())) if holdings_input else [0]*len(all_stocks)
    if len(user_h) < len(all_stocks): user_h += [0]*(len(all_stocks)-len(user_h))

    with st.spinner('🚀 데이터 정밀 분석 중...'):
        curr_stock_assets = 0; t_profit = 0; t_prev_a = input_cash; cache = []
        cat_c = {"US": 0, "KR": 0, "ETF": 0}; cat_p = {"US": 0, "KR": 0, "ETF": 0}

        # 삼성전자 계산
        sp, sc, s_p = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        sam_amt = sp * SAMSUNG_QTY; sam_p_amt = s_p * SAMSUNG_QTY
        curr_stock_assets += sam_amt; t_profit += (sam_amt - sam_p_amt); t_prev_a += sam_p_amt
        cat_c["KR"] += sam_amt; cat_p["KR"] += sam_p_amt

        # 15종목 계산
        for i, p in enumerate(all_stocks):
            price, cp, prev_c = get_real_price_and_change(p['ticker'], p['country'])
            rate = exc_rate if p['country'] == "US" else 1
            my_amt = user_h[i] * price * rate; p_amt = user_h[i] * prev_c * rate
            curr_stock_assets += my_amt; t_profit += (my_amt - p_amt); t_prev_a += p_amt
            cat_cur_type = p.get('type', 'US'); cat_c[cat_cur_type] += my_amt; cat_p[cat_cur_type] += p_amt
            cache.append({"price_krw": price*rate, "my_amt": my_amt, "cp": cp, "profit": my_amt-p_amt, "type": cat_cur_type, "ratio": p['ratio'], "name": p['name']})

        total_asset = curr_stock_assets + input_cash
        st.session_state.update({
            "total_asset": total_asset, "sam_amt": sam_amt, "rebalance_budget": total_asset - sam_amt,
            "t_profit": t_profit, "t_cp": (t_profit/t_prev_a*100) if t_prev_a>0 else 0,
            "sam_price": sp, "sam_cp": sc, "sam_profit": sam_amt-sam_p_amt,
            "cache": cache, "user_holdings": user_h, "input_cash": input_cash,
            "cat_stats": {"US": [cat_c["US"], cat_p["US"]], "KR": [cat_c["KR"], cat_p["KR"]], "ETF": [cat_c["ETF"], cat_p["ETF"]]},
            "df_hist": yf.download(all_tickers, period="3y", threads=True, progress=False),
            "df_5m": yf.download(all_tickers, period="2d", interval="5m", threads=True, progress=False),
            "analyzed": True, "exc_rate": exc_rate
        })
        st.rerun()

# ==========================================
# 4. 화면 출력 (필터링 및 표)
# ==========================================
if st.session_state.analyzed:
    st.subheader("📑 종목별 실시간 현황")
    
    # 필터 버튼
    f1, f2, f3, f4, _ = st.columns([1,1,1,1,6])
    if f1.button("🌐 전체", use_container_width=True): st.session_state.view_filter = "전체"
    if f2.button("🇰🇷 국장", use_container_width=True): st.session_state.view_filter = "KR"
    if f3.button("🇺🇸 미장", use_container_width=True): st.session_state.view_filter = "US"
    if f4.button("🛡️ 현금성", use_container_width=True): st.session_state.view_filter = "ETF"

    st.markdown("**↕️ 정렬 기준**")
    s1, s2, s3, _ = st.columns([2.5, 2.5, 2.5, 2.5])
    if s1.button("💰 실제금액순", use_container_width=True): st.session_state.sort_by = "실제금액숫자"
    if s2.button("📈 등락률순", use_container_width=True): st.session_state.sort_by = "등락률숫자"
    if s3.button("💸 오늘수익순", use_container_width=True): st.session_state.sort_by = "오늘수익숫자"

    rows = []; budget_invest = st.session_state.rebalance_budget * 0.63
    
    # 삼성전자 필터
    if st.session_state.view_filter in ["전체", "KR"]:
        rows.append({"종목": "🔒 삼성전자", "현재가(₩)": f"{st.session_state.sam_price:,.0f}원", "등락률": f"{st.session_state.sam_cp:+.2f}%", "오늘수익": f"{st.session_state.sam_profit:+,.0f}원", "실제비중": f"{(st.session_state.sam_amt/st.session_state.total_asset):.1%}", "실제금액": f"{st.session_state.sam_amt:,.0f}원", "실행": "🔒 고정", "오늘수익숫자": st.session_state.sam_profit, "실제금액숫자": st.session_state.sam_amt, "등락률숫자": st.session_state.sam_cp})

    # 나머지 종목
    for i, c in enumerate(st.session_state.cache):
        if st.session_state.view_filter != "전체" and c['type'] != st.session_state.view_filter: continue
        
        my_qty = st.session_state.user_holdings[i]
        target_amt = st.session_state.rebalance_budget * c['ratio'] if i < 5 else budget_invest * c['ratio']
        target_qty = round(target_amt / c['price_krw']) if c['price_krw'] > 0 else 0
        diff = target_qty - my_qty
        action = f"🔴 {int(diff)}주 매수" if diff > 0 else (f"🔵 {int(abs(diff))}주 매도" if diff < 0 else "🟢 유지")

        rows.append({"종목": get_brand(c['name'])["name"], "현재가(₩)": f"{c['price_krw']:,.0f}원", "등락률": f"{c['cp']:+.2f}%", "오늘수익": f"{c['profit']:+,.0f}원", "실제비중": f"{(c['my_amt']/st.session_state.total_asset):.1%}", "실제금액": f"{c['my_amt']:,.0f}원", "실행": action, "오늘수익숫자": c['profit'], "실제금액숫자": c['my_amt'], "등락률숫자": c['cp']})

    df_main = pd.DataFrame(rows).sort_values(by=st.session_state.sort_by, ascending=False)
    
    # 분류 합계 계산
    f_sum_p = df_main['오늘수익숫자'].sum(); f_sum_a = df_main['실제금액숫자'].sum()
    summary_row = pd.DataFrame([{"종목": "✨ 선택 분류 합계", "오늘수익": f"{f_sum_p:+,.0f}원", "실제비중": f"{(f_sum_a/st.session_state.total_asset):.1%}", "실제금액": f"{f_sum_a:,.0f}원"}])
    df_final = pd.concat([df_main, summary_row], ignore_index=True)

    def color_v(val):
        c = '#2E7D32' if '+' in str(val) or '매수' in str(val) else ('#C2185B' if '-' in str(val) or '매도' in str(val) else 'black')
        return f'color: {c}; font-weight: bold;'

    st.dataframe(df_final.style.apply(lambda r: ['background-color: #F8F9FA' if r['종목'] == '✨ 선택 분류 합계' else '' for _ in r], axis=1).map(color_v, subset=['등락률','오늘수익','실행']),
                 column_order=["종목","현재가(₩)","등락률","오늘수익","실제비중","실제금액","실행"],
                 column_config={"종목": st.column_config.TextColumn("종목", width=160)},
                 hide_index=True, use_container_width=True, height=650)

    # 요약표
    st.write("---")
    st.subheader("📋 전체 포트폴리오 요약")
    sum_rows = []
    for cd, lb in [("US","🌎 해외주식 총합"), ("KR","🇰🇷 국내주식 총합"), ("ETF","🛡️ 현금성ETF 총합")]:
        v = st.session_state.cat_stats[cd]; p = v[0]-v[1]
        sum_rows.append({"종목":lb, "등락률":f"{(p/v[1]*100):+.2f}%" if v[1]>0 else "0%", "오늘수익":f"{p:+,.0f}원", "실제비중":f"{v[0]/st.session_state.total_asset:.1%}", "실제금액":f"{v[0]:,.0f}원"})
    sum_rows.append({"종목":"📊 포트폴리오 총합", "등락률":f"{st.session_state.t_cp:+.2f}%", "오늘수익":f"{st.session_state.t_profit:+,.0f}원", "실제비중":"100.0%", "실제금액":f"{st.session_state.total_asset:,.0f}원"})
    st.dataframe(pd.DataFrame(sum_rows).style.apply(lambda r: ['background-color: #EEEEEE' if '총합' in r['종목'] else '' for _ in r], axis=1).map(color_v, subset=['등락률','오늘수익']), hide_index=True, use_container_width=True)

    # ==========================================
    # 5. 차트 센터
    # ==========================================
    st.write("---")
    st.subheader("📊 차트 분석 센터")
    
    def calc_ohlc(df, t_list):
        res = pd.DataFrame(0.0, index=df.index, columns=['Open','High','Low','Close'])
        for t in t_list:
            qty = SAMSUNG_QTY if t == SAMSUNG_TICKER else st.session_state.user_holdings[all_tickers.index(t)]
            r = st.session_state.exc_rate if (".KS" not in t and t != SAMSUNG_TICKER) else 1
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
        # 연/월 구분 수직선
        f_m = [g.index[0] for _, g in ohlc_df.groupby([ohlc_df.index.year, ohlc_df.index.month])]
        f_y = [g.index[0] for _, g in ohlc_df.groupby(ohlc_df.index.year)]
        for d in f_m:
            if d in f_y: fig.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5)
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

    # 파이차트
    st.write("---")
    st.subheader("🍕 현재 자산 구성 비율")
    p_data = [{"종목":get_brand("삼성전자")["name"], "금액":st.session_state.sam_amt}]
    for i, c in enumerate(st.session_state.cache):
        if c['my_amt'] > 0: p_data.append({"종목":get_brand(c['name'])["name"], "금액":c['my_amt']})
    p_data.append({"종목":"💵 예수금", "금액":st.session_state.input_cash})
    st.plotly_chart(px.pie(pd.DataFrame(p_data), values='금액', names='종목', hole=0.4, color='종목',
                   color_discrete_map={v["name"]: v["color"] for v in brand_meta.values()}, height=600), use_container_width=True)
