import pandas as pd
import requests

# CoinGecko API에서 상위 100위 코인 리스트 가져오는 함수
def get_top_100_coins():
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',  # 시가총액 기준 내림차순 정렬
        'per_page': 200,  # 100개만 가져오기
        'page': 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    top_100_coins = [coin['symbol'].upper() + 'USDT' for coin in data]  # 'USDT'와 결합하여 거래쌍 형식으로 반환
    return top_100_coins

# Binance API에서 데이터 가져오는 함수
def get_binance_data(symbol, interval='1d'):
    url = f'https://api.binance.com/api/v1/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': 1000
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    # 데이터를 pandas DataFrame으로 변환
    ohlcv_data = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
    ohlcv_data['timestamp'] = pd.to_datetime(ohlcv_data['timestamp'], unit='ms')
    ohlcv_data['close'] = ohlcv_data['close'].astype(float)
    ohlcv_data['low'] = ohlcv_data['low'].astype(float)
    
    return ohlcv_data

# 10일선 아래로 떨어진 적이 없고, 2024년 이후 최저점이 2024년 이전 최저점보다 높은 코인 필터링
def filter_coins(coin_list):
    valid_coins = []
    
    for coin in coin_list:
        try:
            data = get_binance_data(coin)
            data['MA10'] = data['close'].rolling(window=10).mean()
            
            # 최근 7일 동안 10일선 아래로 떨어진 적이 있는지 확인
            recent_data = data.tail(7)
            if any(recent_data['low'] < recent_data['MA10']):
                continue  # 10일선 아래로 떨어진 적이 있으면 제외
            
            # 2024년 이전 데이터와 이후 데이터로 분리
            data_2024_before = data[data['timestamp'] < '2024-01-01']
            data_2024_after = data[data['timestamp'] >= '2024-01-01']
            
            # 2024년 이전 최저점 구하기
            min_before_2024 = data_2024_before['low'].min() if not data_2024_before.empty else float('inf')
            
            # 2024년 이후 최저점 구하기
            min_after_2024 = data_2024_after['low'].min() if not data_2024_after.empty else float('inf')
            
            # 2024년 이후 최저점이 2024년 이전 최저점보다 높은지 확인
            if min_after_2024 > min_before_2024:
                valid_coins.append(coin)
                
        except Exception as e:
            print(f"Error with {coin}: {e}")
    
    return valid_coins

# 상위 100위 코인 목록을 가져옴
top_100_coins = get_top_100_coins()

# 상위 100위 코인에 대해 필터링 적용
valid_coins = filter_coins(top_100_coins)

# 결과 출력
print(f"조건을 만족하는 코인들: {valid_coins}")
print(f"조건을 만족하는 코인 개수: {len(valid_coins)}")
