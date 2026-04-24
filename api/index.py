import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import time
import requests

app = Flask(__name__)
CORS(app)

# Подтягиваем данные из настроек Vercel
APP_KEY = os.environ.get('ALI_APP_KEY')
SECRET_KEY = os.environ.get('ALI_SECRET_KEY')
TRACKING_ID = os.environ.get('ALI_TRACKING_ID')

def generate_signature(params, secret):
    # Фирменная подпись AliExpress
    sorted_params = sorted(params.items())
    query_string = "".join(f"{k}{v}" for k, v in sorted_params)
    return hashlib.md5((secret + query_string + secret).encode('utf-8')).hexdigest().upper()

@app.route('/api/check-price')
def check_price():
    query = request.args.get('q')
    ebay_price = request.args.get('ebay_price')

    if not APP_KEY or not SECRET_KEY:
        return jsonify({"found": False, "error": "API Keys missing"})

    params = {
        "method": "aliexpress.affiliate.product.query",
        "app_key": APP_KEY,
        "format": "json",
        "v": "2.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
        "sign_method": "md5",
        "keywords": query,
        "tracking_id": TRACKING_ID,
        "page_size": "1"
    }

    params["sign"] = generate_signature(params, SECRET_KEY)
    
    try:
        # Для режима Test используем глобальный эндпоинт
        response = requests.get("https://api-sg.aliexpress.com/sync", params=params, timeout=10)
        data = response.json()
        
        # Разбираем ответ
        res = data.get("aliexpress_affiliate_product_query_response", {}).get("resp_result", {}).get("result", {})
        products = res.get("products", {}).get("product", [])
        
        if products:
            item = products[0]
            ali_price = float(item.get("target_sale_price"))
            
            # Логика: показываем только если реально дешевле
            if ebay_price and ali_price < float(ebay_price):
                return jsonify({
                    "found": True,
                    "ali_price": ali_price,
                    "link": item.get("promotion_link"),
                    "savings": round(float(ebay_price) - ali_price, 2)
                })
        
        return jsonify({"found": False, "debug": "No products found on Ali"})
    except Exception as e:
        return jsonify({"found": False, "error": str(e)})
