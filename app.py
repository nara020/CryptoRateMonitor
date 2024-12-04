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

# 필터링된 코인 목록
FILTERED_COINS = ['XRPUSDT', 'AVAXUSDT', 'XLMUSDT', 'DOTUSDT', 'LINKUSDT', 'UNIUSDT', 'ICPUSDT', 'FILUSDT', 'ALGOUSDT', 'VETUSDT', 'TIAUSDT', 'IMXUSDT', 'STXUSDT', 'OPUSDT', 'INJUSDT', 'THETAUSDT', 'FTMUSDT', 'GALAUSDT', 'MKRUSDT', 'LDOUSDT', 'FLOWUSDT', 'ENSUSDT']

# 캔들 데이터 가져오기
def fetch_kline_data(symbol, interval="1d", start_time=None, end_time=None):
    try:
        params = {"symbol": symbol, "interval": interval, "limit": 1000}
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
        response = requests.get(f"{BASE_URL}/klines", params=params)
        response.raise_for_status()
        data = response.json()
        
        # 데이터 로그에 출력 (날짜 포함)
        for entry in data:
            timestamp = datetime.datetime.utcfromtimestamp(entry[0] / 1000)  # 타임스탬프 변환
        
        return data
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

# 수익률 계산 함수
def calculate_percentage(numerator, denominator):
    if numerator is not None and denominator is not None and denominator != 0:
        return round(((numerator / denominator) - 1) * 100, 2)
    return None

# 데이터 분석 함수
def calculate_metrics(symbol):
    now = datetime.datetime.utcnow()
    start_2023 = datetime.datetime(2023, 1, 1)

    # A: 상장 시점부터 2023년 1월 1일 이전 최저가
    print(f"Fetching data for {symbol} before 2023...")
    pre_2023_data = fetch_kline_data(symbol, end_time=start_2023)
    lowest_price_pre_2023 = None
    highest_price_pre_2023 = None

    # 2023년 이전 데이터가 있는지 확인
    if pre_2023_data:
        lowest_pre_2023 = min(pre_2023_data, key=lambda x: float(x[3]))  # x[3]은 low
        highest_pre_2023 = max(pre_2023_data, key=lambda x: float(x[2]))  # x[2]은 high
        lowest_price_pre_2023 = round(float(lowest_pre_2023[3]), 2)
        # B: 2023년 1월 1일 이전 최고가 
        highest_price_pre_2023 = round(float(highest_pre_2023[2]), 2)
    else:
        print(f"2023년 이전 데이터가 없습니다: {symbol}")



    # B: 2023년 1월 1일 이후 최저가
    print(f"Fetching data for {symbol} after 2023...")
    post_2023_data = fetch_kline_data(symbol, start_time=start_2023)
    lowest_price_post_2023 = None
    if post_2023_data:
        lowest_post_2023 = min(post_2023_data, key=lambda x: float(x[3]))  # x[3]은 low
        lowest_price_post_2023 = round(float(lowest_post_2023[3]), 2)
    else:
        print(f"2023년 이후 데이터가 없습니다: {symbol}")

    # C: 2023년 1월 1일 이후 최고가
    highest_price_post_C = None
    if lowest_post_2023:
        c_date = datetime.datetime.utcfromtimestamp(lowest_post_2023[0] / 1000)  # C 날짜
        print(f"Fetching data for {symbol} after {c_date}...")
        post_C_data = fetch_kline_data(symbol, start_time=c_date)
        if post_C_data:
            highest_post_C = max(post_C_data, key=lambda x: float(x[2]))  # x[2]은 high
            highest_price_post_C = round(float(highest_post_C[2]), 2)

    # D: C 날짜 이후 최저가
    lowest_price_post_D = None
    if highest_post_C:
        d_date = datetime.datetime.utcfromtimestamp(highest_post_C[0] / 1000)  # D 날짜
        print(f"Fetching data for {symbol} after {d_date}...")
        post_D_data = fetch_kline_data(symbol, start_time=d_date)
        if post_D_data:
            print(f"Data for {symbol} after {d_date} fetched successfully!")
            lowest_post_D = min(post_D_data, key=lambda x: float(x[3]))  # x[3]은 low
            lowest_price_post_D = round(float(lowest_post_D[3]), 2)

    # F: 현재 가격
    print(f"Fetching current price for {symbol}...")
    current_price = fetch_current_price(symbol)
    if current_price is not None:
        print(f"Current price for {symbol}: {current_price}")
        current_price = round(current_price, 2)

    metrics = {
        "symbol": symbol,
        "lowest_price_pre_2023": format_number(lowest_price_pre_2023),
        "highest_price_pre_2023": format_number(highest_price_pre_2023),
        "lowest_price_post_2023": format_number(lowest_price_post_2023),
        "highest_price_post_2023": format_number(highest_price_post_C),
        "lowest_price_post_2023_after_D": format_number(lowest_price_post_D),
        "current_price": format_number(current_price),
        "percentage_increase_pre_2023": calculate_percentage(highest_price_pre_2023, lowest_price_pre_2023) if highest_price_pre_2023 else None,
        "percentage_decrease_post_2023": calculate_percentage(lowest_price_post_2023, highest_price_pre_2023) if lowest_price_post_2023 else None,
        "percentage_increase_post_2023": calculate_percentage(highest_price_post_C, lowest_price_post_2023) if highest_price_post_C else None,
        "percentage_decrease_post_2024": calculate_percentage(lowest_price_post_D, highest_price_post_C) if lowest_price_post_D else None,
        "percentage_increase_current": calculate_percentage(current_price, lowest_price_post_D) if current_price and lowest_price_post_D else None,
    }

    print(f"Metrics for {symbol}: {metrics}")
    return metrics


@app.route("/", methods=["GET"])
def home():
    search_symbol = request.args.get("symbol")
    page = int(request.args.get("page", 1))  # 현재 페이지 (기본값은 1)
    items_per_page = 50  # 한 페이지에 보여줄 항목 수

    all_metrics = []
    try:
        total_symbols = len(FILTERED_COINS)  # 필터링된 코인 데이터 수
        
        if search_symbol:
            filtered_coins = [s for s in FILTERED_COINS if search_symbol.upper() in s]
        else:
            filtered_coins = FILTERED_COINS
        
        # 30개씩 나누어 처리
        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page

        for symbol in filtered_coins[start_index:end_index]:
            metrics = calculate_metrics(symbol)
            if metrics:
                all_metrics.append(metrics)

        # 총 페이지 수 계산
        total_pages = math.ceil(len(filtered_coins) / items_per_page)

    except Exception as e:
        return f"<h1>오류 발생: {e}</h1>"

    return render_template("home.html", data=all_metrics, total_pages=total_pages, current_page=page, total_symbols=total_symbols)

if __name__ == "__main__":
    app.run(debug=True)
