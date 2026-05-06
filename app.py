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
all_names = [item['name'] for item in all_stocks] + ["삼성전자"]

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
    "예수금": {"name": "💵 예수금", "color": "#85BB65"},
    "포트폴리오 총합": {"name": "📊 포트폴리오 총합", "color": "#EEEEEE"}
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
        return float(hist['Close'].iloc[-1])
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
# 3. 최상단 UI (기록 차트 + 전광판 + 입력 패널)
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="📈", layout="wide")
st.title("📈 퀀트 포트폴리오 터미널")

# 과거 총자산 기록 차트
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
                diff = history_df['총자산'].iloc[-1] - history_df['총자산'].iloc[-2]
                st.metric(label="구글 시트에 기록된 최근 총 자산", value=f"{int(history_df['총자산'].iloc[-1]):,.0f}원", delta=f"{int(diff):,.0f}원")
            st.write("---")
except Exception as e:
    pass

st.subheader("⚙️ 통합 자산 데이터 입력 (원클릭 복붙)")
params = st.query_params
default_data = params.get("data", "")

st.caption(f"🚨 **입력 규칙 (총 48개 숫자):** 현금(1) + 수량(15) + 평균단가_원화(16) + 실현손익_원화(16)")
all_data_input = st.text_input("📝 데이터 입력칸", value=default_data, placeholder="예: 10000000 10 5 3 0 10 50 ... (48개 숫자 띄어쓰기 연속 입력)")
execute_btn = st.button("분석 실행 및 시트에 기록 🚀", type="primary", use_container_width=True)

st.write("---")

kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
weekdays = ["월", "화", "수", "목", "금", "토", "일"]
date_str = f"{now.strftime('%Y년 %m월 %d일')} ({weekdays[now.weekday()]})"
time_str = now.strftime("%p %I:%M").replace("AM", "오전").replace("PM", "오후")
exc_rate = get_current_exchange_rate()

# ★ 전광판: 날짜 -> 총자산 -> 시간 -> 환율 순서 배치
head_col1, head_col2, head_col3, head_col4 = st.columns(4)
with head_col1: st.info(f"**📅 오늘 날짜**\n### {date_str}")
with head_col2: 
    if st.session_state.total_asset > 0:
        st.info(f"**💰 포트폴리오 총 자산**\n### {st.session_state.total_asset:,.0f}원")
    else:
        st.info(f"**💰 포트폴리오 총 자산**\n### 분석 대기중")
