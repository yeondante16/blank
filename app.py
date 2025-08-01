# app.py
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import copy

# --- 페이지 설정 ---
st.set_page_config(
    page_title="세계 무역 게임: 초콜릿을 향한 여정",
    page_icon="🍫",
    layout="wide",
)

# --- API 정보 ---
# Streamlit의 Secrets 관리 기능을 통해 API 키를 안전하게 불러옵니다.
try:
    API_KEY = st.secrets["API_KEY"]
    # API 호출을 위한 URL (API_KEY를 포함하여 완성)
    API_URL = f"https://www.koreaexim.go.kr/site/program/financial/exchangeJSON?authkey={API_KEY}&searchdate={{date}}&data=AP01"
except (KeyError, FileNotFoundError):
    st.error("API 키를 찾을 수 없습니다. Streamlit Cloud의 Secrets에 API_KEY를 정확히 설정했는지 확인해주세요.")
    st.stop()


# --- 함수 정의 ---
@st.cache_data(ttl=3600) # 1시간 동안 캐시 유지
def fetch_exchange_rates():
    """한국수출입은행 API를 호출하여 최신 환율 정보를 가져옵니다."""
    today_str = datetime.now().strftime('%Y%m%d')
    url = API_URL.format(date=today_str)
    try:
        response = requests.get(url)
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        data = response.json()
        
        if not data: # 주말 등 데이터가 없는 경우
            return {"error": "은행 영업일이 아니라서 최신 환율 정보를 가져올 수 없습니다. 기본 환율로 게임을 시작합니다."}

        rates = {'KRW': 1} # 원화 기준
        for item in data:
            if item['cur_unit'] == 'USD':
                rates['USD'] = float(item['tts'].replace(',', ''))
            elif item['cur_unit'] == 'JPY(100)':
                rates['JPY'] = float(item['tts'].replace(',', '')) / 100
            elif item['cur_unit'] == 'CNH':
                rates['CNY'] = float(item['tts'].replace(',', ''))
        
        return rates
    except requests.exceptions.RequestException as e:
        return {"error": f"API 요청 중 오류가 발생했습니다: {e}"}
    except (KeyError, ValueError):
        return {"error": "환율 데이터 처리 중 오류가 발생했습니다. API 응답 형식을 확인해주세요."}

def convert_currency(amount, from_currency, to_currency, rates):
    """환율에 따라 통화를 변환합니다."""
    if from_currency not in rates or to_currency not in rates:
        return None

    # 모든 통화를 KRW 기준으로 변환 후 계산
    amount_in_krw = amount * rates[from_currency]
    converted_amount = amount_in_krw / rates[to_currency]
    return converted_amount

