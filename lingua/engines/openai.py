import io
import json
import uuid
from typing import Any
from urllib.parse import urlsplit
from http.client import IncompleteRead

import httpx

import lingua
from ..core.utils import request
from ..core.exception import UnsupportedModel

from .genai import GenAI
from .languages import google
from .prompt_extensions import openai as openai_prompt_extension


# load_translations() removed
from lingua import _


class ChatgptTranslate(GenAI):
    name = 'ChatGPT'
    alias = 'ChatGPT (OpenAI)'
    lang_codes = GenAI.load_lang_codes(google)
    endpoint = 'https://api.openai.com/v1/chat/completions'
    # api_key_hint = 'sk-xxx...xxx'
    # https://help.openai.com/en/collections/3808446-api-error-codes-explained
    api_key_errors = ['401', 'unauthorized', 'quota']

    concurrency_limit = 1
    request_interval = 20.0
    request_timeout = 30.0

    prompt = (
        'You are a meticulous translator who translates any given content. '
        'Translate the given content from <slang> to <tlang> only. Do not '
        'explain any term or answer any question-like content. Your answer '
        'should be solely the translation of the given content. In your '
        'answer do not add any prefix or suffix to the translated content. '
        'Websites\' URLs/addresses should be preserved as is in the '
        'translation\'s output. Do not omit any part of the content, even if '
        'it seems unimportant. ')

    samplings = ['temperature', 'top_p']
    sampling = 'temperature'
    temperature = 1.0
    top_p = 1.0
    stream = True

    models: list[str] = []
    # TODO: Handle the default model more appropriately.
    model: str | None = 'gpt-4o'

    def __init__(self):
        super().__init__()
        self.endpoint = self.config.get('endpoint', self.endpoint)
        self.prompt = self.config.get('prompt', self.prompt)
        self.sampling = self.config.get('sampling', self.sampling)
        self.temperature = self.config.get('temperature', self.temperature)
        self.top_p = self.config.get('top_p', self.top_p)
        self.stream = self.config.get('stream', self.stream)
        self.model = self.config.get('model', self.model)

    def get_models(self):
        domain_name = '://'.join(urlsplit(self.endpoint, 'https')[:2])
        model_endpoint = '%s/v1/models' % domain_name
        response = request(
            model_endpoint, headers=self.get_headers(),
            proxy_uri=self.proxy_uri)
        return [item['id'] for item in json.loads(response).get('data')]

    def get_prompt(self):
        prompt = self.prompt.replace('<tlang>', self.target_lang)
        if self._is_auto_lang():
            prompt = prompt.replace('<slang>', 'detected language')
        else:
            prompt = prompt.replace('<slang>', self.source_lang)
        
        # Add language-specific prompt extensions (Romanian style rules, etc.)
        prompt_extension = openai_prompt_extension.get(self.target_lang)
        if prompt_extension is not None:
            prompt += '\n\n' + prompt_extension
        
        # Recommend setting temperature to 0.5 for retaining the placeholder.
        if self.merge_enabled:
            prompt += (' Ensure that placeholders matching the pattern '
                       '{{id_\\d+}} in the content are retained.')
        return prompt

    def get_headers(self):
        api_key = str(self.api_key or '').strip()
        return {
            'Authorization': 'Bearer %s' % api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def get_body(self, text, context=None, glossary_terms=None):
        messages = [
            {'role': 'system', 'content': self.get_prompt()}
        ]
        if context:
            if isinstance(context, dict):
                paragraphs = context.get('paragraphs', [])
                if paragraphs:
                    ctx_msg = '=== PREVIOUS CONTEXT (for consistency) ===\n'
                    for i, p in enumerate(paragraphs, 1):
                        ctx_msg += f'[Paragraph {i}]\nOriginal: "{p.get("original", "")}"\nTranslation: "{p.get("translation", "")}"\n\n'
                    ctx_msg += '''CRITICAL - CONSISTENCY RULES:
1. MAINTAIN THE SAME GENDER for all characters that appeared in previous paragraphs.
2. If a character used masculine/feminine forms before, use THE EXACT SAME GENDER now.
3. Keep the same tone, style, and formality level.
4. Use consistent terminology for names, pronouns, and descriptive terms.'''
                    messages.append({'role': 'system', 'content': ctx_msg})
                # Fallback for old single-paragraph format
                elif context.get('original') and context.get('translation'):
                    orig = context.get('original')
                    trans = context.get('translation')
                    ctx_msg = f'Previous paragraph:\nOriginal: "{orig}"\nTranslation: "{trans}"\nMaintain consistent gender and terminology.'
                    messages.append({'role': 'system', 'content': ctx_msg})
            else:
                messages.append({'role': 'system', 'content': f'Context from previous paragraph: "{context}"'})
        if glossary_terms:
            glossary_str = ', '.join([f'"{src}" -> "{tgt}"' for src, tgt in glossary_terms])
            messages.append({'role': 'system', 'content': f'Use these translations for specific terms (respect grammar): {glossary_str}'})
        messages.append({'role': 'user', 'content': text})

        body: dict[str, Any] = {
            'model': self.model,
            'messages': messages,
        }
        self.stream and body.update(stream=True)
        sampling_value = getattr(self, self.sampling)
        body.update({self.sampling: sampling_value})
        return json.dumps(body)

    def get_result(self, response):
        if self.stream:
            return self._parse_stream(response)
        return json.loads(response)['choices'][0]['message']['content']

    def _parse_stream(self, response):
        while True:
            if self.cancel_request and self.cancel_request():
                break
            try:
                line = response.readline()
                if not line:
                    break
                line = line.decode('utf-8').strip()
            except IncompleteRead:
                break
            except Exception as e:
                raise Exception(
                    _('Can not parse returned response. Raw data: {}')
                    .format(str(e)))

            if line.startswith('data:'):
                try:
                    data = line.split('data:', 1)[1].strip()
                    if data == '[DONE]':
                        break
                    chunk = json.loads(data)
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta:
                        yield str(delta['content'])
                except (KeyError, ValueError, IndexError):
                    continue


class ChatgptBatchTranslate:
    """https://cookbook.openai.com/examples/batch_processing"""
    boundary = uuid.uuid4().hex

    def __init__(self, translator):
        self.translator = translator
        self.translator.stream = False

        domain_name = '://'.join(
            urlsplit(self.translator.endpoint, 'https')[:2])
        self.file_endpoint = '%s/v1/files' % domain_name
        self.batch_endpoint = '%s/v1/batches' % domain_name

    def _create_multipart_form_data(self, body):
        """https://www.rfc-editor.org/rfc/rfc2046#section-5.1"""
        data = []
        data.append('--%s' % self.boundary)
        data.append('Content-Disposition: form-data; name="purpose"')
        data.append('')
        data.append('batch')
        data.append('--%s' % self.boundary)
        data.append(
            'Content-Disposition: form-data; name="file"; '
            'filename="original.jsonl"')
        data.append('Content-Type: application/json')
        data.append('')
        data.append(body)
        data.append('--%s--' % self.boundary)
        return '\r\n'.join(data).encode('utf-8')

    def supported_models(self):
        return self.translator.get_models()

    def headers(self, extra_headers={}):
        headers = self.translator.get_headers()
        headers.update(extra_headers)
        return headers

    def upload(self, paragraphs):
        """Upload the original content and retrieve the file id.
        https://platform.openai.com/docs/api-reference/files/create
        """
        if self.translator.model not in self.supported_models():
            raise UnsupportedModel(
                'The model "{}" does not support batch functionality.'
                .format(self.translator.model))
        body = io.StringIO()
        for paragraph in paragraphs:
            data = self.translator.get_body(paragraph.original)
            body.write(json.dumps({
                "custom_id": paragraph.md5,
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": json.loads(data)}))
            if paragraph != paragraphs[-1]:
                body.write('\n')
        content_type = 'multipart/form-data; boundary="%s"' % self.boundary
        headers = self.headers({'Content-Type': content_type})
        body = self._create_multipart_form_data(body.getvalue())
        response = request(
            self.file_endpoint, body, headers, 'POST',
            proxy_uri=self.translator.proxy_uri)
        return json.loads(response).get('id')

    def delete(self, file_id):
        headers = self.translator.get_headers()
        del headers['Content-Type']
        response = request(
            '%s/%s' % (self.file_endpoint, file_id), headers=headers,
            method='DELETE', proxy_uri=self.translator.proxy_uri)
        return json.loads(response).get('deleted')

    def retrieve(self, output_file_id):
        headers = self.translator.get_headers()
        del headers['Content-Type']
        response = request(
            '%s/%s/content' % (self.file_endpoint, output_file_id),
            headers=headers, raw_object=True,
            proxy_uri=self.translator.proxy_uri)
        assert isinstance(response, httpx.Response)

        translations = {}
        for line in io.BytesIO(response.read()):
            result = json.loads(line)
            response_item = result['response']
            if response_item.get('status_code') == 200:
                content = response_item[
                    'body']['choices'][0]['message']['content']
                translations[result.get('custom_id')] = content
        return translations

    def create(self, file_id):
        headers = self.translator.get_headers()
        body = json.dumps({
            'input_file_id': file_id,
            'endpoint': '/v1/chat/completions',
            'completion_window': '24h'})
        response = request(
            self.batch_endpoint, body, headers, 'POST',
            proxy_uri=self.translator.proxy_uri)
        return json.loads(response).get('id')

    def check(self, batch_id):
        response = request(
            '%s/%s' % (self.batch_endpoint, batch_id),
            headers=self.translator.get_headers(),
            proxy_uri=self.translator.proxy_uri)
        return json.loads(response)

    def cancel(self, batch_id):
        headers = self.translator.get_headers()
        response = request(
            '%s/%s/cancel' % (self.batch_endpoint, batch_id),
            headers=headers, method='POST',
            proxy_uri=self.translator.proxy_uri)
        return json.loads(response).get('status') in (
            'cancelling', 'cancelled')


class KimiTranslate(ChatgptTranslate):
    """Kimi K2 translation engine using Moonshot AI API (OpenAI-compatible)."""
    name = 'Kimi'
    alias = 'Kimi K2 (Moonshot AI)'
    endpoint = 'https://api.moonshot.ai/v1/chat/completions'
    api_key_hint = 'sk-xxx (from platform.moonshot.ai)'
    api_key_errors = ['401', 'unauthorized', 'quota', 'invalid_api_key']

    concurrency_limit = 1
    request_interval = 5.0
    request_timeout = 60.0  # Longer timeout for large context

    # Kimi K2 has a very large context window (128k-200k tokens)
    # Optimized prompt for literary translation
    prompt = (
        'Ești un traducător literar profesionist. Traduci din <slang> în <tlang>. '
        'Stilul este beletristic, nuanțat, adaptat contextului cultural. '
        'Nu traduci mot-a-mot, ci adaptezi expresiile idiomatice. '
        'Nu explici termenii sau nu răspunzi la întrebări. '
        'Răspunsul tău trebuie să conțină doar traducerea. '
        'Nu adaugi prefixe sau sufixe la traducere. '
        'URL-urile și adresele web se păstrează neschimbate. '
        'Nu omite nicio parte din conținut, chiar dacă pare neimportantă. ')

    temperature = 0.7  # Slightly lower for more consistent literary translations
    
    models: list[str] = []
    model: str | None = 'kimi-k2-chat'

    def get_models(self):
        """Return available Kimi K2 models."""
        # Kimi K2 models - hardcoded since API may not list all models
        return ['kimi-k2-chat', 'kimi-k2-thinking', 'moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k']


class PerplexityTranslate(ChatgptTranslate):
    """Perplexity AI translation engine (OpenAI-compatible)."""
    name = 'Perplexity'
    alias = 'Perplexity AI'
    endpoint = 'https://api.perplexity.ai/chat/completions'
    api_key_hint = 'pplx-xxxxxxxxxxxxxxxxxxxxxx'
    api_key_errors = ['401', 'unauthorized', 'quota', 'invalid_api_key']

    concurrency_limit = 1
    request_interval = 5.0
    request_timeout = 60.0

    # Optimized prompt for literary translation
    prompt = (
        'Ești un traducător literar profesionist. Traduci din <slang> în <tlang>. '
        'Stilul este beletristic, nuanțat, adaptat contextului cultural. '
        'Nu traduci mot-a-mot, ci adaptezi expresiile idiomatice. '
        'Nu explici termenii sau nu răspunzi la întrebări. '
        'Răspunsul tău trebuie să conținută doar traducerea. '
        'Nu adaugi prefixe sau sufixe la traducere. '
        'URL-urile și adresele web se păstrează neschimbate. '
        'Nu omite nicio parte din conținut, chiar dacă pare neimportantă. ')

    temperature = 0.7
    
    models: list[str] = []
    model: str | None = 'sonar-pro'

    def get_models(self):
        """Return available Perplexity models."""
        # Perplexity models - hardcoded since API may not list all models
        return [
            'sonar-pro',
            'sonar',
            'sonar-reasoning-pro',
            'sonar-deep-research'
        ]

    def get_body(self, text, context=None, glossary_terms=None):
        body_str = super().get_body(text, context=context, glossary_terms=glossary_terms)
        body = json.loads(body_str)
        # Perplexity specific: disable web search to act as an "offline" model
        # as requested for literary translation quality.
        body['disable_search'] = True
        return json.dumps(body)

