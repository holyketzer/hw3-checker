import importlib.util
import json
import os
import sys
import traceback

import requests
import uuid

from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
from unittest.mock import patch, Mock

CBR_CURRENCY_BASE_DAILY_FILE = "cbr_currency_base_daily.html"
CBR_KEY_INDICATORS_FILE = "cbr_key_indicators.html"
UPLOAD_FOLDER = "uploads/"
EXPECTED_FILE = "expected.json"
EPSILON = 10e-8
ENCODING = "utf-8"

def _read_file(path):
    with open(path, "r") as f:
        return f.read()

CBR_CURRENCY_BASE_DAILY = _read_file(CBR_CURRENCY_BASE_DAILY_FILE)
CBR_KEY_INDICATORS = _read_file(CBR_KEY_INDICATORS_FILE)
EXPECTED = json.loads(_read_file(EXPECTED_FILE))

# import pdb; pdb.set_trace()

app = Flask(__name__, static_url_path="/static")

@app.route("/status")
def status():
    return { "status": "ok" }

@app.route("/")
def root():
    return render_template(
        'index.html',
    )

@app.route("/score", methods=["POST"])
def score():
    try:
        file = request.files["file"]
        filename = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + ".py")
        file.save(filename)
        result = test_solution(filename)
        os.remove(filename)

        return render_template(
            'index.html',
            result=result,
        )
    except:
        return render_template(
            'index.html',
            error=str(format_error(sys.exc_info())),
        )

def test_solution(filename):
    spec = importlib.util.spec_from_file_location(os.path.basename(filename).replace(".py", ""), filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    web_app = module.app
    test_client = web_app.test_client()
    parse_cbr_currency_base_daily = module.parse_cbr_currency_base_daily
    parse_cbr_key_indicators = module.parse_cbr_key_indicators

    res = {}
    res.update(test_parse(parse_cbr_currency_base_daily, CBR_CURRENCY_BASE_DAILY, "cbr_currency_base_daily"))
    res.update(test_parse(parse_cbr_key_indicators, CBR_KEY_INDICATORS, "cbr_key_indicators"))

    with patch.object(module.requests, 'get', new=http_get_mocker):
        actual_responses = EXPECTED["requests"]
        response_res = []

        for i, (url, status_code, expected_response) in enumerate(actual_responses):
            # import pdb; pdb.set_trace()

            try:
                actual_response = test_client.get(url)
                actual_status_code = actual_response.status_code

                try:
                    actual_response = json.loads(actual_response.data.decode(actual_response.charset))
                except json.decoder.JSONDecodeError:
                    actual_response = actual_response.data.decode(actual_response.charset)

                if status_code != actual_status_code or (status_code == 200 and not isinstance(expected_response, str) and not json_is_same(expected_response, actual_response)):
                    response_res.append(
                        {
                            "url": url,
                            "actual": { "status": actual_status_code, "response": actual_response},
                            "expected": { "status": status_code, "response": expected_response},
                        }
                    )
                else:
                    response_res.append(
                        {
                            "url": url,
                            "actual": {
                                "status": actual_status_code,
                                "response": actual_response,
                            },
                        }
                    )
            except:
                response_res.append({"url": url, "error": format_error(sys.exc_info())})

        res["requests"] = response_res

    res["requests"].append(
        test_cbr_503("/cbr/daily", test_client, module.requests, http_get_mocker_with_500, "CBR 500")
    )
    res["requests"].append(
        test_cbr_503("/cbr/key_indicators", test_client, module.requests, http_get_mocker_with_500, "CBR 500")
    )
    res["requests"].append(
        test_cbr_503("/cbr/daily", test_client, module.requests, http_get_mocker_with_exception, "ConnectionError")
    )
    res["requests"].append(
        test_cbr_503("/cbr/key_indicators", test_client, module.requests, http_get_mocker_with_exception, "ConnectionError")
    )

    res["requests"].append(test_cbr_404("/api/asset/invalid_route", test_client))

    return res

def json_is_same(expected, actual):
    if type(expected) != type(actual):
        return False

    if isinstance(expected, int) or isinstance(expected, float):
        return abs(expected - actual) < EPSILON

    if isinstance(expected, str):
        return expected == actual

    if isinstance(expected, dict):
        expected_keys = set(expected.keys())
        actual_keys = set(actual.keys())

        if expected_keys != actual_keys:
            return False

        for key in expected_keys:
            if not json_is_same(expected[key], actual[key]):
                return False

    return True

def format_error(e):
    return "\n".join([str(e[1]), traceback.format_exc()]).replace("\n", "</br>")

def test_parse(func, source, expected_key):
    error = None
    test_res = "ok"

    try:
        actual = func(source)

        if not json_is_same(EXPECTED[expected_key], actual):
            return {
                expected_key: {
                    "expected": EXPECTED[expected_key],
                    "actual": actual,
                }
            }
    except:
        error = str(format_error(sys.exc_info()))

    if error:
        return { expected_key: { "error": error } }
    else:
        return { expected_key: { "actual": actual } }

def test_cbr_503(url, test_client, module_requests, mock_func, desc):
    expected = {
        "status": 503,
        "response": "CBR service is unavailable",
    }

    try:
        with patch.object(module_requests, 'get', new=mock_func):
            actual_response = test_client.get(url)

            actual = {
                "status": actual_response.status_code,
                "response": actual_response.data.decode(actual_response.charset),
            }

            if expected != actual:
                return { "expected": expected, "actual": actual, "url": f"{url} {desc}" }
            else:
                return { "actual": actual, "url": f"{url} {desc}" }
    except:
        error = str(format_error(sys.exc_info()))
        return { "error": error, "url": f"{url} {desc}" }

def test_cbr_404(url, test_client):
    expected = {
        "status": 404,
        "response": "This route is not found",
    }

    try:
        actual_response = test_client.get(url)

        actual = {
            "status": actual_response.status_code,
            "response": actual_response.data.decode(actual_response.charset),
        }

        if expected != actual:
            return { "expected": expected, "actual": actual, "url": url }
        else:
            return { "actual": actual, "url": url }
    except:
        error = str(format_error(sys.exc_info()))
        return { "error": error, "url": url }


def http_get_mocker(url, allow_redirects=True, **kwargs):
    html = None

    if "currency_base/daily" in url:
        html = CBR_CURRENCY_BASE_DAILY
    elif "key-indicators" in url:
        html = CBR_KEY_INDICATORS
    else:
        raise Exception(f'Unexpected request {url}')

    return Mock(
        status_code=200,
        ok=True,
        text=html,
        content=html.encode(ENCODING),
        encoding=ENCODING,
    )

def http_get_mocker_with_500(url, allow_redirects=True, **kwargs):
    return Mock(
        status_code=500,
        ok=False,
        text="Something went wrong"
    )

def http_get_mocker_with_exception(url, allow_redirects=True, **kwargs):
    return Mock(
        side_effect=ConnectionError("something when wrong")
    )
