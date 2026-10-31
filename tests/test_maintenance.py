"""Offline, bounded retry and no-false-success regression tests."""
from email.message import Message
from email.utils import format_datetime
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import http_get
import maintenance


def error(code, **headers):
    message = Message()
    for key, value in headers.items():
        message[key.replace('_', '-')] = str(value)
    return HTTPError('https://example.invalid', code, 'fixture', message, io.BytesIO())


class RetryTests(unittest.TestCase):
    def test_429_retry_after_then_success(self):
        with patch.object(http_get, 'OPEN', side_effect=[error(429, Retry_After=3), io.BytesIO(b'ok')]) as request, patch.object(http_get.time, 'sleep') as sleep:
            self.assertEqual(http_get.get_bytes('https://example.invalid'), b'ok')
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(3)

    def test_continuous_429_is_failure_not_empty_response(self):
        with patch.object(http_get, 'OPEN', side_effect=lambda *a, **k: (_ for _ in ()).throw(error(429))) as request, patch.object(http_get.time, 'sleep') as sleep:
            with self.assertRaises(HTTPError):
                http_get.get_bytes('https://example.invalid', attempts=3)
            self.assertEqual(request.call_count, 3)
            self.assertEqual(sleep.call_count, 2)

    def test_network_error_then_503_then_success(self):
        with patch.object(http_get, 'OPEN', side_effect=[URLError('fixture'), error(503), io.BytesIO(b'ok')]), patch.object(http_get.time, 'sleep'):
            self.assertEqual(http_get.get_bytes('https://example.invalid'), b'ok')

    def test_404_and_regular_403_not_retried(self):
        for code in (404, 403):
            with patch.object(http_get, 'OPEN', side_effect=error(code)) as request, patch.object(http_get.time, 'sleep') as sleep:
                with self.assertRaises(HTTPError):
                    http_get.get_bytes('https://example.invalid')
                self.assertEqual(request.call_count, 1)
                sleep.assert_not_called()

    def test_rate_limited_403_is_retried(self):
        with patch.object(http_get, 'OPEN', side_effect=[error(403, Retry_After=1), io.BytesIO(b'ok')]), patch.object(http_get.time, 'sleep'):
            self.assertEqual(http_get.get_bytes('https://example.invalid'), b'ok')

    def test_long_retry_after_fails_without_retrying_too_early(self):
        with patch.object(http_get, 'OPEN', side_effect=error(429, Retry_After=600)) as request, patch.object(http_get.time, 'sleep') as sleep:
            with self.assertRaises(RuntimeError):
                http_get.get_bytes('https://example.invalid')
            self.assertEqual(request.call_count, 1)
            sleep.assert_not_called()

    def test_http_date_retry_after_supported(self):
        headers = {'Retry-After': format_datetime(datetime.now(timezone.utc) + timedelta(seconds=30))}
        self.assertTrue(28 <= http_get.retry_delay(headers, 0) <= 31)

    def test_token_only_sent_to_github_api(self):
        requests = []
        def capture(request, **kwargs):
            requests.append(request)
            return io.BytesIO(b'{}')
        with patch.dict(os.environ, {'GH_TOKEN': 'fixture-not-a-secret'}), patch.object(http_get, 'OPEN', side_effect=capture):
            for url in ('https://api.github.com/repos/x/y', 'https://gitlab.com/api/v4/x', 'https://codeload.github.com/x/y'):
                http_get.get_json(url)
        self.assertIsNotNone(requests[0].get_header('Authorization'))
        self.assertTrue(all(r.get_header('Authorization') is None for r in requests[1:]))

    def test_cross_origin_redirect_drops_authorization(self):
        request = Request('https://api.github.com/x', headers={'Authorization': 'fixture'})
        redirected = http_get.SafeRedirect().redirect_request(request, None, 302, 'found', {}, 'https://example.invalid/x')
        self.assertIsNone(redirected.get_header('Authorization'))


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.versions = json.loads((ROOT / 'config/versions.json').read_text())

    def test_same_pins_need_no_update(self):
        values = [{'commit': {'id': item['commit']}} if key == 'susfs' else
                  {'sha': item['commit'], 'html_url': 'https://example.invalid/commit'}
                  for key, item in self.versions.items() if isinstance(item, dict)]
        with patch.object(maintenance, 'get_json', side_effect=values):
            self.assertEqual(maintenance.collect_updates(self.versions), [])

    def test_upstream_failure_never_edits_or_closes_issue(self):
        with patch.object(maintenance, 'get_json', side_effect=URLError('fixture')), patch.object(maintenance, 'sync_issue') as sync:
            self.assertEqual(maintenance.main(), 1)
            sync.assert_not_called()

    def test_invalid_commit_is_not_reported_as_current(self):
        with patch.object(maintenance, 'get_json', return_value={'sha': None, 'html_url': 'fixture'}):
            with self.assertRaises((ValueError, TypeError)):
                maintenance.collect_updates(self.versions)

    def test_changed_upstream_is_reported(self):
        versions = {'bakasu': self.versions['bakasu']}
        with patch.object(maintenance, 'get_json', return_value={'sha': 'a' * 40, 'html_url': 'https://example.invalid/a'}):
            updates = maintenance.collect_updates(versions)
            self.assertEqual(len(updates), 1)
            self.assertIn('aaaaaaaa', updates[0])

    def test_issue_write_failure_propagates_without_retry(self):
        with patch.object(maintenance, 'gh', side_effect=['[{"number": 3, "body": "old"}]', RuntimeError('write failed')]) as gh:
            with self.assertRaises(RuntimeError):
                maintenance.sync_issue('owner/repo', ['new'])
            self.assertEqual(gh.call_count, 2)


if __name__ == '__main__':
    unittest.main()
