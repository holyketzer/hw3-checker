import importlib.util
import json
import os
import sys
import traceback

import requests
import uuid

from flask import Flask, request, render_template
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

CBR_CURRENCY_BASE_DAILY_FILE = "cbr_currency_base_daily.html"
CBR_KEY_INDICATORS_FILE = "cbr_key_indicators.html"
UPLOAD_FOLDER = "uploads/"
EXPECTED_FILE = "expected.json"

def _read_file(path):
    with open(path, "r") as f:
        return f.read()

CBR_CURRENCY_BASE_DAILY = _read_file(CBR_CURRENCY_BASE_DAILY_FILE)
CBR_KEY_INDICATORS = _read_file(CBR_KEY_INDICATORS_FILE)
EXPECTED = json.loads(_read_file(EXPECTED_FILE))

# import pdb; pdb.set_trace()

load_dotenv(verbose=True)

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

        return render_template(
            'index.html',
            filename=filename,
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

    actual_responses = EXPECTED["requests"]
    response_res = []

    for i, (url, status_code, expected_response) in enumerate(actual_responses):
        try:
            actual_response = test_client.get(url)
            actual_status_code = actual_response.status_code

            try:
                actual_response = json.loads(actual_response.data.decode(actual_response.charset))
            except json.decoder.JSONDecodeError:
                actual_response = actual_response.data.decode(actual_response.charset)

            if status_code != actual_status_code or (status_code == 200 and not isinstance(expected_response, str) and expected_response != actual_response):
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
    return res

def format_error(e):
    return "\n".join([str(e[1]), traceback.format_exc()]).replace("\n", "</br>")

def test_parse(func, source, expected_key):
    error = None
    test_res = "ok"

    try:
        actual = func(source)

        if actual != EXPECTED[expected_key]:
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