from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import time
import requests

app = Flask(__name__)
CORS(app) # Разрешаем расширению обращаться к серверу

# ВСТАВЬТЕ ВАШИ ДАННЫЕ ИЗ ALIEXPRESS PORTALS
APP_KEY = "ВАШ_APP_KEY"
SECRET_KEY = "ВАШ_SECRET_KEY"
TRACKING_ID = "ВАШ_TRACKING_ID"

def generate_signature(params, secret):
    # Логика подписи запроса AliExpress
    sorted_params = sorted(params.items())
    query_string = "".join(f"{k}{v}" for k, v in sorted_params)
    signature = hashlib.md5((secret + query_string + secret).encode('utf-8')).hexdigest().upper()
    return signature

@app.route('/api/check-price', methods=['GET'])
def check_price():
    query = request.args.get('q')
    ebay_price = float(request.args.get('ebay_price', 0))

    if not query:
        return jsonify({"found": False, "error": "No query"})

    # Параметры для API AliExpress (aliexpress.ds.product.get)
    params = {
        "method": "aliexpress.affiliate.product.query",
        "app_key": APP_KEY,
        "format": "json",
        "v": "2.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "sign_method": "md5",
        "keywords": query,
        "tracking_id": TRACKING_ID,
        "page_size": "1",
        "sort": "LAST_VOLUME_DESC" # Сортировка по популярности
    }

    params["sign"] = generate_signature(params, SECRET_KEY)
    
    try:
        response = requests.get("https://api-sg.aliexpress.com/sync", params=params)
        data = response.json()
        
        # Парсим результат
        result = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {}).get("products", {}).get("product", [])
        
        if result:
            product = result[0]
            ali_price = float(product.get("target_sale_price"))
            
            # Проверяем выгоду: показываем только если Ali дешевле хотя бы на 5%
            if ali_price < (ebay_price * 0.95):
                return jsonify({
                    "found": True,
                    "ali_price": ali_price,
                    "affiliate_link": product.get("promotion_link"),
                    "savings": round(ebay_price - ali_price, 2)
                })
        
        return jsonify({"found": False})

    except Exception as e:
        return jsonify({"found": False, "error": str(e)})

# Для локального запуска
if __name__ == "__main__":
    app.run(debug=True)
