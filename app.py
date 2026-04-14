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
# 1. 포트폴리오 정의 (총 15종목)
# ==========================================
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
# 2. 앱 화면 구성 & 상단 구글시트 차트
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

# --- 입력 영역 ---
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
    placeholder="예: 10 5 3 0 10 50 15 20 5 10 5 8 10 200 50"
)

# ★ 가격, 등락률, 전일 종가를 모두 가져오는 함수
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

        if prev_close > 0 and current_price > 0:
            change_pct = ((current_price - prev_close) / prev_close) * 100
        else:
            change_pct = 0.0

        return current_price, change_pct, prev_close
    except:
        return 0, 0.0, 0

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

    with st.spinner('실시간 시세 및 수익률 계산 중... (약 10초 소요)'):
        
        try: exchange_rate = yf.Ticker("KRW=X").history(period="1d")['Close'].iloc[-1]
        except: exchange_rate = 1400 
        
        current_stock_assets = 0
        total_today_profit = 0
        total_prev_asset = input_cash # 어제 총 자산 (현금은 그대로라고 가정)

        stock_data_cache = [] 

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
            
            # 오늘 종목별 수익금 계산
            today_profit = my_amt - prev_amt_krw
            
            current_stock_assets += my_amt
            total_today_profit += today_profit
            total_prev_asset += prev_amt_krw
            
            stock_data_cache.append({
                "price_krw": price_krw, 
                "price_usd": price_usd, 
                "my_amt": my_amt,
                "change_pct": change_pct,
                "today_profit": today_profit
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

        st.success(f"**📊 현재 총 자산:** {total_asset:,.0f}원")
        st.write("---")

        # ==========================================
        # 테이블 데이터 생성
        # ==========================================
        stock_rows = []
        total_buy_cost = 0 
        budget_invest = total_asset * 0.63  

        for i, p in enumerate(all_stocks):
            cached = stock_data_cache[i]
            price_krw = cached['price_krw']
            price_usd = cached['price_usd']
            my_amt = cached['my_amt']
            change_pct = cached['change_pct']
            today_profit = cached['today_profit']
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

            # 등락률 및 수익금 텍스트 포맷팅
            change_str = f"▲ {change_pct:.2f}%" if change_pct > 0 else (f"▼ {abs(change_pct):.2f}%" if change_pct < 0 else "-")
            profit_str = f"▲ {today_profit:,.0f}원" if today_profit > 0 else (f"▼ {abs(today_profit):,.0f}원" if today_profit < 0 else "-")

            stock_rows.append({
                "구분": category, "종목": p['name'], "현재가($)": price_display, "현재가(₩)": f"{price_krw:,.0f}원", 
                "등락률": change_str, "오늘수익": profit_str,
                "목표비중(전체)": display_target_ratio, "실제비중": current_ratio,
                "목표금액": actual_target_cost, "목표금액(표시)": actual_target_cost,
                "목표수량": int(target_qty), "내보유": int(my_qty), "실행": action,
            })

        # 종목 표 정렬
        df_stocks = pd.DataFrame(stock_rows).sort_values(by='목표금액', ascending=False)

        # 잔여현금 행 생성
        remaining_cash = total_asset - total_buy_cost
        cash_row = pd.DataFrame([{
            "구분": "💵 잔여현금", "종목": "예수금 (KRW)", "현재가($)": "-", "현재가(₩)": "-", "등락률": "-", "오늘수익": "-",
            "목표비중(전체)": 0.21, "실제비중": input_cash / total_asset,
            "목표금액": remaining_cash, "목표금액(표시)": remaining_cash,
            "목표수량": int(remaining_cash), "내보유": int(input_cash),
            "실행": f"예상잔고: {remaining_cash:,.0f}원",
        }])

        # 총합계 행 생성 (맨 아래)
        tot_pct_str = f"▲ {total_daily_return_pct:.2f}%" if total_daily_return_pct > 0 else (f"▼ {abs(total_daily_return_pct):.2f}%" if total_daily_return_pct < 0 else "-")
        tot_profit_str = f"▲ {total_today_profit:,.0f}원" if total_today_profit > 0 else (f"▼ {abs(total_today_profit):,.0f}원" if total_today_profit < 0 else "-")
        
        total_row = pd.DataFrame([{
            "구분": "📊 포트폴리오 총합", "종목": "전체 자산 (현금포함)", "현재가($)": "-", "현재가(₩)": "-", "등락률": tot_pct_str, "오늘수익": tot_profit_str,
            "목표비중(전체)": 1.0, "실제비중": 1.0,
            "목표금액": total_asset, "목표금액(표시)": total_asset,
            "목표수량": "-", "내보유": "-", "실행": "-"
        }])

        # 데이터프레임 병합 (주식들 -> 현금 -> 총합)
        df_final = pd.concat([df_stocks, cash_row, total_row], ignore_index=True)
        
        # 스타일링 함수들
        def style_dataframe(row):
            bg_color = 'white'
            if row['구분'] == '💵 잔여현금': bg_color = '#FFECB3'
            elif row['구분'] == '현금성ETF': bg_color = '#FFF9C4'
            elif row['구분'] == '국장(투자)': bg_color = '#E3F2FD'
            elif row['구분'] == '미장(투자)': bg_color = '#FCE4EC'
            elif row['구분'] == '📊 포트폴리오 총합': bg_color = '#E8EAF6' # 옅은 보라색 강조
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

        # 출력
        st.dataframe(
            df_final.style.apply(style_dataframe, axis=1)
                    .map(style_text_color, subset=['실행'])
                    .map(style_change_color, subset=['등락률', '오늘수익']) 
                    .format({"목표비중(전체)": "{:.1%}", "실제비중": "{:.1%}", "목표금액(표시)": "{:,.0f}원", "내보유": "{}", "목표수량": "{}"}),
            column_order=["구분", "종목", "현재가($)", "현재가(₩)", "등락률", "오늘수익", "목표비중(전체)", "실제비중", "목표금액(표시)", "목표수량", "내보유", "실행"],
            hide_index=True, use_container_width=True, height=900
        )

    # ==========================================
    # 3. 3개월 과거 시뮬레이션 차트
    # ==========================================
    with st.spinner("최근 3개월 시뮬레이션 데이터 불러오는 중..."):
        try:
            tickers = [p['ticker'] for p in all_stocks]
            if "KRW=X" not in tickers: tickers.append("KRW=X")
            
            # 과거 3개월 데이터 쫙 끌어오기
            df_hist = yf.download(tickers, period="3mo", progress=False)
            
            if isinstance(df_hist.columns, pd.MultiIndex): close_hist = df_hist['Close']
            else: close_hist = df_hist

            # 비어있는 날짜(휴일 등) 앞뒤 가격으로 채우기
            close_hist = close_hist.ffill().bfill()
            
            # 매일매일의 내 총자산(기본으로 현금부터 깔아둠)
            total_history = pd.Series(input_cash, index=close_hist.index)
            
            for i, p in enumerate(all_stocks):
                qty = user_holdings[i]
                if qty > 0:
                    tkr = p['ticker']
                    if p['country'] == "US":
                        asset_val = close_hist[tkr] * close_hist['KRW=X'] * qty
                    else:
                        asset_val = close_hist[tkr] * qty
                    total_history += asset_val
                    
            st.subheader("📉 최근 3개월 내 자산 시뮬레이션")
            st.caption("※ 현재 보유한 주식 수량을 3개월 전부터 그대로 들고 있었다고 가정했을 때의 포트폴리오 가치 변화입니다.")
            
            # 차트 그리기
            st.line_chart(total_history)
            
        except Exception as e:
            st.warning(f"3개월 차트 데이터를 불러오는 데 실패했습니다. (야후 파이낸스 접속 지연 등)")
