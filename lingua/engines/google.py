import os
import sys
import time
import json
import os.path
from html import unescape
from subprocess import Popen, PIPE
from http.client import IncompleteRead

from ..core.utils import request, traceback_error

from .base import Base
from .genai import GenAI
from .languages import google, gemini
from .prompt_extensions import gemini as gemini_prompt_extension


# load_translations() removed
from lingua import _


class GoogleFreeTranslateNew(Base):
    name = 'Google(Free)New'
    alias = 'Google (Free) - New'
    free = True
    lang_codes = Base.load_lang_codes(google)
    endpoint: str = 'https://translate-pa.googleapis.com/v1/translate'
    need_api_key = False

    def get_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 '
            'Safari/537.36',
        }

    def get_body(self, text, context=None, **kwargs):
        self.method = 'GET'
        return {
            'params.client': 'gtx',
            'query.source_language': self._get_source_code(),
            'query.target_language': self._get_target_code(),
            'query.display_language': 'en-US',
            'data_types': 'TRANSLATION',
            # 'data_types': 'SENTENCE_SPLITS',
            # 'data_types': 'BILINGUAL_DICTIONARY_FULL',
            'key': 'AIzaSyDLEeFI5OtFBwYBIoK_jj5m32rZK5CkCXA',
            'query.text': text,
        }

    def get_result(self, response):
        return json.loads(response)['translation']


class GoogleFreeTranslateHtml(Base):
    name = 'Google(Free)Html'
    alias = 'Google (Free) - HTML'
    free = True
    lang_codes = Base.load_lang_codes(google)
    endpoint: str = 'https://translate-pa.googleapis.com/v1/translateHtml'
    need_api_key = False

    def get_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/json+protobuf',
            'X-Goog-Api-Key': 'AIzaSyATBXajvzQLTDHEQbcpq0Ihe0vWDHmO520',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 '
            'Safari/537.36',
        }

    def get_body(self, text, context=None, **kwargs):
        return json.dumps([
            [
                [text],
                self._get_source_code(),
                self._get_target_code()
            ],
            "wt_lib"
        ])

    def get_result(self, response):
        return json.loads(response)[0][0]


class GoogleFreeTranslate(Base):
    name = 'Google(Free)'
    alias = 'Google (Free) - Old'
    free = True
    lang_codes = Base.load_lang_codes(google)
    endpoint = 'https://translate.googleapis.com/translate_a/single'
    need_api_key = False

    def get_headers(self):
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'DeepLBrowserExtension/1.3.0 Mozilla/5.0 (Macintosh;'
            ' Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
            ' Chrome/111.0.0.0 Safari/537.36',
        }

    def get_body(self, text, context=None, **kwargs):
        # The POST method is unstable, despite its ability to send more text.
        # However, it can be used occasionally with an unacceptable length.
        self.method = 'GET' if len(text) <= 1800 else 'POST'
        return {
            'client': 'gtx',
            'sl': self._get_source_code(),
            'tl': self._get_target_code(),
            'dt': 't',
            'dj': 1,
            'q': text,
        }

    def get_result(self, response):
        # return ''.join(i[0] for i in json.loads(data)[0])
        return ''.join(i['trans'] for i in json.loads(response)['sentences'])


