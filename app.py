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
if "filter_by" not in st.session_state: st.session_state.filter_by = "전체" # 필터 상태 추가
if "total_asset" not in st.session_state: st.session_state.total_asset = 0

# ==========================================
# 🔑 구글 시트 및 포트폴리오 설정 (기존과 동일)
# ==========================================
SAMSUNG_TICKER = "005930.KS"
SAMSUNG_QTY = 41
WEB_APP_URL = "여기에_웹앱_URL을_넣어주세요"

fixed_portfolio = [
    {"name": "GLDM", "ticker": "GLDM", "ratio": 0.04, "country": "US", "type": "현금성"},
    {"name": "VTV",  "ticker": "VTV",  "ratio": 0.04, "country": "US", "type": "현금성"},
    {"name": "TLT",  "ticker": "TLT",  "ratio": 0.025, "country": "US", "type": "현금성"},
    {"name": "IEI",  "ticker": "IEI",  "ratio": 0.015, "country": "US", "type": "현금성"},
    {"name": "SCHD", "ticker": "SCHD", "ratio": 0.04, "country": "US", "type": "현금성"},
]

invest_portfolio = [
    {"name": "TSM",        "ticker": "TSM",    "ratio": 0.25, "country": "US", "type": "미장"},
    {"name": "NVDA",       "ticker": "NVDA",   "ratio": 0.08, "country": "US", "type": "미장"},
    {"name": "TSLA",       "ticker": "TSLA",   "ratio": 0.06, "country": "US", "type": "미장"},
    {"name": "MSFT",       "ticker": "MSFT",   "ratio": 0.065, "country": "US", "type": "미장"},
    {"name": "AAPL",       "ticker": "AAPL",   "ratio": 0.065, "country": "US", "type": "미장"},
    {"name": "GOOGL",      "ticker": "GOOGL",  "ratio": 0.10, "country": "US", "type": "미장"},
    {"name": "AMD",        "ticker": "AMD",    "ratio": 0.065, "country": "US", "type": "미장"},
    {"name": "AMZN",       "ticker": "AMZN",   "ratio": 0.065, "country": "US", "type": "미장"},
    {"name": "SK하이닉스", "ticker": "000660.KS", "ratio": 0.20, "country": "KR", "type": "국장"},
    {"name": "현대차",     "ticker": "005380.KS", "ratio": 0.05, "country": "KR", "type": "국장"},
]

all_stocks = fixed_portfolio + invest_portfolio

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

# --- 데이터 캐싱 함수 (get_current_exchange_rate, get_exchange_trend, get_portfolio_news, get_real_price_and_change 는 기존과 동일하므로 생략 가능하나 로직 유지를 위해 포함) ---
@st.cache_data(ttl=600)
def get_current_exchange_rate():
    try: return yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
    except: return 1400.0

@st.cache_data(ttl=1800)
def get_portfolio_news():
    tickers = ["NVDA", "AAPL", "TSLA", "TSM", "MSFT", "GOOGL"]
    news_list = []
    for t in tickers:
        try:
            news = yf.Ticker(t).news
            if isinstance(news, list):
                for n in news[:2]:
                    if n.get('title') and n.get('link'):
                        news_list.append({"title": f"[{t}] {n['title']}", "link": n['link'], "publisher": n.get('publisher', 'News'), "time": n.get('providerPublishTime', 0)})
        except: pass
    news_list.sort(key=lambda x: x['time'], reverse=True)
    return news_list[:10]

def get_real_price_and_change(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="7d")
        if len(hist) >= 3:
            d2_close, d1_close = hist['Close'].iloc[-3], hist['Close'].iloc[-2]
            prev_change_pct = ((d1_close - d2_close) / d2_close) * 100
        else:
            d2_close, d1_close, prev_change_pct = 0, stock.fast_info.get('previous_close', 0), 0.0
        if country == "KR":
            try: current_price = stock.fast_info['last_price']
            except: current_price = hist['Close'].iloc[-1] if not hist.empty else 0
        else:
            df_intra = stock.history(period="1d", interval="1m", prepost=True)
            current_price = df_intra['Close'].iloc[-1] if not df_intra.empty else stock.fast_info.get('last_price', d1_close)
        change_pct = ((current_price - d1_close) / d1_close) * 100 if d1_close > 0 else 0.0
        return current_price, change_pct, d1_close, prev_change_pct, d2_close
    except: return 0, 0.0, 0, 0.0, 0

