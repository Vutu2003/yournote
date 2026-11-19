"""Signed JWT verification and loopback browser endpoint protections."""
import json
import time
import unittest
from unittest.mock import MagicMock, patch

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import httpx
import jwt

from backend.main import app
from backend.services.chatgpt_oauth import ISSUER, OpenAIOAuth
from backend.services.chatgpt_storage import CredentialVault
from src.errors import LLMServiceError


class OIDCVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwk.update(kid='test-key', alg='RS256', use='sig')

    def setUp(self):
        metadata = {'issuer': ISSUER, 'authorization_endpoint': ISSUER + '/api/accounts/authorize',
                    'token_endpoint': ISSUER + '/api/accounts/oauth/token', 'jwks_uri': ISSUER + '/.well-known/jwks.json',
                    'revocation_endpoint': ISSUER + '/api/accounts/oauth/revoke'}
        def transport(request):
            return httpx.Response(200, json={'keys': [self.jwk]} if request.url.path.endswith('jwks.json') else metadata)
        self.enterContext(patch('backend.services.chatgpt_oauth.new_client', side_effect=lambda: httpx.Client(transport=httpx.MockTransport(transport))))
        self.oauth = OpenAIOAuth()
        self.claims = {'iss': ISSUER, 'aud': 'oaiapp_test', 'sub': 'student', 'iat': int(time.time()),
                       'exp': int(time.time()) + 3600, 'nonce': 'expected-nonce'}

    def sign(self, claims=None, key=None):
        return jwt.encode(claims or self.claims, key or self.key, algorithm='RS256', headers={'kid': 'test-key'})

    def test_signature_issuer_audience_expiry_nonce_are_all_required(self):
        self.assertEqual(self.oauth.verify_identity(self.sign(), 'oaiapp_test', 'expected-nonce')['sub'], 'student')
        cases = [('iss', 'https://attacker.example'), ('aud', 'another-client'), ('exp', int(time.time()) - 100),
                 ('iat', int(time.time()) + 100), ('nonce', 'wrong'), ('sub', '')]
        for field, value in cases:
            with self.subTest(field=field), self.assertRaises(LLMServiceError):
                self.oauth.verify_identity(self.sign({**self.claims, field: value}), 'oaiapp_test', 'expected-nonce')
        with self.assertRaises(LLMServiceError):
            self.oauth.verify_identity(self.sign(key=rsa.generate_private_key(public_exponent=65537, key_size=2048)), 'oaiapp_test', 'expected-nonce')
        with self.assertRaises(LLMServiceError):
            self.oauth.verify_identity(jwt.encode(self.claims, '', algorithm='none', headers={'kid': 'test-key'}), 'oaiapp_test', 'expected-nonce')

    def test_discovery_cannot_redirect_credentials_to_another_origin(self):
        with patch('backend.services.chatgpt_oauth.new_client', side_effect=lambda: httpx.Client(transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={'issuer': ISSUER, 'token_endpoint': 'https://attacker.example/token'}),
        ))), self.assertRaises(LLMServiceError):
            OpenAIOAuth().discovery()


class LocalEndpointTests(unittest.TestCase):
    def setUp(self):
        self.manager = MagicMock()
        self.manager.status.return_value = {'profiles': [], 'active_connection_id': None, 'storage_mode': 'memory', 'error': None, 'pending': None}
        self.enterContext(patch('backend.api.routes.ai.manager', return_value=self.manager))
        self.client = self.enterContext(TestClient(app, base_url='http://127.0.0.1:8000', client=('127.0.0.1', 12345)))
        self.headers = {'X-YourNote-Local': '1', 'Origin': 'http://127.0.0.1:5173'}

    def session(self):
        response = self.client.get('/api/ai/session', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['set-cookie'].lower()
        self.assertIn('httponly', cookie)
        self.assertIn('samesite=strict', cookie)
        return {**self.headers, 'X-YourNote-CSRF': response.json()['csrf']}

    def test_all_mutations_require_session_csrf_and_origin(self):
        path = '/api/ai/chatgpt/sign-in'
        self.assertEqual(self.client.post(path, headers=self.headers, json={}).status_code, 401)
        headers = self.session()
        self.assertEqual(self.client.post(path, headers=self.headers, json={}).status_code, 403)
        self.assertEqual(self.client.post(path, headers={**headers, 'Origin': 'https://attacker.example'}, json={}).status_code, 403)
        self.manager.start.assert_not_called()
        self.manager.start.return_value = {'launch_path': '/api/ai/chatgpt/sign-in/launch?ticket=local-ticket'}
        self.assertEqual(self.client.post(path, headers=headers, json={}).status_code, 200)
        self.manager.start.assert_called_once()

    def test_remote_peers_host_rebinding_and_cross_site_bootstrap_are_rejected(self):
        for headers in ({}, {**self.headers, 'Host': 'attacker.example'}, {**self.headers, 'Sec-Fetch-Site': 'cross-site'}):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get('/api/ai/session', headers=headers).status_code, 403)
        with TestClient(app, base_url='http://127.0.0.1:8000', client=('192.0.2.1', 12345)) as remote:
            self.assertEqual(remote.get('/api/ai/session', headers=self.headers).status_code, 403)

    def test_safe_status_no_credential_fields_and_no_caching(self):
        self.session()
        response = self.client.get('/api/ai/chatgpt', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(set(response.json()), {'profiles', 'active_connection_id', 'storage_mode', 'error', 'pending'})


class VaultTests(unittest.TestCase):
    def test_plaintext_backend_is_not_used(self):
        class Plaintext:
            priority = 10
        backend = Plaintext()
        backend.set_password = MagicMock()
        with patch('keyring.get_keyring', return_value=backend):
            vault = CredentialVault('test-host')
        self.assertEqual(vault.mode, 'memory')
        backend.set_password.assert_not_called()
