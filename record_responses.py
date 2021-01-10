import importlib.util
import json
import os

import requests

from unittest.mock import patch, Mock

SOLUTION_FILE = "../hw-03-asset-web-service/task_emelyanov_alexandr_asset_web_service.py"
CBR_CURRENCY_BASE_DAILY_FILE = "cbr_currency_base_daily.html"
CBR_KEY_INDICATORS_FILE = "cbr_key_indicators.html"
OUTPUT_FILE = "expected.json"

REQUEST_LIST = [
    '/cbr/daily',
    '/cbr/key_indicators',
    '/api/asset/list',
    '/api/asset/add/USD/US stocks/120.0/5.6',
    '/api/asset/add/EUR/Eurobonds/12.0/1.2',
    '/api/asset/add/Ag/Silver/50.5/10.1',
    '/api/asset/add/INR/Indian high-yield bonds/10.5/99.1',
    '/api/asset/add/JPY/Japanese Government Bond/1.5/1.7',
    '/api/asset/add/JPY/Japanese Government Bond/1.5/1.7',
    '/api/asset/list',
    '/api/asset/get?name=US stocks&name=Eurobonds&name=Unknown',
    '/api/asset/calculate_revenue?period=1&period=2&period=5',
    '/api/asset/cleanup',
    '/api/asset/list',
]

def _read_file(path):
    with open(path, "r") as f:
        return f.read()

CBR_CURRENCY_BASE_DAILY = _read_file(CBR_CURRENCY_BASE_DAILY_FILE)
CBR_KEY_INDICATORS = _read_file(CBR_KEY_INDICATORS_FILE)

def http_mocker(arg, **kwargs):
    html = None

    if "currency_base/daily" in arg:
        html = CBR_CURRENCY_BASE_DAILY
    elif "key-indicators" in arg:
        html = CBR_KEY_INDICATORS
    else:
        raise Exception(f"Unexpected request {arg}")

    return Mock(
        status_code=200,
        ok=True,
        text=html
    )

def main():
    spec = importlib.util.spec_from_file_location(os.path.basename(SOLUTION_FILE).replace(".py", ""), SOLUTION_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    web_app = module.app
    test_client = web_app.test_client()
    parse_cbr_currency_base_daily = module.parse_cbr_currency_base_daily
    parse_cbr_key_indicators = module.parse_cbr_key_indicators

    total = {}

    total["cbr_currency_base_daily"] = parse_cbr_currency_base_daily(CBR_CURRENCY_BASE_DAILY)
    total["cbr_key_indicators"] = parse_cbr_key_indicators(CBR_KEY_INDICATORS)

    with patch.object(requests, 'get', side_effect=http_mocker):
        req_res = []
        for url in REQUEST_LIST:
            response = test_client.get(url)
            try:
                req_res.append([url, response.status_code, json.loads(response.data.decode(response.charset))])
            except json.decoder.JSONDecodeError:
                req_res.append([url, response.status_code, response.data.decode(response.charset)])

        total["requests"] = req_res

    with open(OUTPUT_FILE, "w") as f:
        f.write(json.dumps(total))

if __name__ == "__main__":
    main()
    print("Recorded to", OUTPUT_FILE)