# ==========================================
# 3. UI 및 헤더 (기존 유지)
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널")

input_cash = st.number_input("💵 현재 예수금 총액 (원화)", min_value=0, value=10000000, step=100000)
holdings_input = st.text_input("🔢 종목별 수량 (띄어쓰기 구분)", value=st.query_params.get("holdings", ""))
execute_btn = st.button("분석 실행 🚀", type="primary", use_container_width=True)

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
date_str = f"{now.strftime('%Y년 %m월 %d일')}"
time_str = now.strftime("%p %I:%M KST")
exc_rate = get_current_exchange_rate()

head_col1, head_col2, head_col3, head_col4 = st.columns([1, 1.3, 1, 1])
with head_col1: st.info(f"**📅 날짜**\n### {date_str}")
with head_col2: st.info(f"**💰 총자산**\n### {st.session_state.get('total_asset', 0):,.0f}원")
with head_col3: st.info(f"**⏰ 시간**\n### {time_str}")
with head_col4: st.info(f"**💵 환율**\n### {exc_rate:,.1f}원")

# ==========================================
# 4. 데이터 수집 엔진 (기존 로직 유지)
# ==========================================
if execute_btn:
    user_holdings = list(map(int, holdings_input.split())) if holdings_input else [0]*len(all_stocks)
    with st.spinner('시세 분석 중...'):
        stock_data_cache = []
        total_today_profit, total_prev_asset, current_stock_assets = 0, input_cash, 0
        
        # 삼성전자 (고정 국장)
        sp, sc, spre, sprev_c, sd2 = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        sam_amt = sp * SAMSUNG_QTY
        stock_data_cache.append({"name": "삼성전자", "type": "국장", "price_krw": sp, "price_usd": 0, "my_amt": sam_amt, "change_pct": sc, "today_profit": sam_amt - (spre * SAMSUNG_QTY), "prev_close": spre, "qty": SAMSUNG_QTY, "prev_change_pct": sprev_c})
        
        for i, p in enumerate(all_stocks):
            price, change, prev, prev_c, d2 = get_real_price_and_change(p['ticker'], p['country'])
            p_krw = price * exc_rate if p['country'] == "US" else price
            my_amt = p_krw * user_holdings[i]
            prev_amt = (prev * exc_rate if p['country'] == "US" else prev) * user_holdings[i]
            stock_data_cache.append({"name": p['name'], "type": p['type'], "price_krw": p_krw, "price_usd": price if p['country']=="US" else 0, "my_amt": my_amt, "change_pct": change, "today_profit": my_amt - prev_amt, "prev_close": prev, "qty": user_holdings[i], "prev_change_pct": prev_c})

        st.session_state.stock_data_cache = stock_data_cache
        st.session_state.total_asset = sum(x['my_amt'] for x in stock_data_cache) + input_cash
        st.session_state.input_cash = input_cash
        st.session_state.analyzed = True
        st.rerun()

