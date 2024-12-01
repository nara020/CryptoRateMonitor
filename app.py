import requests
from flask import Flask, render_template, request
import math

app = Flask(__name__)

BASE_URL = "https://api.binance.com/api/v3"

# 모든 심볼 가져오기 (상장 폐지된 코인 제외)
def get_all_symbols():
    response = requests.get(f"{BASE_URL}/exchangeInfo")
    if response.status_code == 200:
        return [
            market["symbol"] for market in response.json()["symbols"]
            if market["status"] == "TRADING" and market["symbol"].endswith("USDT")
        ]
    else:
        raise Exception("심볼 데이터를 가져오지 못했습니다.")

# 캔들 데이터 가져오기
def fetch_kline_data(symbol, interval="1d", start_time=None, end_time=None):
    params = {"symbol": symbol, "interval": interval}
    if start_time:
        params["startTime"] = int(start_time.timestamp() * 1000)
    if end_time:
        params["endTime"] = int(end_time.timestamp() * 1000)
    response = requests.get(f"{BASE_URL}/klines", params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# 현재 가격 가져오기
def fetch_current_price(symbol):
    response = requests.get(f"{BASE_URL}/ticker/price", params={"symbol": symbol})
    if response.status_code == 200:
        return float(response.json()["price"])
    else:
        return None

# 시가총액 가져오기
def fetch_market_cap(symbol):
    response = requests.get(f"{BASE_URL}/ticker/24hr", params={"symbol": symbol})
    if response.status_code == 200:
        data = response.json()
        return float(data["marketCap"]) if "marketCap" in data else None
    return None

# 데이터 분석
def calculate_metrics(symbol):
    import datetime
    now = datetime.datetime.utcnow()
    start_2023 = datetime.datetime(2023, 1, 1)

    # 전체 데이터 가져오기
    all_data = fetch_kline_data(symbol)
    if not all_data:
        return None

    # 상장 일자
    listing_date = datetime.datetime.utcfromtimestamp(all_data[0][0] / 1000)

    # 상장 이후 최저가
    lowest_all_time = min(all_data, key=lambda x: float(x[3]))
    lowest_price = round(float(lowest_all_time[3]), 2)

    # 2023년 이전 최고가
    pre_2023_data = fetch_kline_data(symbol, end_time=start_2023)
    highest_price_pre_2023 = None
    if pre_2023_data:
        highest_pre_2023 = max(pre_2023_data, key=lambda x: float(x[2]))
        highest_price_pre_2023 = round(float(highest_pre_2023[2]), 2)

    # 2023년 이후 최저가
    post_2023_data = fetch_kline_data(symbol, start_time=start_2023)
    lowest_price_post_2023 = None
    highest_price_post_2023 = None
    if post_2023_data:
        lowest_price_post_2023 = min(post_2023_data, key=lambda x: float(x[3]))
        highest_price_post_2023 = max(post_2023_data, key=lambda x: float(x[2]))
        lowest_price_post_2023 = round(float(lowest_price_post_2023[3]), 2)
        highest_price_post_2023 = round(float(highest_price_post_2023[2]), 2)

    # 현재 가격
    current_price = fetch_current_price(symbol)
    if current_price is not None:
        current_price = round(current_price, 2)

    # 수익률 계산
    def calculate_percentage(numerator, denominator):
        if numerator is not None and denominator is not None and denominator != 0:
            return round(((numerator / denominator) - 1) * 100, 2)
        return None

    metrics = {
        "symbol": symbol,
        "listing_date": listing_date.strftime("%Y-%m-%d"),
        "lowest_price_all_time": lowest_price,
        "highest_price_pre_2023": highest_price_pre_2023,
        "lowest_price_post_2023": lowest_price_post_2023,
        "highest_price_post_2023": highest_price_post_2023,
        "current_price": current_price,
        "percentage_increase_pre_2023": calculate_percentage(highest_price_pre_2023, lowest_price) if highest_price_pre_2023 else None,
        "percentage_decrease_post_2023": calculate_percentage(lowest_price_post_2023, highest_price_pre_2023) if lowest_price_post_2023 else None,
        "percentage_increase_post_2023": calculate_percentage(highest_price_post_2023, lowest_price_post_2023) if highest_price_post_2023 else None,
        "percentage_increase_current": calculate_percentage(current_price, lowest_price_post_2023) if current_price and lowest_price_post_2023 else None,
        "market_cap": fetch_market_cap(symbol)  # 시가총액 추가
    }

    # None 값이 있을 경우 해당 데이터를 제외
    if any(value is None for value in metrics.values()):
        return None

    return metrics

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
        
        # 50개씩 나누어 처리
        start_index = (page - 1) * items_per_page
        end_index = start_index + items_per_page

        for symbol in symbols[start_index:end_index]:
            metrics = calculate_metrics(symbol)
            if metrics:
                all_metrics.append(metrics)

        # 시가총액 순으로 정렬
        all_metrics = sorted(all_metrics, key=lambda x: x.get("market_cap", 0), reverse=True)

        # 총 페이지 수 계산
        total_pages = math.ceil(len(symbols) / items_per_page)

    except Exception as e:
        return f"<h1>오류 발생: {e}</h1>"

    return render_template("home.html", data=all_metrics, total_pages=total_pages, current_page=page, total_symbols=total_symbols)

if __name__ == "__main__":
    app.run(debug=True)