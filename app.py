import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone

# ==========================================
# 🔑 구글 시트 연결 설정 (사용자님 링크로 변경하세요!)
# ==========================================
SHEET_CSV_URL = "여기에_시트_CSV_링크를_넣어주세요"
WEB_APP_URL = "여기에_웹앱_URL을_넣어주세요"

# ==========================================
# 1. 포트폴리오 정의 (총 15종목) + 삼성전자 고정
# ==========================================
SAMSUNG_TICKER = "005930.KS"
SAMSUNG_QTY = 41

fixed_portfolio = [
    {"name": "GLDM (금)",    "ticker": "GLDM", "ratio": 0.04, "country": "US"},
    {"name": "VTV (가치주)",  "ticker": "VTV",  "ratio": 0.04, "country": "US"},
    {"name": "TLT (장기채)",  "ticker": "TLT",  "ratio": 0.025, "country": "US"},
    {"name": "IEI (중기채)",  "ticker": "IEI",  "ratio": 0.015, "country": "US"},
    {"name": "SCHD (배당주)", "ticker": "SCHD", "ratio": 0.04, "country": "US"},
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
all_names = [item['name'].split()[0] for item in all_stocks] 

# ==========================================
# 2. 앱 화면 구성
# ==========================================
st.set_page_config(page_title="스마트 리밸런싱", page_icon="📈", layout="wide")
st.title("📈 내 자산 성장 대시보드 (63:16:21)")

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
                st.metric(label="구글 시트에 기록된 최근 총 자산", value=f"{int(last_asset):,.0f}원", delta=f"{int(diff):,.0f}원")
except Exception as e:
    st.caption("※ 시트 링크가 설정되지 않았거나 아직 데이터가 부족하여 기록 차트를 표시할 수 없습니다.")

st.write("---")

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
st.caption(f"**입력 순서 (총 15개, 삼성전자 제외):** {' → '.join(all_names)}")

holdings_input = st.text_input(
    "종목별 수량 (띄어쓰기로 구분)", 
    value=default_holdings,
    placeholder="예: 10 5 3 0 10 50 15 20 5 10 5 8 10 200 50"
)

def get_real_price_and_change(ticker, country):
    try:
        stock = yf.Ticker(ticker)
        try: prev_close = stock.fast_info['previous_close']
        except:
            hist = stock.history(period="5d")
            prev_close = hist['Close'].iloc[-2] if len(hist) >= 2 else 0

        if country == "KR":
            try: current_price = stock.fast_info['last_price']
            except: current_price = stock.history(period="1d")['Close'].iloc[-1]
        else:
            df = stock.history(period="1d", interval="1m", prepost=True)
            if not df.empty: current_price = df['Close'].iloc[-1]
            else: current_price = stock.fast_info.get('last_price', prev_close)

        if prev_close > 0 and current_price > 0: change_pct = ((current_price - prev_close) / prev_close) * 100
        else: change_pct = 0.0

        return current_price, change_pct, prev_close
    except: return 0, 0.0, 0

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

    with st.spinner('실시간 시세 및 수익률 계산 중...'):
        
        try: exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except: exchange_rate = 1400 
        
        current_stock_assets = 0
        total_today_profit = 0
        total_prev_asset = input_cash 
        stock_data_cache = [] 

        # 1. 삼성전자 계산
        sam_price, sam_change, sam_prev = get_real_price_and_change(SAMSUNG_TICKER, "KR")
        sam_amt = sam_price * SAMSUNG_QTY
        sam_profit = sam_amt - (sam_prev * SAMSUNG_QTY)
        
        current_stock_assets += sam_amt
        total_today_profit += sam_profit
        total_prev_asset += (sam_prev * SAMSUNG_QTY)

        # 2. 나머지 종목 계산
        for i, p in enumerate(all_stocks):
            price, change_pct, prev_close = get_real_price_and_change(p['ticker'], p['country'])
            
            if p['country'] == "US":
                price_krw = price * exchange_rate
                price_usd = price
                prev_amt_krw = prev_close * exchange_rate * user_holdings[i]
            else:
                price_krw = price
                price_usd = 0
                prev_amt_krw = prev_close * user_holdings[i]
            
            my_qty = user_holdings[i]
            my_amt = my_qty * price_krw
            today_profit = my_amt - prev_amt_krw
            
            current_stock_assets += my_amt
            total_today_profit += today_profit
            total_prev_asset += prev_amt_krw
            
            stock_data_cache.append({
                "price_krw": price_krw, "price_usd": price_usd, "my_amt": my_amt,
                "change_pct": change_pct, "today_profit": today_profit
            })

        total_asset = current_stock_assets + input_cash
        total_daily_return_pct = (total_today_profit / total_prev_asset) * 100 if total_prev_asset > 0 else 0

        if total_asset == 0:
            st.error("총 자산이 0원입니다.")
            st.stop()

        if "script.google.com" in WEB_APP_URL:
            try:
                kst = timezone(timedelta(hours=9))
                today_str = datetime.now(kst).strftime("%Y-%m-%d")
                requests.post(WEB_APP_URL, data={"date": today_str, "asset": int(total_asset)})
            except: pass

        # ★ 예산 완벽 분리: 전체 자산 vs 리밸런싱 대상 자산
        rebalance_budget = total_asset - sam_amt
        budget_invest = rebalance_budget * 0.63  

        st.success(f"**📊 현재 총 자산:** {total_asset:,.0f}원 (삼성전자 제외 리밸런싱 예산: {rebalance_budget:,.0f}원)")
        st.write("---")

        stock_rows = []
        total_buy_cost = 0 

        # 삼성전자 행
        sam_change_str = f"▲ {sam_change:.2f}%" if sam_change > 0 else (f"▼ {abs(sam_change):.2f}%" if sam_change < 0 else "-")
        sam_profit_str = f"▲ {sam_profit:,.0f}원" if sam_profit > 0 else (f"▼ {abs(sam_profit):,.0f}원" if sam_profit < 0 else "-")
        
        stock_rows.append({
            "종목": "🔒삼성전자 (고정)", "현재가($)": "-", "현재가(₩)": f"{sam_price:,.0f}원", 
            "등락률": sam_change_str, "오늘수익": sam_profit_str,
            "목표비중": "-", "실제비중": f"{(sam_amt/total_asset):.1%} (총자산)",
            "목표금액": "-", "실제금액": f"{sam_amt:,.0f}원",
            "목표수량": "-", "내보유": str(SAMSUNG_QTY), "실행": "🔒 매매불가",
            "등락률숫자": sam_change 
        })

        # 15개 종목 행
        for i, p in enumerate(all_stocks):
            cached = stock_data_cache[i]
            price_krw = cached['price_krw']
            price_usd = cached['price_usd']
            my_amt = cached['my_amt']
            change_pct = cached['change_pct']
            today_profit = cached['today_profit']
            my_qty = user_holdings[i]

            if i < 5: 
                target_amt = rebalance_budget * p['ratio']
                display_target_ratio = f"{p['ratio']:.1%}"
            else: 
                target_amt = budget_invest * p['ratio']
                display_target_ratio = f"{(0.63 * p['ratio']):.1%}"

            if price_krw > 0: target_qty = round(target_amt / price_krw)
            else: target_qty = 0
            
            actual_target_cost = target_qty * price_krw
            total_buy_cost += actual_target_cost
            
            # 실제비중 계산을 리밸런싱 예산 기준으로 통일!
            current_ratio = f"{(my_amt / rebalance_budget):.1%}" if rebalance_budget > 0 else "0.0%"

            diff = target_qty - my_qty
            if diff > 0: action = f"🔴 {int(diff)}주 매수"
            elif diff < 0: action = f"🔵 {int(abs(diff))}주 매도"
            else: action = "🟢 유지"

            price_display = f"${price_usd:,.2f}" if p['country'] == "US" else "-"
            change_str = f"▲ {change_pct:.2f}%" if change_pct > 0 else (f"▼ {abs(change_pct):.2f}%" if change_pct < 0 else "-")
            profit_str = f"▲ {today_profit:,.0f}원" if today_profit > 0 else (f"▼ {abs(today_profit):,.0f}원" if today_profit < 0 else "-")

            stock_rows.append({
                "종목": p['name'], "현재가($)": price_display, "현재가(₩)": f"{price_krw:,.0f}원", 
                "등락률": change_str, "오늘수익": profit_str,
                "목표비중": display_target_ratio, "실제비중": current_ratio,
                "목표금액": f"{actual_target_cost:,.0f}원", 
                "실제금액": f"{my_amt:,.0f}원",
                "목표수량": str(int(target_qty)), "내보유": str(int(my_qty)), "실행": action,
                "등락률숫자": change_pct 
            })

        # 등락률 내림차순 정렬 (오른 종목이 위로)
        df_stocks = pd.DataFrame(stock_rows).sort_values(by='등락률숫자', ascending=False).drop(columns=['등락률숫자'])

        # 잔여현금
        remaining_cash = rebalance_budget - total_buy_cost
        cash_row = pd.DataFrame([{
            "종목": "💵 예수금 (현금)", "현재가($)": "-", "현재가(₩)": "-", "등락률": "-", "오늘수익": "-",
            "목표비중": "21.0%", "실제비중": f"{(input_cash / rebalance_budget):.1%}" if rebalance_budget > 0 else "0.0%",
            "목표금액": f"{remaining_cash:,.0f}원", "실제금액": f"{input_cash:,.0f}원",
            "목표수량": "-", "내보유": str(int(input_cash)), "실행": f"예상잔고: {remaining_cash:,.0f}원"
        }])

        # 총합계
        tot_pct_str = f"▲ {total_daily_return_pct:.2f}%" if total_daily_return_pct > 0 else (f"▼ {abs(total_daily_return_pct):.2f}%" if total_daily_return_pct < 0 else "-")
        tot_profit_str = f"▲ {total_today_profit:,.0f}원" if total_today_profit > 0 else (f"▼ {abs(total_today_profit):,.0f}원" if total_today_profit < 0 else "-")
        
        total_row = pd.DataFrame([{
            "종목": "📊 포트폴리오 총합", "현재가($)": "-", "현재가(₩)": "-", "등락률": tot_pct_str, "오늘수익": tot_profit_str,
            "목표비중": "-", "실제비중": "-",
            "목표금액": "-", "실제금액": f"{total_asset:,.0f}원",
            "목표수량": "-", "내보유": "-", "실행": "-"
        }])

        df_final = pd.concat([df_stocks, cash_row, total_row], ignore_index=True)
        
        def style_dataframe(row):
            bg_color = 'white'
            if '포트폴리오 총합' in row['종목']: bg_color = '#E8EAF6' 
            return [f'background-color: {bg_color}'] * len(row)

        def style_change_color(val):
            val_str = str(val)
            if '▲' in val_str: return 'background-color: #CCFFCC; color: #2E7D32; font-weight: bold;'
            elif '▼' in val_str: return 'background-color: #FFD1DC; color: #C2185B; font-weight: bold;'
            return ''

        def style_text_color(val):
            color = 'black'
            if '매수' in str(val): color = '#D32F2F'
            elif '매도' in str(val): color = '#1976D2'
            return f'color: {color}; font-weight: bold;'

        # 가운데 정렬 및 핏 맞춤 (use_container_width=False)
        st.dataframe(
            df_final.style.apply(style_dataframe, axis=1)
                    .map(style_text_color, subset=['실행'])
                    .map(style_change_color, subset=['등락률', '오늘수익'])
                    .set_properties(**{'text-align': 'center'}),
            column_order=["종목", "현재가($)", "현재가(₩)", "등락률", "오늘수익", "목표비중", "실제비중", "목표금액", "실제금액", "목표수량", "내보유", "실행"],
            hide_index=True, 
            use_container_width=False, 
            height=900
        )

    # ==========================================
    # 3. 고급 차트 섹션
    # ==========================================
    with st.spinner("최근 3개월 시뮬레이션 및 차트 생성 중..."):
        try:
            tickers = [p['ticker'] for p in all_stocks] + ["KRW=X", SAMSUNG_TICKER]
            df_hist = yf.download(tickers, period="3mo", progress=False)
            
            def get_series(col):
                s = pd.Series(input_cash, index=df_hist.index) 
                s += df_hist[col][SAMSUNG_TICKER].ffill().bfill() * SAMSUNG_QTY
                for i, p in enumerate(all_stocks):
                    qty = user_holdings[i]
                    if qty > 0:
                        tkr = p['ticker']
                        if p['country'] == 'US': s += df_hist[col][tkr].ffill().bfill() * df_hist[col]['KRW=X'].ffill().bfill() * qty
                        else: s += df_hist[col][tkr].ffill().bfill() * qty
                return s

            hist_O = get_series('Open')
            hist_H = get_series('High')
            hist_L = get_series('Low')
            hist_C = get_series('Close')

            max_val = hist_H.max() * 1.05
            y_max = max(max_val, 52000000)

            st.write("---")
            st.subheader("📉 내 포트폴리오 3개월 과거 시뮬레이션")
            st.caption("※ 현재 수량을 3개월 전부터 들고 있었다고 가정한 총 자산 변화입니다. (Y축 최솟값 5천만원 고정)")

            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=hist_C.index, y=hist_C.values, mode='lines', name='총자산', line=dict(color='#1f77b4', width=3)))
            fig_line.update_layout(yaxis_range=[50000000, y_max], margin=dict(l=0, r=0, t=30, b=0), height=400)
            st.plotly_chart(fig_line, use_container_width=True)

            st.subheader("🕯️ 총 자산 캔들 차트")
            fig_candle = go.Figure(data=[go.Candlestick(x=hist_C.index,
                            open=hist_O.values, high=hist_H.values,
                            low=hist_L.values, close=hist_C.values)])
            fig_candle.update_layout(yaxis_range=[50000000, y_max], margin=dict(l=0, r=0, t=30, b=0), height=400)
            fig_candle.update_xaxes(rangeslider_visible=False) 
            st.plotly_chart(fig_candle, use_container_width=True)

            st.subheader("🍕 현재 자산 구성 비율 (파이 차트)")
            pie_data = []
            if sam_amt > 0: pie_data.append({"종목": "삼성전자", "금액": sam_amt})
            for i, p in enumerate(all_stocks):
                if stock_data_cache[i]['my_amt'] > 0:
                    pie_data.append({"종목": p['name'], "금액": stock_data_cache[i]['my_amt']})
            if input_cash > 0: pie_data.append({"종목": "예수금", "금액": input_cash})

            df_pie = pd.DataFrame(pie_data)
            fig_pie = px.pie(df_pie, values='금액', names='종목', hole=0.3)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=500)
            st.plotly_chart(fig_pie, use_container_width=True)

        except Exception as e:
            st.warning("차트 데이터를 불러오는 데 일시적인 문제가 발생했습니다.")