with head_col3: st.info(f"**⏰ 현재 시간**\n### {time_str}")
with head_col4: 
    st.info(f"**💵 실시간 환율**\n### {exc_rate:,.1f}원")
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
    st.query_params["data"] = all_data_input
    
    try:
        raw_vals = [float(x) for x in all_data_input.split()]
        if len(raw_vals) == 0:
            input_cash = 10000000
            user_holdings = [0]*15 
            avg_prices = [0]*16
            realized_profits = [0]*16
        else:
            input_cash = raw_vals[0]
            user_holdings = [int(x) for x in raw_vals[1:16]]
            avg_prices = raw_vals[16:32]
            realized_profits = raw_vals[32:48]
            
            while len(user_holdings) < 15: user_holdings.append(0)
            while len(avg_prices) < 16: avg_prices.append(0.0)
            while len(realized_profits) < 16: realized_profits.append(0.0)
    except ValueError:
        st.error("숫자와 띄어쓰기만 입력해주세요!")
        st.stop()

    with st.spinner('실시간 시세 및 3년치 글로벌 차트 로딩 중... (약 15초 소요)'):
        try: 
            fx_hist = yf.Ticker("KRW=X").history(period="5d")
            exchange_rate = float(fx_hist['Close'].iloc[-1])
        except: exchange_rate = 1400.0
        
        current_stock_assets = 0
        total_today_profit = 0
        total_prev_asset = input_cash 
        total_prev2_asset = input_cash 
        stock_data_cache = [] 
        
        cat_cur = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev = {"US": 0, "KR": 0, "ETF": 0}
        cat_prev2 = {"US": 0, "KR": 0, "ETF": 0}

        profit_details = []
        cat_profit = {
            "US": {"unreal":0, "real":0, "total":0, "prin":0},
            "KR": {"unreal":0, "real":0, "total":0, "prin":0},
            "ETF": {"unreal":0, "real":0, "total":0, "prin":0},
            "ALL": {"unreal":0, "real":0, "total":0, "prin":0}
        }

        def add_profit_cat(category, unreal, real, prin):
            for c in [category, "ALL"]:
                cat_profit[c]["unreal"] += unreal
                cat_profit[c]["real"] += real
                cat_profit[c]["total"] += (unreal + real)
                cat_profit[c]["prin"] += prin

        sam_qty = SAMSUNG_QTY
        sam_price, sam_change, sam_prev, sam_prev_change, sam_d2 = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        sam_amt = sam_price * sam_qty
        sam_profit = sam_amt - (sam_prev * sam_qty)
        current_stock_assets += sam_amt
        total_today_profit += sam_profit
        total_prev_asset += (sam_prev * sam_qty)
        total_prev2_asset += (sam_d2 * sam_qty)
        cat_cur["KR"] += sam_amt
        cat_prev["KR"] += (sam_prev * sam_qty)
        cat_prev2["KR"] += (sam_d2 * sam_qty)

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
            
            current_stock_assets += my_amt
            total_today_profit += today_profit
            total_prev_asset += prev_amt_krw
            total_prev2_asset += prev2_amt_krw
            
            sector = "ETF" if i < 5 else ("US" if p['country'] == 'US' else "KR")
            if sector == "ETF":
                cat_cur["ETF"] += my_amt; cat_prev["ETF"] += prev_amt_krw; cat_prev2["ETF"] += prev2_amt_krw
            elif sector == "US":
                cat_cur["US"] += my_amt; cat_prev["US"] += prev_amt_krw; cat_prev2["US"] += prev2_amt_krw
            else:
                cat_cur["KR"] += my_amt; cat_prev["KR"] += prev_amt_krw; cat_prev2["KR"] += prev2_amt_krw
            
            stock_data_cache.append({
                "price_krw": price_krw, "price_usd": price_usd, "my_amt": my_amt, 
                "change_pct": change_pct, "today_profit": today_profit, "prev_change_pct": prev_change_pct,
                "sector": sector # 필터링을 위한 섹터 정보 임시 저장
            })

            avg_p = avg_prices[i]
            real_p = realized_profits[i]
            inv_krw = avg_p * my_qty 
            
            unreal = my_amt - inv_krw if my_qty > 0 else 0
            total = unreal + real_p
            prin = my_amt - total 
            
            real_avg = avg_p - (real_p / my_qty) if my_qty > 0 else 0
            rtn = (total / prin * 100) if prin > 0 else 0
            
            add_profit_cat(sector, unreal, real_p, prin)
            
            profit_details.append({
                "종목": get_brand(p['name'])["name"],
                "평균단가": f"{avg_p:,.0f}원", "실제평균단가": f"{real_avg:,.0f}원", "현재가": f"{price_krw:,.0f}원",
                "미실현수익": unreal, "실현수익": real_p, "총수익": total, "원금(조정)": prin, "수익률": rtn
            })

        sam_avg_p = avg_prices[15]
        sam_real_p = realized_profits[15]
        sam_inv_krw = sam_avg_p * sam_qty
        sam_unreal = sam_amt - sam_inv_krw if sam_qty > 0 else 0
        sam_total = sam_unreal + sam_real_p
        sam_prin = sam_amt - sam_total
        sam_real_avg = sam_avg_p - (sam_real_p / sam_qty) if sam_qty > 0 else 0
        sam_rtn = (sam_total / sam_prin * 100) if sam_prin > 0 else 0

        add_profit_cat("KR", sam_unreal, sam_real_p, sam_prin)
        profit_details.append({
            "종목": get_brand("삼성전자")["name"],
            "평균단가": f"{sam_avg_p:,.0f}원", "실제평균단가": f"{sam_real_avg:,.0f}원", "현재가": f"{sam_price:,.0f}원",
            "미실현수익": sam_unreal, "실현수익": sam_real_p, "총수익": sam_total, "원금(조정)": sam_prin, "수익률": sam_rtn
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
        st.session_state.sam_qty = sam_qty
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
        st.session_state.profit_details = profit_details
        st.session_state.cat_profit = cat_profit
        st.session_state.df_hist = df_hist
        st.session_state.analyzed = True
        st.rerun()

# ==========================================
# 5. 화면 출력부 (표 분리, 필터 버튼 추가)
# ==========================================
if st.session_state.analyzed:
    st.write("↕️ **정렬 기준 선택 (클릭 시 즉각 정렬)**")
    col_btn1, col_btn2, col_btn3, _ = st.columns([2.5, 2.5, 2.5, 2.5])
    if col_btn1.button("💰 실제금액 내림차순", use_container_width=True): st.session_state.sort_by = "실제금액숫자"
    if col_btn2.button("📈 등락률 내림차순", use_container_width=True): st.session_state.sort_by = "등락률숫자"
    if col_btn3.button("💸 오늘수익 내림차순", use_container_width=True): st.session_state.sort_by = "오늘수익숫자"

    # --- 공통 스타일링 함수 ---
    def style_change_color(val):
        val_str = str(val)
        if '▼' in val_str or '-' in val_str: return 'background-color: #FFD1DC; color: #C2185B; font-weight: bold;'
        elif '▲' in val_str: return 'background-color: #CCFFCC; color: #2E7D32; font-weight: bold;'
        return ''

    def style_profit_color(val):
        val_str = str(val)
        if '▼' in val_str or '-' in val_str: return 'color: #C2185B; font-weight: bold;'
        elif '▲' in val_str: return 'color: #2E7D32; font-weight: bold;'
        return ''

    def style_d1_color(val):
        val_str = str(val)
        if '▼' in val_str or '-' in val_str: return 'color: #C2185B; font-weight: bold;'
        elif '▲' in val_str: return 'color: #2E7D32; font-weight: bold;'
        return ''

    def style_text_color(val):
        color = 'black'
        if '매수' in str(val): color = '#D32F2F'
        elif '매도' in str(val): color = '#1976D2'
        return f'color: {color}; font-weight: bold;'

    def format_profit(v):
        if v > 0: return f"▲ {v:,.0f}원"
        elif v < 0: return f"▼ {abs(v):,.0f}원"
        return "0원"

    def format_rtn(v):
        if v > 0: return f"▲ {v:,.2f}%"
        elif v < 0: return f"▼ {abs(v):,.2f}%"
        return "0.00%"

    # --- 5-1. 리밸런싱 현황표 ---
    stock_rows = []
    total_buy_cost = 0 
    budget_invest = st.session_state.rebalance_budget * 0.63  

    sam_change_str = f"▲ {st.session_state.sam_change:.2f}%" if st.session_state.sam_change > 0 else (f"▼ {abs(st.session_state.sam_change):.2f}%" if st.session_state.sam_change < 0 else "-")
    sam_prev_change_str = f"▲ {st.session_state.sam_prev_change:.2f}%" if st.session_state.sam_prev_change > 0 else (f"▼ {abs(st.session_state.sam_prev_change):.2f}%" if st.session_state.sam_prev_change < 0 else "-")
    sam_profit_str = format_profit(st.session_state.sam_profit)
    
    stock_rows.append({
        "구분": "KR", # 필터링용
        "종목": get_brand("삼성전자")["name"], "현재가($)": "-", "현재가(₩)": f"{st.session_state.sam_price:,.0f}원", 
        "D-1": sam_prev_change_str, "등락률": sam_change_str, "오늘수익": sam_profit_str,
        "목표비중": "-", "실제비중": f"{(st.session_state.sam_amt/st.session_state.total_asset):.1%}",
        "목표금액": "-", "실제금액": f"{st.session_state.sam_amt:,.0f}원",
        "목표수량": "-", "내보유": str(int(st.session_state.sam_qty)), "실행": "🔒 매매불가",
        "등락률숫자": st.session_state.sam_change, "실제금액숫자": st.session_state.sam_amt, "오늘수익숫자": st.session_state.sam_profit
    })

    for i, p in enumerate(all_stocks):
        cached = st.session_state.stock_data_cache[i]
        price_krw = cached['price_krw']; price_usd = cached['price_usd']
        my_amt = cached['my_amt']; change_pct = cached['change_pct']
        prev_change_pct = cached['prev_change_pct']; today_profit = cached['today_profit']
        my_qty = st.session_state.user_holdings[i]
        sector_cat = cached['sector']

        if i < 5: 
            target_amt = st.session_state.rebalance_budget * p['ratio']
            display_target_ratio = f"{p['ratio']:.1%}"
        else: 
            target_amt = budget_invest * p['ratio']
            display_target_ratio = f"{(0.63 * p['ratio']):.1%}"

        target_qty = round(target_amt / price_krw) if price_krw > 0 else 0
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
        
        stock_rows.append({
            "구분": sector_cat,
            "종목": get_brand(p['name'])["name"], "현재가($)": price_display, "현재가(₩)": f"{price_krw:,.0f}원", 
            "D-1": prev_change_str, "등락률": change_str, "오늘수익": format_profit(today_profit),
            "목표비중": display_target_ratio, "실제비중": current_ratio,
            "목표금액": f"{actual_target_cost:,.0f}원", "실제금액": f"{my_amt:,.0f}원",
            "목표수량": str(int(target_qty)), "내보유": str(int(my_qty)), "실행": action,
            "등락률숫자": change_pct, "실제금액숫자": my_amt, "오늘수익숫자": today_profit
        })

    df_stocks = pd.DataFrame(stock_rows).sort_values(by=st.session_state.sort_by, ascending=False)
    
    # ★ 버튼식 종목 필터링 복구
    filter_opt = st.radio("🔍 섹터 필터", ["전체보기", "🌎 미장 (US)", "🇰🇷 국장 (KR)", "🛡️ 현금성 (ETF)"], horizontal=True)
    if filter_opt == "🌎 미장 (US)": df_stocks = df_stocks[df_stocks['구분'] == 'US']
    elif filter_opt == "🇰🇷 국장 (KR)": df_stocks = df_stocks[df_stocks['구분'] == 'KR']
    elif filter_opt == "🛡️ 현금성 (ETF)": df_stocks = df_stocks[df_stocks['구분'] == 'ETF']
    
    df_stocks = df_stocks.drop(columns=['등락률숫자', '실제금액숫자', '오늘수익숫자', '구분'])

    # ★ 누락됐던 총합 줄 상세 표에 복구
    tot_pct = st.session_state.total_daily_return_pct
    tot_d1_pct = st.session_state.total_d1_change_pct
    tot_prof = st.session_state.total_today_profit
    
    tot_pct_str = f"▲ {tot_pct:.2f}%" if tot_pct > 0 else (f"▼ {abs(tot_pct):.2f}%" if tot_pct < 0 else "-")
    tot_d1_pct_str = f"▲ {tot_d1_pct:.2f}%" if tot_d1_pct > 0 else (f"▼ {abs(tot_d1_pct):.2f}%" if tot_d1_pct < 0 else "-")
    tot_profit_str = f"▲ {tot_prof:,.0f}원" if tot_prof > 0 else (f"▼ {abs(tot_prof):,.0f}원" if tot_prof < 0 else "-")
    
    total_row_df = pd.DataFrame([{
        "종목": "📊 포트폴리오 총합", "현재가($)": "-", "현재가(₩)": "-", "D-1": tot_d1_pct_str, "등락률": tot_pct_str, "오늘수익": tot_profit_str,
        "목표비중": "100.0%", "실제비중": "100.0%", "목표금액": "-", "실제금액": f"{st.session_state.total_asset:,.0f}원",
        "목표수량": "-", "내보유": "-", "실행": "-"
    }])
    
    df_stocks = pd.concat([df_stocks, total_row_df], ignore_index=True)

    st.subheader("📑 리밸런싱 상세 현황")
    
    def style_stocks_dataframe(row):
        bg = 'white'
        if '포트폴리오 총합' in row['종목']: bg = '#EEEEEE'
        return [f'background-color: {bg}'] * len(row)

    st.dataframe(
        df_stocks.style.apply(style_stocks_dataframe, axis=1)
                 .map(style_text_color, subset=['실행'])
                 .map(style_change_color, subset=['등락률', '오늘수익'])
                 .map(style_d1_color, subset=['D-1'])
                 .set_properties(**{'text-align': 'center'}),
        column_order=["종목", "현재가($)", "현재가(₩)", "D-1", "등락률", "오늘수익", "목표비중", "실제비중", "목표금액", "실제금액", "목표수량", "내보유", "실행"],
        column_config={"종목": st.column_config.TextColumn("종목", width=160)},
        hide_index=True, use_container_width=False, height=650 
    )

    # --- 5-2. 섹터별 요약표 ---
    st.write("---")
    col_t1, col_t2 = st.columns([5, 5])
    
    with col_t1:
        st.subheader("📋 섹터별 자산 요약")
        sum_rows = []
        for code, label in [("US", "🌎 해외주식 총합"), ("KR", "🇰🇷 국내주식 총합"), ("ETF", "🛡️ 현금성ETF 총합")]:
            c_cur = st.session_state.cat_stats[code]
            c_prev = st.session_state.cat_stats[code + "_P"]
            c_prev2 = st.session_state.cat_stats[code + "_P2"]
            c_prof = c_cur - c_prev
            c_pct = (c_prof / c_prev * 100) if c_prev > 0 else 0
            c_d1_pct = ((c_prev - c_prev2) / c_prev2 * 100) if c_prev2 > 0 else 0
            sum_rows.append({
                "구분": label, "D-1": format_rtn(c_d1_pct), "등락률": format_rtn(c_pct), "오늘수익": format_profit(c_prof),
                "실제비중": f"{(c_cur / st.session_state.total_asset):.1%}", "실제금액": f"{c_cur:,.0f}원"
            })
        
        remaining_cash = st.session_state.rebalance_budget - total_buy_cost
        sum_rows.append({
            "구분": get_brand("예수금")["name"], "D-1": "-", "등락률": "-", "오늘수익": "-",
            "실제비중": f"{(st.session_state.input_cash / st.session_state.total_asset):.1%}", "실제금액": f"{st.session_state.input_cash:,.0f}원"
        })

        sum_rows.append({
            "구분": "📊 포트폴리오 총합", "D-1": format_rtn(tot_d1_pct), "등락률": format_rtn(tot_pct), "오늘수익": format_profit(tot_prof),
            "실제비중": "100.0%", "실제금액": f"{st.session_state.total_asset:,.0f}원"
        })
        
        def style_summary_dataframe(row):
            bg = 'white'
            if '해외주식' in row['구분']: bg = '#FCE4EC'
            elif '국내주식' in row['구분']: bg = '#E3F2FD'
            elif '현금성ETF' in row['구분']: bg = '#FFF9C4'
            elif '예수금' in row['구분']: bg = '#F1F8E9' 
            elif '총합' in row['구분']: bg = '#EEEEEE'
            return [f'background-color: {bg}'] * len(row)

        st.dataframe(
            pd.DataFrame(sum_rows).style.apply(style_summary_dataframe, axis=1)
                      .map(style_change_color, subset=['등락률', '오늘수익'])
                      .map(style_d1_color, subset=['D-1'])
                      .set_properties(**{'text-align': 'center'}),
            hide_index=True, use_container_width=True
        )

    # --- 5-3. 섹터별 수익 요약표 (실현/미실현) ---
    with col_t2:
        st.subheader("📋 섹터별 수익 요약 (실현 반영)")
        cat_p = st.session_state.cat_profit
        sec_profit_rows = []
        for code, label in [("US", "🌎 해외주식"), ("KR", "🇰🇷 국내주식"), ("ETF", "🛡️ 현금성ETF"), ("ALL", "📊 포트폴리오 전체")]:
            c = cat_p[code]
            rtn = (c['total'] / c['prin'] * 100) if c['prin'] > 0 else 0
            sec_profit_rows.append({
                "구분": label, "미실현수익": format_profit(c['unreal']), "실현수익": format_profit(c['real']),
                "총수익": format_profit(c['total']), "원금(조정)": f"{c['prin']:,.0f}원", "수익률": format_rtn(rtn)
            })

        st.dataframe(
            pd.DataFrame(sec_profit_rows).style.apply(style_summary_dataframe, axis=1)
                      .map(style_profit_color, subset=['미실현수익', '실현수익', '총수익', '수익률'])
                      .set_properties(**{'text-align': 'center'}),
            hide_index=True, use_container_width=True
        )

    # --- 5-4. 종목별 상세 수익 현황 ---
    st.write("---")
    st.subheader("📑 종목별 상세 수익 현황 (실현손익 반영)")
    df_profits = pd.DataFrame(st.session_state.profit_details)
    
    # ★ 누락됐던 종목별 수익현황 총합 줄 복구
    tot_unreal = st.session_state.cat_profit["ALL"]["unreal"]
    tot_real = st.session_state.cat_profit["ALL"]["real"]
    tot_total = st.session_state.cat_profit["ALL"]["total"]
    tot_prin = st.session_state.cat_profit["ALL"]["prin"]
    tot_profit_rtn = (tot_total / tot_prin * 100) if tot_prin > 0 else 0
    
    profit_total_row = pd.DataFrame([{
        "종목": "📊 포트폴리오 총합", "평균단가": "-", "실제평균단가": "-", "현재가": "-",
        "미실현수익": tot_unreal, "실현수익": tot_real, "총수익": tot_total, "원금(조정)": tot_prin, "수익률": tot_profit_rtn
    }])
    df_profits = pd.concat([df_profits, profit_total_row], ignore_index=True)

    df_profits['미실현수익'] = df_profits['미실현수익'].apply(format_profit)
    df_profits['실현수익'] = df_profits['실현수익'].apply(format_profit)
    df_profits['총수익'] = df_profits['총수익'].apply(format_profit)
    df_profits['수익률'] = df_profits['수익률'].apply(format_rtn)
    df_profits['원금(조정)'] = df_profits['원금(조정)'].apply(lambda x: f"{x:,.0f}원" if isinstance(x, (int, float)) else x)

    def style_profit_dataframe(row):
        bg = 'white'
        if '포트폴리오 총합' in row['종목']: bg = '#EEEEEE'
        return [f'background-color: {bg}'] * len(row)

    st.dataframe(
        df_profits.style.apply(style_profit_dataframe, axis=1)
                  .map(style_profit_color, subset=['미실현수익', '실현수익', '총수익', '수익률'])
                  .set_properties(**{'text-align': 'center'}),
        column_config={"종목": st.column_config.TextColumn("종목", width=160)},
        hide_index=True, use_container_width=False, height=650
    )

    # ==========================================
    # 6. 전문가 레이아웃 차트 구역
    # ==========================================
    st.write("---")
    col_chart, col_pie = st.columns([6, 4])
    
    with col_chart:
        st.subheader("📉 자산 성장 시뮬레이션 (3년)")
        # ★ 내 보유종목 기준 맞춤형 미장/국장 캔들 차트 복구
        tab1, tab2, tab3, tab4 = st.tabs(["🕯️ 총자산 캔들", "📊 층별 누적 영역", "🦅 내 미장 포트폴리오", "🐅 내 국장 포트폴리오"])
        
        try:
            df_hist = st.session_state.df_hist
            
            # --- 차트 데이터 생성기 (섹터별 분리) ---
            def get_custom_series(sector):
                s_O = pd.Series(0.0, index=df_hist.index)
                s_H = pd.Series(0.0, index=df_hist.index)
                s_L = pd.Series(0.0, index=df_hist.index)
                s_C = pd.Series(0.0, index=df_hist.index)
                
                if sector in ['ALL', 'KR']:
                    s_O += df_hist['Open'][SAMSUNG_TICKER].ffill().bfill() * st.session_state.sam_qty
                    s_H += df_hist['High'][SAMSUNG_TICKER].ffill().bfill() * st.session_state.sam_qty
                    s_L += df_hist['Low'][SAMSUNG_TICKER].ffill().bfill() * st.session_state.sam_qty
                    s_C += df_hist['Close'][SAMSUNG_TICKER].ffill().bfill() * st.session_state.sam_qty
                
                if sector == 'ALL':
                    s_O += st.session_state.input_cash
                    s_H += st.session_state.input_cash
                    s_L += st.session_state.input_cash
                    s_C += st.session_state.input_cash

                for i, p in enumerate(all_stocks):
                    qty = st.session_state.user_holdings[i]
                    if qty > 0:
                        tkr = p['ticker']
                        p_sec = "US" if p['country'] == 'US' else "KR"
                        
                        if sector == 'ALL' or sector == p_sec:
                            if p['country'] == 'US':
                                s_O += df_hist['Open'][tkr].ffill().bfill() * df_hist['Open']['KRW=X'].ffill().bfill() * qty
                                s_H += df_hist['High'][tkr].ffill().bfill() * df_hist['High']['KRW=X'].ffill().bfill() * qty
                                s_L += df_hist['Low'][tkr].ffill().bfill() * df_hist['Low']['KRW=X'].ffill().bfill() * qty
                                s_C += df_hist['Close'][tkr].ffill().bfill() * df_hist['Close']['KRW=X'].ffill().bfill() * qty
                            else:
                                s_O += df_hist['Open'][tkr].ffill().bfill() * qty
                                s_H += df_hist['High'][tkr].ffill().bfill() * qty
                                s_L += df_hist['Low'][tkr].ffill().bfill() * qty
                                s_C += df_hist['Close'][tkr].ffill().bfill() * qty
                return s_O, s_H, s_L, s_C

            # 총자산 시리즈
            hist_O, hist_H, hist_L, hist_C = get_custom_series('ALL')
            # 미장 전용 시리즈
            us_O, us_H, us_L, us_C = get_custom_series('US')
            # 국장 전용 시리즈
            kr_O, kr_H, kr_L, kr_C = get_custom_series('KR')

            # 현재가 강제 동기화 (꼬리 보정)
            if len(hist_C) > 0:
                hist_C.iloc[-1] = st.session_state.total_asset
                us_C.iloc[-1] = st.session_state.cat_stats['US']
                kr_C.iloc[-1] = st.session_state.cat_stats['KR']
                
                if hist_H.iloc[-1] < hist_C.iloc[-1]: hist_H.iloc[-1] = hist_C.iloc[-1]
                if hist_L.iloc[-1] > hist_C.iloc[-1]: hist_L.iloc[-1] = hist_C.iloc[-1]
                
                if us_H.iloc[-1] < us_C.iloc[-1]: us_H.iloc[-1] = us_C.iloc[-1]
                if us_L.iloc[-1] > us_C.iloc[-1]: us_L.iloc[-1] = us_C.iloc[-1]
                
                if kr_H.iloc[-1] < kr_C.iloc[-1]: kr_H.iloc[-1] = kr_C.iloc[-1]
                if kr_L.iloc[-1] > kr_C.iloc[-1]: kr_L.iloc[-1] = kr_C.iloc[-1]

            s_cash = pd.Series(st.session_state.input_cash, index=df_hist.index) 
            s_etf = pd.Series(0, index=df_hist.index)
            s_us = pd.Series(0, index=df_hist.index)
            s_kr = pd.Series(0, index=df_hist.index)
            s_kr += df_hist['Close'][SAMSUNG_TICKER].ffill().bfill() * st.session_state.sam_qty
            
            for i, p in enumerate(all_stocks):
                qty = st.session_state.user_holdings[i]
                if qty > 0:
                    tkr = p['ticker']
                    if p['country'] == 'US': val = df_hist['Close'][tkr].ffill().bfill() * df_hist['Close']['KRW=X'].ffill().bfill() * qty
                    else: val = df_hist['Close'][tkr].ffill().bfill() * qty
                    if i < 5: s_etf += val
                    elif p['country'] == 'US': s_us += val
                    else: s_kr += val

            def get_chart_bounds(s_H, s_L, s_C):
                a_val = s_H.max(); a_date = s_H.idxmax()
                l_date = df_hist.index[-1]
                z_start = l_date - pd.Timedelta(days=90)
                mask = (df_hist.index >= z_start)
                if mask.any():
                    l_3m_val = s_L[mask].min(); l_3m_date = s_L[mask].idxmin()
                    m_y = s_H[mask].max() * 1.10
                else:
                    l_3m_val = s_L.min(); l_3m_date = s_L.idxmin()
                    m_y = s_H.max() * 1.10
                mi_y = max(0, l_3m_val * 0.98) 
                c_val = s_C.iloc[-1]; c_date = s_C.index[-1]
                return a_val, a_date, l_3m_val, l_3m_date, c_val, c_date, z_start, l_date, mi_y, m_y

            first_days_month = [group.index[0] for _, group in df_hist.groupby([df_hist.index.year, df_hist.index.month])]
            first_days_year = [group.index[0] for _, group in df_hist.groupby(df_hist.index.year)]

            # 탭 1: 총자산 캔들
            with tab1:
                ath_val, ath_date, low_3m_val, low_3m_date, curr_val, curr_date, zoom_start, last_date, min_y, max_y = get_chart_bounds(hist_H, hist_L, hist_C)
                fig_candle = go.Figure(data=[go.Candlestick(x=hist_C.index, open=hist_O.values, high=hist_H.values, low=hist_L.values, close=hist_C.values, name='총자산')])
                
                fig_candle.add_hline(y=ath_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig_candle.add_hline(y=low_3m_val, line_dash="dash", line_color="gray", opacity=0.7)
                fig_candle.add_hline(y=curr_val, line_dash="dash", line_color="red", opacity=0.7)

                fig_candle.add_annotation(x=ath_date, y=ath_val, text=f"📅 {ath_date.strftime('%y년 %m월 %d일')}<br>🚩 전고점: {ath_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=-45, bgcolor="white", bordercolor="gray")
                fig_candle.add_annotation(x=low_3m_date, y=low_3m_val, text=f"📅 {low_3m_date.strftime('%y년 %m월 %d일')}<br>📉 3개월 저점: {low_3m_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=45, bgcolor="white", bordercolor="gray")
                fig_candle.add_annotation(x=curr_date, y=curr_val, text=f"🔴 현재가: {curr_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=-70, ay=0, bgcolor="white", bordercolor="red")

                fig_candle.update_yaxes(tickformat=",.0f")
                fig_candle.update_xaxes(tickformat="%Y년 %m월 %d일", hoverformat="%Y년 %m월 %d일", rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])]) 
                fig_candle.update_layout(xaxis_range=[zoom_start, last_date], yaxis_range=[min_y, max_y], margin=dict(l=0, r=0, t=30, b=0), height=500)
                
                for d in first_days_month: 
                    if d in first_days_year: fig_candle.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                    else: fig_candle.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                st.plotly_chart(fig_candle, use_container_width=True)

            # 탭 2: 층별 누적 영역
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
                
                for d in first_days_month: 
                    if d in first_days_year: fig_area.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                    else: fig_area.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                st.plotly_chart(fig_area, use_container_width=True)

            # ★ 탭 3: 내 미장 포트폴리오 전용 캔들차트
            with tab3:
                u_ath_val, u_ath_date, u_low_3m_val, u_low_3m_date, u_curr_val, u_curr_date, u_z_start, u_l_date, u_min_y, u_max_y = get_chart_bounds(us_H, us_L, us_C)
                if us_H.max() > 0:
                    fig_us = go.Figure(data=[go.Candlestick(x=us_C.index, open=us_O.values, high=us_H.values, low=us_L.values, close=us_C.values, name='미장 포트')])
                    fig_us.add_hline(y=u_ath_val, line_dash="dash", line_color="gray", opacity=0.7)
                    fig_us.add_hline(y=u_low_3m_val, line_dash="dash", line_color="gray", opacity=0.7)
                    fig_us.add_hline(y=u_curr_val, line_dash="dash", line_color="red", opacity=0.7)
                    fig_us.add_annotation(x=u_ath_date, y=u_ath_val, text=f"🚩 미장 고점: {u_ath_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=-45, bgcolor="white", bordercolor="gray")
                    fig_us.add_annotation(x=u_curr_date, y=u_curr_val, text=f"🔴 현재가: {u_curr_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=-70, ay=0, bgcolor="white", bordercolor="red")
                    fig_us.update_yaxes(tickformat=",.0f")
                    fig_us.update_xaxes(tickformat="%Y년 %m월 %d일", hoverformat="%Y년 %m월 %d일", rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])])
                    fig_us.update_layout(xaxis_range=[u_z_start, u_l_date], yaxis_range=[u_min_y, u_max_y], margin=dict(l=0, r=0, t=30, b=0), height=500)
                    for d in first_days_month: 
                        if d in first_days_year: fig_us.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                        else: fig_us.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                    st.plotly_chart(fig_us, use_container_width=True)
                else:
                    st.info("현재 미장(US) 종목을 보유하고 있지 않습니다.")

            # ★ 탭 4: 내 국장 포트폴리오 전용 캔들차트
            with tab4:
                k_ath_val, k_ath_date, k_low_3m_val, k_low_3m_date, k_curr_val, k_curr_date, k_z_start, k_l_date, k_min_y, k_max_y = get_chart_bounds(kr_H, kr_L, kr_C)
                if kr_H.max() > 0:
                    fig_kr = go.Figure(data=[go.Candlestick(x=kr_C.index, open=kr_O.values, high=kr_H.values, low=kr_L.values, close=kr_C.values, name='국장 포트')])
                    fig_kr.add_hline(y=k_ath_val, line_dash="dash", line_color="gray", opacity=0.7)
                    fig_kr.add_hline(y=k_low_3m_val, line_dash="dash", line_color="gray", opacity=0.7)
                    fig_kr.add_hline(y=k_curr_val, line_dash="dash", line_color="red", opacity=0.7)
                    fig_kr.add_annotation(x=k_ath_date, y=k_ath_val, text=f"🚩 국장 고점: {k_ath_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=0, ay=-45, bgcolor="white", bordercolor="gray")
                    fig_kr.add_annotation(x=k_curr_date, y=k_curr_val, text=f"🔴 현재가: {k_curr_val/10000:,.0f}만원", showarrow=True, arrowhead=1, ax=-70, ay=0, bgcolor="white", bordercolor="red")
                    fig_kr.update_yaxes(tickformat=",.0f")
                    fig_kr.update_xaxes(tickformat="%Y년 %m월 %d일", hoverformat="%Y년 %m월 %d일", rangeslider_visible=False, rangebreaks=[dict(bounds=["sat", "mon"])])
                    fig_kr.update_layout(xaxis_range=[k_z_start, k_l_date], yaxis_range=[k_min_y, k_max_y], margin=dict(l=0, r=0, t=30, b=0), height=500)
                    for d in first_days_month: 
                        if d in first_days_year: fig_kr.add_vline(x=d, line_dash="solid", line_color="black", line_width=1.5, opacity=0.8)
                        else: fig_kr.add_vline(x=d, line_dash="dot", line_color="rgba(150,150,150,0.5)", line_width=1)
                    st.plotly_chart(fig_kr, use_container_width=True)
                else:
                    st.info("현재 국장(KR) 종목을 보유하고 있지 않습니다.")

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
