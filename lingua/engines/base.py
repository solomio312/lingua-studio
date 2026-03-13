"""
Base translation engine class.

Migrated from Calibre plugin engines/base.py.
Changes:
  - mechanize.HTTPError → httpx.HTTPStatusError
  - mechanize._response.Response → httpx.Response
  - calibre.utils.localization.lang_as_iso639_1 → own implementation
  - load_translations() removed
"""

import os.path
from typing import Any

import httpx

from ..core.utils import traceback_error, request
from ..core.exception import UnexpectedResult

from .languages import lang_directionality


# Simple ISO 639-1 mapping (replaces calibre.utils.localization.lang_as_iso639_1)
def lang_as_iso639_1(code):
    """Convert language code to ISO 639-1 format."""
    if code and len(code) > 2 and '-' in code:
        return code.split('-')[0].lower()
    if code and len(code) > 2 and '_' in code:
        return code.split('_')[0].lower()
    return code.lower() if code else code


class Base:
    name: str | None = None
    alias: str | None = None
    free = False

    lang_codes: dict[str, Any] = {}
    config: dict[str, Any] = {}
    endpoint: str | None = None
    method = 'POST'
    headers: dict[str, str] = {}
    stream = False
    need_api_key = True
    api_key_hint = 'API Keys'
    api_key_pattern = r'^[^\s]+$'
    api_key_errors = ['401']
    separator = '\n\n'
    placeholder = ('{{{{id_{}}}}}', r'({{\s*)+id\s*_\s*{}\s*(\s*}})+')
    using_tip = None

    concurrency_limit: int = 0
    request_interval: float = 0.0
    request_attempt: int = 3
    request_timeout: float = 10.0
    max_error_count: int = 10

    def __init__(self):
        self.source_lang: str | None = None
        self.target_lang: str | None = None
        self.proxy_uri: str | None = None
        self.search_paths = []
        self.cancel_request = None

        self.merge_enabled = False
        self.api_keys: list = self.config.get('api_keys', [])[:]
        self.bad_api_keys = []
        self.api_key = self.get_api_key()

        concurrency_limit = self.config.get('concurrency_limit')
        if concurrency_limit is not None:
            self.concurrency_limit = int(concurrency_limit)
        request_interval = self.config.get('request_interval')
        if request_interval is not None:
            self.request_interval = request_interval
        request_attempt = self.config.get('request_attempt')
        if request_attempt is not None:
            self.request_attempt = int(request_attempt)
        request_timeout = self.config.get('request_timeout')
        if request_timeout is not None:
            self.request_timeout = request_timeout
        max_error_count = self.config.get('max_error_count')
        if max_error_count is not None:
            self.max_error_count = max_error_count

    @classmethod
    def load_lang_codes(cls, codes):
        if not ('source' in codes or 'target' in codes):
            codes = {'source': codes, 'target': codes}
        return codes

    @classmethod
    def get_lang_directionality(cls, lang_code):
        return lang_directionality.get(lang_code, 'auto')

    @classmethod
    def get_source_code(cls, lang):
        source_codes: dict = cls.lang_codes.get('source') or {}
        if lang in ('Auto detect', 'Auto'):
            return 'auto'
        return source_codes.get(lang)

    @classmethod
    def get_target_code(cls, lang):
        target_codes: dict = cls.lang_codes.get('target') or {}
        return target_codes.get(lang)

    @classmethod
    def get_iso639_target_code(cls, lang):
        return lang_as_iso639_1(cls.get_target_code(lang))

    @classmethod
    def set_config(cls, config):
        cls.config = config

    @classmethod
    def api_key_error_message(cls):
        return 'A correct key format "%s" is required.' % cls.api_key_hint

    def get_api_key(self):
        if self.need_api_key and self.api_keys:
            return self.api_keys.pop(0)
        return None

    def swap_api_key(self):
        """Change the API key if the previous one cannot be used."""
        if self.api_key not in self.bad_api_keys:
            self.bad_api_keys.append(self.api_key)
            self.api_key = self.get_api_key()
            if self.api_key is not None:
                return True
        return False

    def need_swap_api_key(self, error_message):
        if self.need_api_key and len(self.api_keys) > 0 \
                and self.match_error(error_message):
            return True
        return False

    def match_error(self, error_message):
        for error in self.api_key_errors:
            if error in error_message:
                return True
        return False

    def set_search_paths(self, paths):
        self.search_paths = paths

    def get_external_program(self, name, paths=[]):
        for path in paths + self.search_paths:
            if not path.endswith('%s%s' % (os.path.sep, name)):
                path = os.path.join(path, name)
            if os.path.isfile(path):
                return path
        return None

    def set_merge_enabled(self, enable):
        self.merge_enabled = enable

    def set_source_lang(self, source_lang):
        self.source_lang = source_lang

    def set_target_lang(self, target_lang):
        self.target_lang = target_lang

    def get_target_lang(self):
        return self.target_lang

    def set_proxy(self, proxy=[]):
        if isinstance(proxy, list) and len(proxy) == 2:
            self.proxy_uri = '%s:%s' % tuple(proxy)
            if not self.proxy_uri.startswith('http'):
                self.proxy_uri = 'http://%s' % self.proxy_uri

    def set_concurrency_limit(self, limit):
        self.concurrency_limit = limit

    def set_request_attempt(self, limit):
        self.request_attempt = limit

    def set_request_interval(self, seconds):
        self.request_interval = seconds

    def set_request_timeout(self, seconds):
        self.request_timeout = seconds

    def _get_source_code(self):
        return self.get_source_code(self.source_lang)

    def _get_target_code(self):
        return self.get_target_code(self.target_lang)

    def _is_auto_lang(self):
        return self._get_source_code() == 'auto'

    def translate(self, text, context=None, glossary_terms=None):
        try:
            # 1. Evaluate body FIRST so engines can set side-effects like self.method
            body = self.get_body(text, context=context, glossary_terms=glossary_terms)
            endpoint = self.get_endpoint()
            method = self.method
            headers = self.get_headers()
            
            print(f"DEBUG ENGINE: Requesting {method} {endpoint} (chars: {len(text)})")
            
            response = request(
                url=endpoint,
                data=body,
                headers=headers, 
                method=method,
                timeout=self.request_timeout, 
                proxy_uri=self.proxy_uri,
                raw_object=self.stream)
            
            result = self.get_result(response)
            if not result or not result.strip():
                print(f"DEBUG ENGINE: WARNING: Result is EMPTY for input: {text[:50]}...")
            return result
        except Exception as e:
            error_message = traceback_error()
            if isinstance(e, httpx.HTTPStatusError):
                error_message += '\n\n' + e.response.text
            elif not self.stream and 'response' in locals():
                error_message += '\n\n' + str(response)
            if self.need_swap_api_key(error_message) and self.swap_api_key():
                return self.translate(text)
            raise UnexpectedResult(
                'Can not parse returned response. Raw data: %s'
                % ('\n\n' + error_message))

    def get_endpoint(self):
        return self.endpoint

    def get_headers(self):
        return self.headers

    def get_body(self, text, context=None, **kwargs):
        return text

    def get_result(self, response: httpx.Response | str):
        return response

    def get_usage(self):
        return None