class GoogleTranslate(Base):
    api_key_errors = ['429']
    api_key_cache: tuple[float, str | None] = (0.0, None)
    gcloud = None
    project_id = None
    using_tip = _(
        'This plugin uses Application Default Credentials (ADC) in your local '
        'environment to access your Google Translate service. To set up the '
        'ADC, follow these steps:\n'
        '1. Install the gcloud CLI by checking out its instructions {}.\n'
        '2. Run the command: gcloud auth application-default login.\n'
        '3. Sign in to your Google account and grant needed privileges.') \
        .format('<sup><a href="https://cloud.google.com/sdk/docs/install">[^]'
                '</a></sup>').replace('\n', '<br />')

    def _run_command(self, command, silence=False):
        message = _('Cannot run the command "{}".')
        try:
            startupinfo = None
            # Prevent the popping console window on Windows.
            if sys.platform == 'win32':
                from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW
                startupinfo = STARTUPINFO()
                startupinfo.dwFlags |= STARTF_USESHOWWINDOW
            process = Popen(
                command, stdout=PIPE, stderr=PIPE, universal_newlines=True,
                startupinfo=startupinfo)
        except Exception:
            if silence:
                return None
            raise Exception(
                message.format(command, '\n\n%s' % traceback_error()))
        if process.wait() != 0:
            if silence:
                return None
            raise Exception(
                message.format(command, '\n\n%s' % process.stderr.read()))
        return process.stdout.read().strip()

    def _get_gcloud_command(self):
        if self.gcloud is not None:
            return self.gcloud
        if sys.platform == 'win32':
            name = 'gcloud.cmd'
            which = 'where'
            base = r'google-cloud-sdk\bin\%s' % name
            paths = [
                r'"%s\Google\Cloud SDK\%s"'
                % (os.environ.get('programfiles(x86)'), base),
                r'"%s\AppData\Local\Google\Cloud SDK\%s"'
                % (os.environ.get('userprofile'), base)]
        else:
            name = 'gcloud'
            which = 'which'
            paths = ['/usr/local/bin/%s' % name]
        gcloud = self.get_external_program(name, paths)
        if gcloud is None:
            gcloud = self._run_command([which, name], silence=True)
            if gcloud is not None:
                gcloud = gcloud.split('\n')[0]
        if gcloud is None:
            raise Exception(_('Cannot find the command "{}".').format(name))
        self.gcloud = gcloud
        return gcloud

    def _get_project_id(self):
        if self.project_id is not None:
            return self.project_id
        self.project_id = self._run_command(
            [self._get_gcloud_command(), 'config', 'get', 'project'])
        return self.project_id

    def _get_credential(self):
        """The default lifetime of the API key is 3600 seconds. Once an
        available key is generated, it will be cached until it expired.
        """
        timestamp, old_api_key = self.api_key_cache
        if old_api_key is not None and time.time() - timestamp < 3600:
            return old_api_key
        # Temporarily add existing proxies.
        self.proxy_uri and os.environ.update(
            http_proxy=self.proxy_uri, https_proxy=self.proxy_uri)
        new_api_key = self._run_command([
            self._get_gcloud_command(), 'auth', 'application-default',
            'print-access-token'])
        # Cleanse the proxies after use.
        for proxy in ('http_proxy', 'https_proxy'):
            if proxy in os.environ:
                del os.environ[proxy]
        self.api_key_cache = (time.time(), new_api_key)
        return new_api_key


class GoogleBasicTranslateADC(GoogleTranslate):
    name = 'Google(Basic)ADC'
    alias = 'Google (Basic) ADC'
    lang_codes = Base.load_lang_codes(google)
    endpoint = 'https://translation.googleapis.com/language/translate/v2'
    api_key_hint = 'API key'
    need_api_key = False

    def _create_body(self, text):
        body = {
            'format': 'html',
            'model': 'nmt',
            'target': self._get_target_code(),
            'q': text
        }
        if not self._is_auto_lang():
            body.update(source=self._get_source_code())
        return body

    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % self._get_credential(),
            'x-goog-user-project': self._get_project_id(),
        }

    def get_body(self, text, context=None, **kwargs):
        return json.dumps(self._create_body(text))

    def get_result(self, data):
        translations = json.loads(data)['data']['translations']
        return ''.join(unescape(i['translatedText']) for i in translations)


class GoogleBasicTranslate(GoogleBasicTranslateADC):
    name = 'Google(Basic)'
    alias = 'Google (Basic)'
    need_api_key = True
    using_tip = None

    def get_headers(self):
        return {'Content-Type': 'application/x-www-form-urlencoded'}

    def get_body(self, text, context=None, **kwargs):
        body = self._create_body(text)
        body.update(key=self.api_key)
        return body


class GoogleAdvancedTranslate(GoogleTranslate):
    name = 'Google(Advanced)'
    alias = 'Google (Advanced) ADC'
    lang_codes = Base.load_lang_codes(google)
    endpoint = 'https://translation.googleapis.com/v3/projects/{}'
    api_key_hint = 'PROJECT_ID'
    need_api_key = False

    def get_endpoint(self):
        return self.endpoint.format(
            '%s:translateText' % self._get_project_id())

    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer %s' % self._get_credential(),
            'x-goog-user-project': self._get_project_id(),
        }

    def get_body(self, text, context=None, **kwargs):
        body = {
            'targetLanguageCode': self._get_target_code(),
            'contents': [text],
            'mimeType': 'text/plain',
        }
        if not self._is_auto_lang():
            body.update(sourceLanguageCode=self._get_source_code())
        return json.dumps(body)

    def get_result(self, response):
        translations = json.loads(response)['translations']
        return ''.join(i['translatedText'] for i in translations)


