#!/usr/bin/env python3
"""Bounded retries for idempotent maintenance GETs, never for issue writes."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
            redirected.remove_header('Authorization')
        return redirected


OPEN = urllib.request.build_opener(SafeRedirect()).open


def retry_delay(headers, attempt):
    value = headers.get('Retry-After')
    if value:
        try:
            return max(0, float(value))
        except ValueError:
            return max(0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
    if headers.get('X-RateLimit-Remaining') == '0' and headers.get('X-RateLimit-Reset'):
        return max(0, float(headers['X-RateLimit-Reset']) - time.time()) + 1
    return min(2 ** attempt, 30)


def get_bytes(url, attempts=5, timeout=30, max_wait=120):
    if attempts < 1:
        raise ValueError('attempts must be positive')
    headers = {'User-Agent': 'Action-Build-Plus-maintenance', 'Accept': 'application/json'}
    token = os.environ.get('GH_TOKEN')
    if token and urllib.parse.urlsplit(url).hostname == 'api.github.com':
        headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(url, headers=headers)
    for attempt in range(attempts):
        try:
            with OPEN(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            limited = exc.code == 403 and (exc.headers.get('Retry-After') or exc.headers.get('X-RateLimit-Remaining') == '0')
            if exc.code not in (408, 429, 500, 502, 503, 504) and not limited:
                raise
            if attempt == attempts - 1:
                raise
            wait = retry_delay(exc.headers, attempt)
            exc.close()
            # Never retry earlier than a long Retry-After; fail explicitly instead.
            if wait > max_wait:
                raise RuntimeError(f'Upstream asks to wait {wait:.0f}s; exceeds bounded retry budget') from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == attempts - 1:
                raise
            wait = min(2 ** attempt, 30)
        time.sleep(wait)
    raise RuntimeError('GET attempts exhausted')


def get_json(url):
    return json.loads(get_bytes(url))
