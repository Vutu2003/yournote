"""Local OAuth lifecycle, protected storage and races with fully fake upstreams."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import httpx

from backend.services.chatgpt_auth import ChatGPTConnections
from backend.services.chatgpt_oauth import OAuthTokenError, PLAN_SCOPE
from backend.services.chatgpt_storage import Tokens
from src.errors import LLMErrorCode, LLMServiceError


class MemoryVault:
    mode = 'memory'
    def __init__(self, host): self.values = {}
    def get(self, key): return self.values.get(key)
    def set(self, key, tokens): self.values[key] = tokens
    def delete(self, key): self.values.pop(key, None); return True
    def close(self): self.values.clear()


class FakeOAuth:
    def __init__(self):
        self.exchanges = []
        self.revokes = []
        self.subject = 'subject-1'
        self.scopes = 'openid ' + PLAN_SCOPE
        self.failure = None
    def discovery(self): return {'authorization_endpoint': 'https://auth.openai.com/api/accounts/authorize'}
    def exchange(self, fields):
        self.exchanges.append(fields)
        if self.failure: raise self.failure
        return {'access_token': 'access-sentinel', 'refresh_token': 'refresh-sentinel', 'id_token': 'id-sentinel',
                'expires_in': 3600, 'scope': self.scopes, 'token_type': 'Bearer'}
    def verify_identity(self, token, client_id, nonce): return {'sub': self.subject, 'email': 'student@example.com'}
    def revoke(self, client_id, refresh): self.revokes.append((client_id, refresh)); return True


class ConnectionsTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix='chatgpt-test-')))
        self.oauth = FakeOAuth()
        self.manager = ChatGPTConnections(self.root, vault_factory=MemoryVault, oauth=self.oauth)
        self.addCleanup(self.manager.close)

    def start(self, connection_id=None):
        result = self.manager.start('browser', connection_id)
        pending = self.manager.pending
        self.addCleanup(pending.close)
        self.assertTrue(result['launch_path'].startswith('/api/ai/'))
        self.manager.launch('browser', pending.ticket)
        return pending

    def connect(self):
        pending = self.start()
        self.assertTrue(self.manager.callback(pending, {'state': pending.state, 'code': 'code-sentinel', 'client_id': 'oaiapp_test'}))
        return pending.connection_id

    def test_callback_and_pkce_keep_tokens_out_of_public_status_and_manifest(self):
        pending = self.start()
        query = parse_qs(urlparse(pending.authorization_url).query)
        self.assertEqual(query['client_id'], ['dynamic_agent_client'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertEqual(query['redirect_uri'], [pending.redirect_uri])
        self.assertNotIn(pending.verifier, pending.authorization_url)
        self.assertTrue(self.manager.callback(pending, {'state': pending.state, 'code': 'code-sentinel', 'client_id': 'oaiapp_test'}))
        public = json.dumps(self.manager.status('browser'))
        disk = (self.root / 'registrations.json').read_text()
        for private in ('access-sentinel', 'refresh-sentinel', 'id-sentinel', 'code-sentinel', pending.verifier):
            self.assertNotIn(private, public)
            self.assertNotIn(private, disk)
        self.assertFalse(self.manager.status('browser')['profiles'][0]['inference_checked'])
        self.assertFalse(self.manager.status('browser')['profiles'][0]['catalog_checked'])

    def test_wrong_expired_and_replayed_callback_never_exchange(self):
        pending = self.start()
        with self.assertRaises(LLMServiceError):
            self.manager.callback(pending, {'state': 'wrong', 'code': 'code'})
        self.assertEqual(self.oauth.exchanges, [])
        pending.expires_at = time.time() - 1
        with self.assertRaises(LLMServiceError):
            self.manager.callback(pending, {'state': pending.state, 'code': 'code'})
        pending.expires_at = time.time() + 60
        self.assertTrue(self.manager.callback(pending, {'state': pending.state, 'code': 'code', 'client_id': 'oaiapp_test'}))
        with self.assertRaises(LLMServiceError):
            self.manager.callback(pending, {'state': pending.state, 'code': 'code', 'client_id': 'oaiapp_test'})
        self.assertEqual(len(self.oauth.exchanges), 1)

    def test_registration_is_retained_when_exchange_fails_and_reused(self):
        self.oauth.failure = OAuthTokenError(True)
        pending = self.start()
        self.assertFalse(self.manager.callback(pending, {'state': pending.state, 'code': 'expired', 'client_id': 'oaiapp_retained'}))
        profile_id = next(iter(self.manager.store.profiles))
        self.assertIsNone(self.manager.store.active_id)
        returning = self.start(profile_id)
        query = parse_qs(urlparse(returning.authorization_url).query)
        self.assertEqual(query['client_id'], ['oaiapp_retained'])
        self.assertNotIn('agent_name_hint', query)
        self.assertEqual(len(self.manager.store.profiles), 1)

    def test_identity_only_login_does_not_enable_catalog_or_inference(self):
        self.oauth.scopes = 'openid email'
        connection_id = self.connect()
        profile = self.manager.status('browser')['profiles'][0]
        self.assertEqual(profile['state'], 'permission_required')
        with self.assertRaises(LLMServiceError) as caught:
            self.manager.access(connection_id)
        self.assertEqual(caught.exception.code, LLMErrorCode.PERMISSION_REQUIRED)

    def test_returning_account_and_client_mismatch_do_not_replace_credentials(self):
        connection_id = self.connect()
        pending = self.start(connection_id)
        self.assertFalse(self.manager.callback(pending, {'state': pending.state, 'code': 'code', 'client_id': 'oaiapp_other'}))
        self.assertEqual(len(self.oauth.exchanges), 1)
        pending = self.start(connection_id)
        self.oauth.subject = 'another-person'
        self.assertFalse(self.manager.callback(pending, {'state': pending.state, 'code': 'code'}))
        self.assertEqual(self.manager.store.profiles[connection_id]['subject'], 'subject-1')

    def test_catalog_only_shows_listed_models_in_server_order_and_check_requires_catalog(self):
        connection_id = self.connect()
        payload = {'models': [{'slug': 'hidden', 'display_name': 'Hidden', 'visibility': 'hide'},
                              {'slug': 'second', 'display_name': 'Second', 'visibility': 'list'},
                              {'slug': 'first', 'display_name': 'First', 'visibility': 'list'}]}
        factory = lambda: httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload)))
        with patch('backend.services.chatgpt_auth.new_client', side_effect=factory):
            models = self.manager.catalog(connection_id)['models']
            self.assertEqual([item['slug'] for item in models], ['second', 'first'])
            with self.assertRaises(LLMServiceError) as caught:
                self.manager.check(connection_id, 'not-in-catalog')
        self.assertEqual(caught.exception.code, LLMErrorCode.MODEL_UNAVAILABLE)
        self.assertFalse(self.manager.status('browser')['profiles'][0]['inference_checked'])

    def test_catalog_exposes_only_advertised_safe_effort_levels(self):
        connection_id = self.connect()
        payload = {'models': [
            {'slug': 'reasoner', 'display_name': 'Reasoner', 'visibility': 'list',
             'supported_reasoning_levels': [{'effort':'high'}, {'effort':'low'}, {'effort':'unknown'}, {'effort':'high'}, None],
             'default_reasoning_level':'high'},
            {'slug':'plain', 'display_name':'Plain', 'visibility':'list'},
        ]}
        factory = lambda: httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload)))
        with patch('backend.services.chatgpt_auth.new_client', side_effect=factory):
            models = self.manager.catalog(connection_id)['models']
        self.assertEqual(models[0]['supported_reasoning_levels'], ['low', 'high'])
        self.assertEqual(models[0]['default_reasoning_level'], 'high')
        self.assertNotIn('supported_reasoning_levels', models[1])

    def test_refresh_is_serialized_and_rotated_tokens_are_stored(self):
        connection_id = self.connect()
        tokens = self.manager.vault.get(connection_id)
        tokens.expires_at = 0
        before = len(self.oauth.exchanges)
        exchange = self.oauth.exchange
        def rotate(fields):
            data = exchange(fields)
            data.update(access_token='rotated-access', refresh_token='rotated-refresh')
            data.pop('scope')  # Refresh may omit scope to retain the original grant.
            return data
        with patch.object(self.oauth, 'exchange', side_effect=rotate), ThreadPoolExecutor(2) as pool:
            values = list(pool.map(lambda _: self.manager.access(connection_id).get_secret_value(), range(2)))
        self.assertEqual(values, ['rotated-access', 'rotated-access'])
        self.assertEqual(self.manager.vault.get(connection_id).refresh, 'rotated-refresh')
        self.assertEqual(len(self.oauth.exchanges), before + 1)
        self.assertEqual(self.oauth.exchanges[-1]['client_id'], 'oaiapp_test')
        self.assertNotIn('scope', self.oauth.exchanges[-1])

    def test_temporary_refresh_failure_keeps_credentials_terminal_failure_clears(self):
        connection_id = self.connect()
        self.manager.vault.get(connection_id).expires_at = 0
        self.oauth.failure = OAuthTokenError(False)
        with self.assertRaises(LLMServiceError): self.manager.access(connection_id)
        self.assertIsNotNone(self.manager.vault.get(connection_id))
        self.oauth.failure = OAuthTokenError(True)
        with self.assertRaises(LLMServiceError): self.manager.access(connection_id)
        self.assertIsNone(self.manager.vault.get(connection_id))
        self.assertTrue(self.manager.store.profiles[connection_id]['signed_out'])

    def test_logout_during_refresh_does_not_restore_tokens(self):
        connection_id = self.connect()
        self.manager.vault.get(connection_id).expires_at = 0
        entered, release = Event(), Event()
        exchange = self.oauth.exchange
        def delayed(fields):
            entered.set()
            self.assertTrue(release.wait(5))
            return {**exchange(fields), 'refresh_token': 'newest-refresh'}
        with patch.object(self.oauth, 'exchange', side_effect=delayed), ThreadPoolExecutor(2) as pool:
            future = pool.submit(self.manager.access, connection_id)
            self.assertTrue(entered.wait(5))
            logout = pool.submit(self.manager.logout, connection_id)
            release.set()
            # The existing rotation may complete before sign-out fences it, but
            # nothing can be restored after logout has returned.
            future.result(timeout=5)
            result = logout.result(timeout=5)
        self.assertTrue(result['remote_revocation_confirmed'])
        self.assertEqual(self.oauth.revokes[-1][1], 'newest-refresh')
        self.assertIsNone(self.manager.vault.get(connection_id))
        self.assertTrue(self.manager.store.profiles[connection_id]['signed_out'])

    def test_cancel_during_code_exchange_does_not_activate_login(self):
        pending = self.start()
        entered, release = Event(), Event()
        exchange = self.oauth.exchange
        def delayed(fields):
            entered.set()
            self.assertTrue(release.wait(5))
            return exchange(fields)
        with patch.object(self.oauth, 'exchange', side_effect=delayed), ThreadPoolExecutor(1) as pool:
            future = pool.submit(self.manager.callback, pending, {'state': pending.state, 'code': 'code', 'client_id': 'oaiapp_test'})
            self.assertTrue(entered.wait(5))
            self.manager.cancel('browser')
            release.set()
            self.assertFalse(future.result(timeout=5))
        self.assertIsNone(self.manager.store.active_id)
        self.assertIsNone(self.manager.vault.get(pending.connection_id))

    def test_restart_reuses_host_registration_and_memory_sessions_do_not_persist(self):
        connection_id = self.connect()
        host = self.manager.store.host_id
        self.manager.close()
        self.manager = ChatGPTConnections(self.root, vault_factory=MemoryVault, oauth=self.oauth)
        self.assertEqual(self.manager.store.host_id, host)
        self.assertEqual(self.manager.store.profiles[connection_id]['client_id'], 'oaiapp_test')
        self.assertEqual(self.manager.status('browser')['profiles'][0]['state'], 'reconnect_required')
        self.manager.close()
        # The original cleanup is safe after close; do not retain runtime locks.

    def test_identity_only_without_access_token_still_shows_permission_required(self):
        pending = self.start()
        with patch.object(self.oauth, 'exchange', return_value={'id_token': 'id-sentinel', 'scope': 'openid email'}):
            self.assertTrue(self.manager.callback(pending, {'state': pending.state, 'code': 'code', 'client_id': 'oaiapp_test'}))
        self.assertEqual(self.manager.status('browser')['profiles'][0]['state'], 'permission_required')

    def test_real_loopback_callback_http_is_one_use_and_does_not_echo_code(self):
        pending = self.start()
        with httpx.Client(trust_env=False) as client:
            url = pending.redirect_uri
            response = client.get(url, params={'state': pending.state, 'code': 'code-sentinel', 'client_id': 'oaiapp_test'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('code-sentinel', response.text)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(len(self.oauth.exchanges), 1)

    def test_failed_manifest_commit_does_not_report_connected(self):
        pending = self.start()
        with patch.object(self.manager.store, 'save', side_effect=[None, OSError('private-storage-error')]):
            self.assertFalse(self.manager.callback(pending, {'state': pending.state, 'code': 'code', 'client_id': 'oaiapp_test'}))
        self.assertIsNone(self.manager.store.active_id)
        self.assertIsNone(self.manager.vault.get(pending.connection_id))
        self.assertEqual(self.manager.status('browser')['profiles'][0]['state'], 'reconnect_required')