# ==========================================
# 5. 화면 출력부 (필터 및 정렬 기능 추가)
# ==========================================
if st.session_state.analyzed:
    # --- 필터 버튼 구역 ---
    st.write("🔍 **카테고리 필터**")
    f_col1, f_col2, f_col3, f_col4, _ = st.columns([1, 1, 1, 1, 4])
    if f_col1.button("🌐 전체보기", use_container_width=True): st.session_state.filter_by = "전체"
    if f_col2.button("🇰🇷 국장", use_container_width=True): st.session_state.filter_by = "국장"
    if f_col3.button("🇺🇸 미장", use_container_width=True): st.session_state.filter_by = "미장"
    if f_col4.button("🛡️ 현금성", use_container_width=True): st.session_state.filter_by = "현금성"

    # --- 정렬 버튼 구역 ---
    st.write("↕️ **정렬 기준**")
    s_col1, s_col2, s_col3, _ = st.columns([2, 2, 2, 4])
    if s_col1.button("💰 금액순", use_container_width=True): st.session_state.sort_by = "실제금액숫자"
    if s_col2.button("📈 등락률순", use_container_width=True): st.session_state.sort_by = "등락률숫자"
    if s_col3.button("💸 수익순", use_container_width=True): st.session_state.sort_by = "오늘수익숫자"

    # --- 데이터 필터링 및 테이블 생성 ---
    raw_data = st.session_state.stock_data_cache
    if st.session_state.filter_by != "전체":
        filtered_data = [x for x in raw_data if x['type'] == st.session_state.filter_by]
    else:
        filtered_data = raw_data

    # 필터된 종목 행 생성
    rows = []
    for x in filtered_data:
        change_str = f"▲{x['change_pct']:.2f}%" if x['change_pct'] > 0 else (f"▼{abs(x['change_pct']):.2f}%" if x['change_pct'] < 0 else "-")
        profit_str = f"{x['today_profit']:,.0f}원"
        rows.append({
            "종목": get_brand(x['name'])["name"],
            "현재가": f"{x['price_krw']:,.0f}원",
            "등락률": change_str,
            "오늘수익": profit_str,
            "실제금액": f"{x['my_amt']:,.0f}원",
            "내보유": f"{x['qty']}주",
            "등락률숫자": x['change_pct'],
            "실제금액숫자": x['my_amt'],
            "오늘수익숫자": x['today_profit'],
            "전일가": x['prev_close']
        })

    # 정렬 적용
    df_main = pd.DataFrame(rows).sort_values(by=st.session_state.sort_by, ascending=False)

    # --- 필터링된 합계 행 계산 및 추가 ---
    if not df_main.empty:
        total_amt = sum(x['my_amt'] for x in filtered_data)
        total_profit = sum(x['today_profit'] for x in filtered_data)
        # 비중보할 등락률 (가중 평균): (수익합계 / (현재금액합계 - 수익합계)) * 100
        prev_total_amt = total_amt - total_profit
        avg_change = (total_profit / prev_total_amt * 100) if prev_total_amt != 0 else 0
        
        avg_change_str = f"▲{avg_change:.2f}%" if avg_change > 0 else (f"▼{abs(avg_change):.2f}%" if avg_change < 0 else "-")
        
        # 현금성 필터일 경우 예수금도 포함해서 계산 (선택 사항)
        if st.session_state.filter_by == "현금성":
            total_amt += st.session_state.input_cash
            
        summary_row = pd.DataFrame([{
            "종목": f"🏁 {st.session_state.filter_by} 합계",
            "현재가": "-",
            "등락률": avg_change_str,
            "오늘수익": f"{total_profit:,.0f}원",
            "실제금액": f"{total_amt:,.0f}원",
            "내보유": "-",
            "등락률숫자": avg_change,
            "실제금액숫자": total_amt,
            "오늘수익숫자": total_profit
        }])
        df_final = pd.concat([df_main, summary_row], ignore_index=True)
    else:
        df_final = df_main

    # 스타일 함수
    def style_rows(row):
        is_total = "합계" in str(row["종목"])
        bg = "#F0F2F6" if is_total else "white"
        weight = "bold" if is_total else "normal"
        color = "#D32F2F" if "▲" in str(row["등락률"]) else ("#1976D2" if "▼" in str(row["등락률"]) else "black")
        return [f"background-color: {bg}; font-weight: {weight}; color: {color if i==2 or i==3 else 'black'}" for i in range(len(row))]

    st.subheader(f"📑 {st.session_state.filter_by} 상세 현황")
    st.dataframe(
        df_final.style.apply(style_rows, axis=1),
        column_order=["종목", "현재가", "등락률", "오늘수익", "실제금액", "내보유"],
        hide_index=True, use_container_width=True, height=500
    )
