import importlib.util
import json
import os

SOLUTION_FILE = "../hw-03-asset-web-service/task_emelyanov_alexandr_asset_web_service.py"
CBR_CURRENCY_BASE_DAILY_FILE = "cbr_currency_base_daily.html"
CBR_KEY_INDICATORS_FILE = "cbr_key_indicators.html"
OUTPUT_FILE = "expected.json"

REQUEST_LIST = [
    '/cbr/daily',
    '/cbr/key_indicators',
    '/api/asset/list',
    '/api/asset/add/USD/dollars/120.0/5.6',
    '/api/asset/add/EUR/euro/12.0/1.2',
    '/api/asset/add/Silver/Ag/50.5/10.1',
    '/api/asset/add/INR/Indian/10.5/99.1',
    '/api/asset/add/Yen/JPY/1.5/1.7',
    '/api/asset/add/Yen/JPY/1.5/1.7',
    '/api/asset/list',
    '/api/asset/get?name=dollars&name=euro&name=Unknown',
    '/api/asset/calculate_revenue?period=1&period=2&period=5',
    '/api/asset/cleanup',
    '/api/asset/list',
]

def _read_file(path):
    with open(path, "r") as f:
        return f.read()

CBR_CURRENCY_BASE_DAILY = _read_file(CBR_CURRENCY_BASE_DAILY_FILE)
CBR_KEY_INDICATORS = _read_file(CBR_KEY_INDICATORS_FILE)

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