def initialize_game():
    """세션 상태를 초기화하여 게임을 설정합니다."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        
        # 기본 환율 정보 (API 실패 시 사용)
        base_rates = {'KRW': 1, 'USD': 1400, 'JPY': 9, 'CNY': 195}
        fetched_rates = fetch_exchange_rates()

        if "error" in fetched_rates:
            st.warning(fetched_rates["error"])
            st.session_state.rates = base_rates
        else:
            st.session_state.rates = fetched_rates
        
        st.session_state.original_rates = copy.deepcopy(st.session_state.rates)
        st.session_state.news_active = False

        # 각 나라별 초기 자원 및 자금 설정
        st.session_state.countries = {
            "한국 🇰🇷": {"자원": ["쌀 🍚", "전자제품 📱"], "자금": {"KRW": 50000}},
            "미국 🇺🇸": {"자원": ["밀 🌾", "카카오 🍫"], "자금": {"USD": 30}},
            "일본 🇯🇵": {"자원": ["자동차 🚗", "우유 🥛"], "자금": {"JPY": 5000}},
            "중국 🇨🇳": {"자원": ["장난감 🧸", "설탕 🧂"], "자금": {"CNY": 250}},
        }
        
        # 거래 기록을 저장할 데이터프레임
        st.session_state.transactions = pd.DataFrame(columns=[
            "시간", "파는 나라", "사는 나라", "거래 물품", "수량", "거래 금액", "통화"
        ])

# --- 앱 UI 구성 ---
initialize_game()

st.title("🍫 세계 무역 게임: 초콜릿을 향한 여정")
st.info("우리 반이 작은 '세계'가 되어 흥미진진한 무역 게임을 해봅시다! 목표는 '카카오', '설탕', '우유'를 모아 초콜릿을 만드는 것입니다.")

# 탭 구성
tab1, tab2, tab3, tab4 = st.tabs(["게임 현황", "🏦 중앙은행 (환율 & 환전)", "✍️ 무역 활동 기록하기", "📊 거래 내역 보기"])

with tab1:
    st.header("🌍 우리들의 나라 현황")
    st.write("각 나라가 현재 가지고 있는 자원과 자금을 확인하세요.")
    
    cols = st.columns(len(st.session_state.countries))
    for i, (country, data) in enumerate(st.session_state.countries.items()):
        with cols[i]:
            st.subheader(country)
            st.write("**보유 자원:**")
            st.write(" ".join(data["자원"]))
            st.write("**보유 자금:**")
            for currency, amount in data["자금"].items():
                st.write(f"- {amount:,.2f} {currency}")

with tab2:
    st.header("🏦 중앙은행")
    
    # 긴급 뉴스 (선생님용)
    with st.expander("📢 긴급 뉴스 (선생님용)"):
        news_toggle = st.toggle("긴급 뉴스 활성화", value=st.session_state.news_active, key="news_toggle_key")
        
        if news_toggle:
            st.session_state.news_active = True
            st.warning("긴급 뉴스가 발동되었습니다! 아래에 새로운 환율을 입력해주세요.")
            
            new_rates_cols = st.columns(3)
            with new_rates_cols[0]:
                st.session_state.rates['USD'] = st.number_input("1달러(USD)는 몇 원?", value=st.session_state.rates['USD'], format="%.2f")
            with new_rates_cols[1]:
                st.session_state.rates['JPY'] = st.number_input("1엔(JPY)은 몇 원?", value=st.session_state.rates['JPY'], format="%.2f")
            with new_rates_cols[2]:
                st.session_state.rates['CNY'] = st.number_input("1위안(CNY)은 몇 원?", value=st.session_state.rates['CNY'], format="%.2f")
        else:
            if st.session_state.news_active:
                st.session_state.news_active = False
                st.session_state.rates = copy.deepcopy(st.session_state.original_rates)
                st.success("긴급 뉴스가 종료되고, 환율이 원래대로 돌아왔습니다.")

    # 환율 정보판
    st.subheader("📈 현재 환율 정보 (1단위당 원화 가치)")
    if st.session_state.news_active:
        st.info("긴급 뉴스에 따라 변경된 환율이 적용 중입니다.")
    else:
        st.info("실시간 환율 정보입니다. (1시간마다 갱신)")

    rate_cols = st.columns(len(st.session_state.rates) -1)
    rate_items = [item for item in st.session_state.rates.items() if item[0] != 'KRW']
    
    for i, (currency, rate) in enumerate(rate_items):
        with rate_cols[i]:
            st.metric(label=f"1 {currency}", value=f"{rate:,.2f} KRW")

    # 환전 계산기
    st.subheader("💱 환전 계산기")
    calc_cols = st.columns([2, 1, 1, 0.5, 2])
    with calc_cols[0]:
        amount_to_convert = st.number_input("바꿀 금액", min_value=0.0, step=100.0, format="%.2f")
    with calc_cols[1]:
        from_curr = st.selectbox("어떤 돈을?", list(st.session_state.rates.keys()), key="from_curr")
    with calc_cols[2]:
        to_curr = st.selectbox("어떤 돈으로?", list(st.session_state.rates.keys()), key="to_curr")
    
    with calc_cols[4]:
        if amount_to_convert > 0:
            converted = convert_currency(amount_to_convert, from_curr, to_curr, st.session_state.rates)
            st.markdown(f"### 👉 **{converted:,.2f} {to_curr}**")

with tab3:
    st.header("✍️ 무역 활동 기록하기")
    st.write("다른 나라와 물건을 사고 팔았다면, 아래에 거래 내역을 정확히 기록해주세요.")

    with st.form(key="trade_form", clear_on_submit=True):
        form_cols = st.columns(2)
        with form_cols[0]:
            seller = st.selectbox("파는 나라", options=list(st.session_state.countries.keys()))
            item = st.text_input("거래 물품 (예: 카카오)")
            price = st.number_input("거래 금액", min_value=0.0, step=1.0, format="%.2f")
        with form_cols[1]:
            buyer = st.selectbox("사는 나라", options=list(st.session_state.countries.keys()))
            quantity = st.number_input("수량", min_value=1, step=1)
            currency = st.selectbox("사용한 통화", options=list(st.session_state.rates.keys()))
        
        submit_button = st.form_submit_button(label="거래 기록하기")

        if submit_button:
            if seller == buyer:
                st.error("파는 나라와 사는 나라는 같을 수 없습니다.")
            else:
                # 자금 변동 계산
                buyer_funds = st.session_state.countries[buyer]["자금"]
                seller_funds = st.session_state.countries[seller]["자금"]

                # 구매자 자금을 거래 통화로 환산하여 잔액 확인
                buyer_total_krw = sum(convert_currency(amt, cur, 'KRW', st.session_state.rates) for cur, amt in buyer_funds.items())
                price_in_krw = convert_currency(price, currency, 'KRW', st.session_state.rates)

                if buyer_total_krw < price_in_krw:
                    st.error(f"{buyer}의 자금이 부족하여 거래할 수 없습니다!")
                else:
                    # 거래 성공: 자금 및 자원 업데이트
                    # 구매자 자금 차감
                    if currency in buyer_funds:
                        if buyer_funds[currency] >= price:
                            buyer_funds[currency] -= price
                        else: # 해당 통화가 부족하면 다른 통화에서 환전하여 차감
                            needed_in_krw = convert_currency(price - buyer_funds[currency], currency, 'KRW', st.session_state.rates)
                            buyer_funds[currency] = 0
                            # 다른 통화에서 차감 (여기서는 단순화를 위해 KRW에서 우선 차감)
                            if 'KRW' in buyer_funds:
                                buyer_funds['KRW'] -= needed_in_krw
                            # (실제로는 복잡한 로직 필요, 수업에서는 개념 이해가 중요하므로 단순화)

                    else: # 구매자가 해당 통화를 아예 가지고 있지 않은 경우
                        buyer_funds['KRW'] -= price_in_krw

                    # 판매자 자금 추가
                    if currency in seller_funds:
                        seller_funds[currency] += price
                    else:
                        seller_funds[currency] = price
                    
                    # 자원 이동
                    new_item_str = f"{item} {quantity}개"
                    st.session_state.countries[buyer]["자원"].append(new_item_str)
                    
                    # 거래 기록 추가
                    new_transaction = pd.DataFrame([{
                        "시간": datetime.now().strftime('%H:%M:%S'),
                        "파는 나라": seller,
                        "사는 나라": buyer,
                        "거래 물품": item,
                        "수량": quantity,
                        "거래 금액": price,
                        "통화": currency
                    }])
                    st.session_state.transactions = pd.concat([st.session_state.transactions, new_transaction], ignore_index=True)
                    st.success("거래가 성공적으로 기록되었습니다!")


with tab4:
    st.header("📊 모든 거래 내역")
    st.write("지금까지 우리들이 한 모든 무역 활동의 기록입니다.")
    
    st.dataframe(st.session_state.transactions, use_container_width=True)

    # CSV 다운로드 기능
    csv = st.session_state.transactions.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="거래 기록 다운로드 (CSV 파일)",
        data=csv,
        file_name='세계무역게임_거래기록.csv',
        mime='text/csv',
    )
    st.info("수업이 끝난 후, 이 파일을 내려받아 우리의 무역 활동을 함께 분석해봅시다!")
