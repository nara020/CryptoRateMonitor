import requests
from flask import Flask, render_template, request
import math
import datetime

app = Flask(__name__)

BASE_URL = "https://api.binance.com/api/v3"

# K 단위로 변환하는 함수
def format_number(number):
    if number is None:
        return None
    if number >= 1_000_000:
        return f"{round(number / 1_000_000, 2)}M"
    elif number >= 1_000:
        return f"{round(number / 1_000, 2)}k"
    else:
        return str(number)

# 모든 심볼 가져오기 (상장 폐지된 코인 제외)
def get_all_symbols():
    try:
        response = requests.get(f"{BASE_URL}/exchangeInfo")
        response.raise_for_status()  # 상태 코드가 200이 아닌 경우 예외 발생
        return [
            market["symbol"] for market in response.json()["symbols"]
            if market["status"] == "TRADING" and market["symbol"].endswith("USDT")
        ]
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return []

# 캔들 데이터 가져오기
def fetch_kline_data(symbol, interval="1d", start_time=None, end_time=None):
    try:
        params = {"symbol": symbol, "interval": interval}
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
        response = requests.get(f"{BASE_URL}/klines", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching kline data for {symbol}: {e}")
        return None

# 현재 가격 가져오기
def fetch_current_price(symbol):
    try:
        response = requests.get(f"{BASE_URL}/ticker/price", params={"symbol": symbol})
        response.raise_for_status()
        return float(response.json()["price"])
    except Exception as e:
        print(f"Error fetching current price for {symbol}: {e}")
        return None

def get_listing_date(symbol):
    try:
        response = requests.get(f"{BASE_URL}/exchangeInfo", params={"symbol": symbol})
        response.raise_for_status()
        data = response.json()
        listing_date_str = data['symbols'][0]['firstTradeTime']  # 'firstTradeTime' 값 확인
        if listing_date_str:
            return datetime.datetime.utcfromtimestamp(listing_date_str / 1000)
    except Exception as e:
        print(f"Error fetching listing date for {symbol}: {e}")
    return None

# 수익률 계산 함수
def calculate_percentage(numerator, denominator):
    if numerator is not None and denominator is not None and denominator != 0:
        return round(((numerator / denominator) - 1) * 100, 2)
    return None

# 데이터 분석 함수
def calculate_metrics(symbol):
    now = datetime.datetime.utcnow()
    start_2023 = datetime.datetime(2023, 1, 1)

    # 전체 데이터 가져오기
    all_data = fetch_kline_data(symbol)
    if not all_data:
        return None

    # 상장 일자
    listing_date = get_listing_date(symbol)
    if not listing_date:
        listing_date = now  # 상장일을 알 수 없으면 현재 시간을 사용

    # A: 상장 시점부터 2023년 1월 1일 이전 최저가
    pre_2023_data = fetch_kline_data(symbol, end_time=start_2023)
    lowest_price_pre_2023 = None
    lowest_price_pre_2023_date = None
    if pre_2023_data:
        lowest_pre_2023 = min(pre_2023_data, key=lambda x: float(x[3]))
        lowest_price_pre_2023 = round(float(lowest_pre_2023[3]), 2)
        lowest_price_pre_2023_date = datetime.datetime.utcfromtimestamp(lowest_pre_2023[0] / 1000).strftime("%Y-%m-%d")

    # B: 2023년 1월 1일 이전 최고가
    highest_price_pre_2023 = None
    highest_price_pre_2023_date = None
    if pre_2023_data:
        highest_pre_2023 = max(pre_2023_data, key=lambda x: float(x[2]))
        highest_price_pre_2023 = round(float(highest_pre_2023[2]), 2)
        highest_price_pre_2023_date = datetime.datetime.utcfromtimestamp(highest_pre_2023[0] / 1000).strftime("%Y-%m-%d")

    # C: 2023년 1월 1일 이후 최저가
    post_2023_data = fetch_kline_data(symbol, start_time=start_2023)
    lowest_price_post_2023 = None
    lowest_price_post_2023_date = None
    if post_2023_data:
        lowest_post_2023 = min(post_2023_data, key=lambda x: float(x[3]))
        lowest_price_post_2023 = round(float(lowest_post_2023[3]), 2)
        lowest_price_post_2023_date = datetime.datetime.utcfromtimestamp(lowest_post_2023[0] / 1000).strftime("%Y-%m-%d")

    # D: C 날짜 이후 최고가
    highest_price_post_C = None
    highest_price_post_C_date = None
    if lowest_post_2023:
        c_date = datetime.datetime.utcfromtimestamp(lowest_post_2023[0] / 1000)  # C 날짜
        post_C_data = fetch_kline_data(symbol, start_time=c_date)
        if post_C_data:
            highest_post_C = max(post_C_data, key=lambda x: float(x[2]))
            highest_price_post_C = round(float(highest_post_C[2]), 2)
            highest_price_post_C_date = datetime.datetime.utcfromtimestamp(highest_post_C[0] / 1000).strftime("%Y-%m-%d")

    # E: D 날짜 이후 최저가
    lowest_price_post_D = None
    lowest_price_post_D_date = None
    if highest_post_C:
        d_date = datetime.datetime.utcfromtimestamp(highest_post_C[0] / 1000)  # D 날짜
        post_D_data = fetch_kline_data(symbol, start_time=d_date)
        if post_D_data:
            lowest_post_D = min(post_D_data, key=lambda x: float(x[3]))
            lowest_price_post_D = round(float(lowest_post_D[3]), 2)
            lowest_price_post_D_date = datetime.datetime.utcfromtimestamp(lowest_post_D[0] / 1000).strftime("%Y-%m-%d")

    # F: 현재 가격
    current_price = fetch_current_price(symbol)
    if current_price is not None:
        current_price = round(current_price, 2)

    metrics = {
        "symbol": symbol,
        "listing_date": listing_date.strftime("%Y-%m-%d"),
        "lowest_price_pre_2023": format_number(lowest_price_pre_2023),
        "highest_price_pre_2023": format_number(highest_price_pre_2023),
        "lowest_price_post_2023": format_number(lowest_price_post_2023),
        "highest_price_post_2023": format_number(highest_price_post_C),
        "lowest_price_post_2023_after_D": format_number(lowest_price_post_D),
        "current_price": format_number(current_price),
        "lowest_price_pre_2023_date": lowest_price_pre_2023_date,
        "highest_price_pre_2023_date": highest_price_pre_2023_date,
        "lowest_price_post_2023_date": lowest_price_post_2023_date,
        "highest_price_post_2023_date": highest_price_post_C_date,
        "lowest_price_post_2023_after_D_date": lowest_price_post_D_date,
        "current_price_date": now.strftime("%Y-%m-%d"),
        "percentage_increase_pre_2023": calculate_percentage(highest_price_pre_2023, lowest_price_pre_2023) if highest_price_pre_2023 else None,
        "percentage_decrease_post_2023": calculate_percentage(lowest_price_post_2023, highest_price_pre_2023) if lowest_price_post_2023 else None,
        "percentage_increase_post_2023": calculate_percentage(highest_price_post_C, lowest_price_post_2023) if highest_price_post_C else None,
        "percentage_decrease_post_2024": calculate_percentage(lowest_price_post_D, highest_price_post_C) if lowest_price_post_D else None,
        "percentage_increase_current": calculate_percentage(current_price, lowest_price_post_D) if current_price and lowest_price_post_D else None,
    }
    print(f"{symbol}: {metrics}")
    return metrics


# 예시 호출 (이 부분은 사용자가 추가할 수 있습니다)
symbol = "BTCUSDT"
metrics = calculate_metrics(symbol)



@app.route("/", methods=["GET"])
def home():
    search_symbol = request.args.get("symbol")
    page = int(request.args.get("page", 1))  # 현재 페이지 (기본값은 1)
    items_per_page = 30  # 한 페이지에 보여줄 항목 수

    all_metrics = []
    try:
        symbols = get_all_symbols()
        total_symbols = len(symbols)  # 총 코인 데이터 수
        
        if search_symbol:
            symbols = [s for s in symbols if search_symbol.upper() in s]
        
        # 30개씩 나누어 처리
        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page

        for symbol in symbols[start_index:end_index]:
            metrics = calculate_metrics(symbol)
            if metrics:
                all_metrics.append(metrics)

        # 총 페이지 수 계산
        total_pages = math.ceil(len(symbols) / items_per_page)

    except Exception as e:
        return f"<h1>오류 발생: {e}</h1>"

    return render_template("home.html", data=all_metrics, total_pages=total_pages, current_page=page, total_symbols=total_symbols)

if __name__ == "__main__":
    app.run(debug=True)
