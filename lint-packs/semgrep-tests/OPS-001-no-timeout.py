import httpx
import requests


def f(url):
    # ruleid: eng-ai.ops-001.python-http-no-timeout
    requests.get(url)
    # ruleid: eng-ai.ops-001.python-http-no-timeout
    requests.post(url, json={})
    # ruleid: eng-ai.ops-001.python-http-no-timeout
    httpx.get(url)
    # ok: eng-ai.ops-001.python-http-no-timeout
    requests.get(url, timeout=5)
    # ok: eng-ai.ops-001.python-http-no-timeout
    httpx.post(url, json={}, timeout=5)
    # ok: eng-ai.ops-001.python-http-no-timeout
    requests.Session()