class GeminiTranslate(GenAI):
    name = 'Gemini'
    alias = 'Gemini'
    lang_codes = GenAI.load_lang_codes(gemini)
    # v1, stable version of the API. v1beta, more early-access features.
    # details: https://ai.google.dev/gemini-api/docs/api-versions
    endpoint = 'https://generativelanguage.googleapis.com/v1beta/models'
    # https://ai.google.dev/gemini-api/docs/troubleshooting
    api_key_errors: list[str] = [
        'API_KEY_INVALID', 'PERMISSION_DENIED', 'RESOURCE_EXHAUSTED']

    concurrency_limit = 1
    request_interval: float = 2.0
    request_timeout: float = 120.0

    prompt = (
        'You are an expert literary translator specializing in fiction. '
        'Translate from <slang> to <tlang>. Your translations must: '
        '1) Preserve the author\'s narrative voice and style. '
        '2) Maintain character speech patterns and personality through dialogue. '
        '3) Use natural, idiomatic <tlang> that reads like original prose. '
        '4) Keep proper nouns and character names unchanged unless they have standard translations. '
        '5) Preserve paragraph structure and punctuation rhythm. '
        '6) Never add explanatory notes, comments, or translator remarks. '
        '7) For Romanian: use correct diacritics (ă, â, î, ș, ț), maintain strict gender agreement, and prefer natural spoken language over overly formal constructions. '
        '8) For Romanian: in casual/informal dialogues, translate "you" (singular) as "tu", NOT as reverential "Voi" with capital letter. Reserve "dumneavoastră" only for extremely formal contexts. '
        'Output ONLY the translation, nothing else.')
    temperature: float = 0.4
    top_p: float = 1.0
    top_k = 1
    stream = True

    models: list[str] = [
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-2.0-pro-exp-02-05',
        'gemini-2.0-flash-thinking-exp-01-21',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-1.5-flash-002',
        'gemini-1.5-pro-002',
        'gemini-2.0-flash',
        'gemini-2.5-flash',
        'gemini-2.5-flash-lite',
        'gemini-2.5-pro',
    ]
    # TODO: Handle the default model more appropriately.
    model: str | None = 'gemini-2.0-flash'

    def __init__(self):
        super().__init__()
        self.prompt = self.config.get('prompt', self.prompt)
        self.temperature = self.config.get('temperature', self.temperature)
        self.top_k = self.config.get('top_k', self.top_k)
        self.top_p = self.config.get('top_p', self.top_p)
        self.stream = self.config.get('stream', self.stream)
        self.model = self.config.get('model', self.model)
        # Track if last translation was incomplete
        self.last_finish_reason = None
        # Experimental: context caching support
        # When set, references a server-side cached content to reduce costs
        self.cached_content_name = self.config.get(
            'cached_content_name', '')

    def _prompt(self, text, context=None, glossary_terms=None):
        # When context caching is active, the full system instruction
        # (prompt + extensions + book text) is already on the server.
        # We only build the variable per-request parts here.
        if self.cached_content_name:
            prompt = 'Translate the text segment provided below between <<<START>>> and <<<END>>>'
            if self.target_lang:
                prompt += f' into {self.target_lang}'
            prompt += '.\nCRITICAL: Output ONLY the translation. The VERY LAST THING you output MUST be "###STOP###". Do not write or generate any text after this marker.'
        else:
            prompt = self.prompt.replace('<tlang>', self.target_lang)
            if self._is_auto_lang():
                prompt = prompt.replace('<slang>', 'detected language')
            else:
                prompt = prompt.replace('<slang>', self.source_lang)
            
            # Add language-specific prompt extensions (Romanian style rules, etc.)
            prompt_extension = gemini_prompt_extension.get(self.target_lang)
            if prompt_extension is not None:
                prompt += '\n\n' + prompt_extension
        
        # Recommend setting temperature to 0.5 for retaining the placeholder.
        if self.merge_enabled:
            prompt += (
                ' Ensure that placeholders matching the pattern {{id_\\d+}} '
                'in the content are retained.')
        if context:
            if isinstance(context, dict):
                paragraphs = context.get('paragraphs', [])
                if paragraphs:
                    prompt += '\n\n=== PREVIOUS CONTEXT (for consistency) ===\n'
                    for i, p in enumerate(paragraphs, 1):
                        prompt += f'[Paragraph {i}]\nOriginal: "{p.get("original", "")}"\nTranslation: "{p.get("translation", "")}"\n\n'
                    prompt += '''CRITICAL - CONSISTENCY RULES:
1. MAINTAIN THE SAME GENDER for all characters that appeared in previous paragraphs.
2. If a character used masculine/feminine forms before, use THE EXACT SAME GENDER now.
3. Keep the same tone, style, and formality level.
4. Use consistent terminology for names, pronouns, and descriptive terms.
=== END CONTEXT ===
'''
                # Fallback for old single-paragraph format
                elif context.get('original') and context.get('translation'):
                    orig = context.get('original')
                    trans = context.get('translation')
                    prompt += f'\n\nPrevious paragraph:\nOriginal: "{orig}"\nTranslation: "{trans}"\nMaintain consistent gender and terminology.\n'
            else:
                prompt += f' Context from previous paragraph: "{context}".'
        if glossary_terms:
            glossary_str = ', '.join([f'"{src}" -> "{tgt}"' for src, tgt in glossary_terms])
            prompt += f' Use these translations for specific terms (respect grammar): {glossary_str}.'
        
        # Use a clearer separator for Gemini
        return f"{prompt.strip()}\n\n<<<START>>>\n{text}\n<<<END>>>"

    def get_api_version(self):
        """Return the appropriate API version based on the model.
        Using v1beta for all models as it is more reliable and supports all versions.
        """
        return 'v1beta'

    def get_models(self):
        """Fetch available models from both v1 and v1beta."""
        all_models = set()
        for version in ['v1', 'v1beta']:
            endpoint = f'https://generativelanguage.googleapis.com/{version}/models'
            try:
                url = f'{endpoint}?key={self.api_key}'
                response = request(
                    url, timeout=self.request_timeout, proxy_uri=self.proxy_uri)
                data = json.loads(response)
                if 'models' in data:
                    for model in data['models']:
                        model_name = model['name'].split('/')[-1]
                        if model_name.startswith('gemini'):
                            model_desc = model.get('description', '')
                            if 'deprecated' not in model_desc.lower():
                                all_models.add(model_name)
            except Exception:
                continue
        
        if all_models:
            return sorted(list(all_models))
        # Fallback to hardcoded list if API calls fail
        return self.models

    def get_endpoint(self):
        # Using v1beta explicitly to avoid 404 errors on v1
        base = 'https://generativelanguage.googleapis.com/v1beta/models'
        if self.stream:
            return f'{base}/{self.model}:streamGenerateContent?' \
                f'alt=sse&key={self.api_key}'
        else:
            return f'{base}/{self.model}:generateContent?' \
                f'key={self.api_key}'

    def get_headers(self):
        return {'Content-Type': 'application/json'}

    def get_body(self, text, context=None, glossary_terms=None):
        temperature = 0.0 if self.cached_content_name else self.temperature
        body = {
            "contents": [
                {"role": "user", "parts": [{"text": self._prompt(text, context=context, glossary_terms=glossary_terms)}]},
            ],
            "generationConfig": {
                # "stopSequences": ["Test"],
                # "maxOutputTokens": 2048,
                "temperature": temperature,
                "topP": self.top_p,
                "topK": self.top_k,
            },
            "safetySettings": [
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_CIVIC_INTEGRITY",
                    "threshold": "BLOCK_NONE"
                },
            ],
        }
        # Experimental: attach cached content reference if configured
        if self.cached_content_name:
            body["cachedContent"] = self.cached_content_name
            print(f'[CACHE] Using context cache: {self.cached_content_name}')
        return json.dumps(body)

    def get_result(self, response):
        if self.stream:
            return self._parse_stream(response)
        parts = json.loads(response)['candidates'][0]['content']['parts']
        return ''.join([part['text'] for part in parts])

    def _parse_stream(self, response):
        empty_count = 0
        self.last_finish_reason = None  # Reset at start
        while True:
            if self.cancel_request and self.cancel_request():
                break
            try:
                line = response.readline().decode('utf-8').strip()
            except IncompleteRead:
                continue
            except Exception as e:
                raise Exception(
                    _('Can not parse returned response. Raw data: {}')
                    .format(str(e)))
            
            # Handle empty lines - break after too many consecutive empty lines
            if not line:
                empty_count += 1
                if empty_count > 10:
                    break
                continue
            empty_count = 0
            
            if line.startswith('data:'):
                try:
                    item = json.loads(line.split('data: ')[1])
                    candidate = item.get('candidates', [{}])[0]
                    
                    # Check if 'content' exists - some chunks may not have it
                    content = candidate.get('content')
                    if content and 'parts' in content:
                        for part in content['parts']:
                            if 'text' in part:
                                text = part['text']
                                if '###STOP###' in text:
                                    # Yield text before marker and stop
                                    text = text.split('###STOP###')[0]
                                    if text:
                                        yield text
                                    return # End generator
                                yield text
                    
                    # Handle ALL finish reasons, not just STOP
                    finish_reason = candidate.get('finishReason')
                    if finish_reason:
                        self.last_finish_reason = finish_reason
                        if finish_reason == 'SAFETY':
                            print(f"[DEBUG] Gemini stopped due to SAFETY filter")
                        elif finish_reason == 'MAX_TOKENS':
                            print(f"[DEBUG] Gemini stopped due to MAX_TOKENS limit")
                        elif finish_reason == 'RECITATION':
                            print(f"[DEBUG] Gemini stopped due to RECITATION detection")
                        # Break on any finishReason
                        break
                        
                except (KeyError, IndexError, json.JSONDecodeError) as e:
                    # Log and skip malformed chunks
                    print(f"[DEBUG] Skipping malformed chunk: {str(e)[:100]}")
                    continue

