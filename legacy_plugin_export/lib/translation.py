import re
import time
import json
from types import GeneratorType

from ..engines import builtin_engines
from ..engines import GoogleFreeTranslateNew
from ..engines.base import Base
from ..engines.custom import CustomTranslate

from .utils import sep, trim, dummy, traceback_error
from .config import get_config
from .exception import TranslationFailed, TranslationCanceled
from .handler import Handler
from .dynamic_glossary import DynamicGlossary


load_translations()


# Pricing per 1M tokens (input, output) - Updated Dec 2024
ENGINE_PRICING = {
    # Gemini models
    'gemini-1.5-pro': {'input': 1.25, 'output': 10.00, 'type': 'token'},
    'gemini-1.5-pro-002': {'input': 1.25, 'output': 10.00, 'type': 'token'},
    'gemini-1.5-flash': {'input': 0.075, 'output': 0.30, 'type': 'token'},
    'gemini-1.5-flash-002': {'input': 0.075, 'output': 0.30, 'type': 'token'},
    'gemini-2.0-flash': {'input': 0.10, 'output': 0.40, 'type': 'token'},
    'gemini-2.0-flash-lite-preview-02-05': {'input': 0.075, 'output': 0.30, 'type': 'token'},
    'gemini-2.0-pro-exp-02-05': {'input': 1.25, 'output': 10.00, 'type': 'token'},
    'gemini-2.0-pro-exp-02-05': {'input': 1.25, 'output': 10.00, 'type': 'token'},
    'gemini-2.5-flash': {'input': 0.15, 'output': 0.60, 'type': 'token'},
    'gemini-2.5-flash-001': {'input': 0.15, 'output': 0.60, 'type': 'token'},
    'gemini-2.5-flash-lite': {'input': 0.10, 'output': 0.40, 'type': 'token'},
    'gemini-2.5-flash-lite-001': {'input': 0.10, 'output': 0.40, 'type': 'token'},
    'gemini-2.5-pro': {'input': 1.25, 'output': 10.00, 'type': 'token'},
    'gemini-3-flash-preview': {'input': 0.50, 'output': 3.00, 'type': 'token'},
    'gemini-3-pro-preview': {'input': 1.25, 'output': 10.00, 'type': 'token'},
    # OpenAI models
    'gpt-4o': {'input': 2.50, 'output': 10.00, 'type': 'token'},
    'gpt-4o-mini': {'input': 0.15, 'output': 0.60, 'type': 'token'},
    'gpt-4-turbo': {'input': 10.00, 'output': 30.00, 'type': 'token'},
    'gpt-3.5-turbo': {'input': 0.50, 'output': 1.50, 'type': 'token'},
    # Claude models
    'claude-3-5-sonnet-20241022': {'input': 3.00, 'output': 15.00, 'type': 'token'},
    'claude-3-opus-20240229': {'input': 15.00, 'output': 75.00, 'type': 'token'},
    'claude-3-haiku-20240307': {'input': 0.25, 'output': 1.25, 'type': 'token'},
    # DeepL (per 1M characters, not tokens)
    'DeepL': {'input': 25.00, 'output': 0, 'type': 'char'},
    'DeepL(Pro)': {'input': 25.00, 'output': 0, 'type': 'char'},
    # Free engines
    'Google(Free)': {'input': 0, 'output': 0, 'type': 'free'},
    'Google(Free)New': {'input': 0, 'output': 0, 'type': 'free'},
    'Google(Free)Html': {'input': 0, 'output': 0, 'type': 'free'},
    'DeepL(Free)': {'input': 0, 'output': 0, 'type': 'free'},
}


def estimate_cost(char_count, engine_name, model_name=None):
    """Estimate translation cost based on character count and engine/model.
    
    Returns a tuple: (cost_estimate, cost_details_string, is_free)
    """
    # Try model name first, then engine name
    pricing = ENGINE_PRICING.get(model_name) or ENGINE_PRICING.get(engine_name)
    
    if not pricing:
        return (0, 'Unknown pricing', False)
    
    if pricing['type'] == 'free':
        return (0, 'FREE ✓', True)
    
    if pricing['type'] == 'char':
        # Character-based pricing (DeepL)
        cost = (char_count / 1_000_000) * pricing['input']
        return (cost, f'~${cost:.4f} (character-based)', False)
    
    # Token-based pricing (LLMs)
    # Approximation: 1 token ≈ 4 characters
    tokens = char_count / 4
    input_cost = (tokens / 1_000_000) * pricing['input']
    output_cost = (tokens / 1_000_000) * pricing['output']  # Output ~= input for translation
    total_cost = input_cost + output_cost
    
    details = f'~${total_cost:.4f} (Input: ${input_cost:.4f} + Output: ${output_cost:.4f})'
    return (total_cost, details, False)


class GenderAnalyzer:
    """Analyzes translated paragraphs for potential gender inconsistencies in Romanian."""
    
    # Romanian gender markers
    MASCULINE_MARKERS = [
        r'\bel\b', r'\blui\b', r'\bărbat', r'\btânăr\b', r'\bdomn',
        r'a spus el', r'a zis el', r'a răspuns el', r'a întrebat el',
        r'\b-l\b', r'\bl-a\b', r'\bîl\b', r'\bsău\b', r'\bpropriu\b'
    ]
    
    FEMININE_MARKERS = [
        r'\bea\b', r'\bei\b', r'\bfeme', r'\btânără\b', r'\bdoamn',
        r'a spus ea', r'a zis ea', r'a răspuns ea', r'a întrebat ea',
        r'\b-o\b', r'\bo\b', r'\bsa\b', r'\bproprie\b'
    ]
    
    def __init__(self):
        self.issues = []
    
    def get_gender_score(self, text):
        """Returns (masculine_score, feminine_score) for a text."""
        text_lower = text.lower()
        masc = sum(1 for pattern in self.MASCULINE_MARKERS 
                   if re.search(pattern, text_lower))
        fem = sum(1 for pattern in self.FEMININE_MARKERS 
                  if re.search(pattern, text_lower))
        return masc, fem
    
    def get_dominant_gender(self, text):
        """Returns 'M', 'F', or None if ambiguous."""
        masc, fem = self.get_gender_score(text)
        if masc > fem + 1:
            return 'M'
        elif fem > masc + 1:
            return 'F'
        return None
    
    def analyze_paragraphs(self, paragraphs):
        """Analyze a list of paragraphs for gender inconsistencies."""
        self.issues = []
        prev_gender = None
        prev_row = None
        
        for paragraph in paragraphs:
            if not hasattr(paragraph, 'translation') or not paragraph.translation:
                continue
            
            current_gender = self.get_dominant_gender(paragraph.translation)
            
            # Check for sudden gender flip
            if prev_gender and current_gender and prev_gender != current_gender:
                self.issues.append({
                    'row': paragraph.row,
                    'prev_row': prev_row,
                    'change': f'{prev_gender}→{current_gender}',
                    'text_preview': paragraph.translation[:80] + '...' if len(paragraph.translation) > 80 else paragraph.translation
                })
            
            if current_gender:
                prev_gender = current_gender
                prev_row = paragraph.row
        
        return self.issues
    
    def generate_report(self):
        """Generate a formatted report of detected issues."""
        if not self.issues:
            return None
        
        report = [
            sep(),
            '⚠️ GENDER CONSISTENCY ANALYSIS ⚠️',
            sep('┈'),
            f'Detected {len(self.issues)} potential gender mismatch(es):',
            ''
        ]
        
        for issue in self.issues[:10]:  # Limit to first 10
            report.append(f"  Row {issue['row']}: {issue['change']} change")
            report.append(f"    Preview: \"{issue['text_preview']}\"")
            report.append('')
        
        if len(self.issues) > 10:
            report.append(f"  ... and {len(self.issues) - 10} more issues.")
        
        report.append(sep())
        report.append('TIP: Review these rows manually in the translated ebook.')
        
        return '\n'.join(report)


class Glossary:
    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.glossary = []

    def load_from_file(self, path):
        content = None
        try:
            with open(path, 'r', newline=None) as f:
                content = f.read().strip()
        except Exception:
            pass
        if not content:
            return
        groups = re.split(r'\n{2,}', content.strip(u'\ufeff'))
        for group in filter(trim, groups):
            group = group.split('\n')
            self.glossary.append(
                (group[0], group[0] if len(group) < 2 else group[1]))

    def replace(self, content):
        for wid, words in enumerate(self.glossary):
            replacement = self.placeholder[0].format(format(wid, '06'))
            content = content.replace(words[0], replacement)
        return content

    def restore(self, content):
        for wid, words in enumerate(self.glossary):
            pattern = self.placeholder[1].format(format(wid, '06'))
            # Eliminate the impact of backslashes on substitution.
            content = re.sub(pattern, lambda _: words[1], content)
        return content

    def get_terms(self):
        """Return glossary terms as a list of (source, target) tuples for LLM injection."""
        return self.glossary.copy()


class ProgressBar:
    total = 0
    length = 0.0
    step = 0

    _count = 0

    def load(self, total):
        self.total = total
        self.step = 1.0 / total

    @property
    def count(self):
        self._count += 1
        self.length += self.step
        return self._count


class Translation:
    def __init__(self, translator, glossary):
        self.translator = translator
        self.glossary = glossary

        self.fresh = False
        self.batch = False
        self.progress = dummy
        self.log = dummy
        self.streaming = dummy
        self.callback = dummy
        self.cancel_request = dummy

        self.total = 0
        self.progress_bar = ProgressBar()
        self.abort_count = 0
        
        # Dynamic glossary for term tracking (optional)
        self.dynamic_glossary = None

    def set_fresh(self, fresh):
        self.fresh = fresh

    def set_batch(self, batch):
        self.batch = batch

    def set_progress(self, progress):
        self.progress = progress

    def set_logging(self, log):
        self.log = log

    def set_streaming(self, streaming):
        self.streaming = streaming

    def set_callback(self, callback):
        self.callback = callback

    def set_cancel_request(self, cancel_request):
        self.cancel_request = cancel_request
        self.translator.cancel_request = cancel_request

    def set_dynamic_glossary(self, dynamic_glossary):
        """Set dynamic glossary for term tracking during translation."""
        self.dynamic_glossary = dynamic_glossary

    def need_stop(self):
        # Cancel the request if there are more than max continuous errors.
        return self.translator.max_error_count > 0 and \
            self.abort_count >= self.translator.max_error_count

    def translate_text(self, row, text, retry=0, interval=0, context=None, glossary_terms=None):
        """Translation engine service error code documentation:
        * https://cloud.google.com/apis/design/errors
        * https://www.deepl.com/docs-api/api-access/error-handling/
        * https://platform.openai.com/docs/guides/error-codes/api-errors
        * https://ai.youdao.com/DOCSIRMA/html/trans/api/wbfy/index.html
        * https://api.fanyi.baidu.com/doc/21
        """
        if self.cancel_request():
            raise TranslationCanceled(_('Translation canceled.'))
        try:
            translation = self.translator.translate(text, context=context, glossary_terms=glossary_terms)
            self.abort_count = 0
            return translation
        except Exception as e:
            if self.cancel_request() or self.need_stop():
                raise TranslationCanceled(_('Translation canceled.'))
            self.abort_count += 1
            message = _(
                'Failed to retrieve data from translate engine API.')
            if retry >= self.translator.request_attempt:
                raise TranslationFailed('{}\n{}'.format(message, str(e)))
            retry += 1
            interval += 5
            # Logging any errors that occur during translation.
            logged_text = text[:200] + '...' if len(text) > 200 else text
            error_messages = [
                sep(), _('Original: {}').format(logged_text), sep('┈'),
                _('Status: Failed {} times / Sleeping for {} seconds')
                .format(retry, interval), sep('┈'), _('Error: {}')
                .format(traceback_error())]
            if row >= 0:
                error_messages.insert(1, _('Row: {}').format(row))
            self.log('\n'.join(error_messages), True)
            if self.translator.match_error(str(e)):
                raise TranslationCanceled(_('Translation canceled.'))
            time.sleep(interval)
            return self.translate_text(row, text, retry, interval, context)

    def translate_paragraph(self, paragraph):
        if self.cancel_request():
            raise TranslationCanceled(_('Translation canceled.'))
        if paragraph.translation and not self.fresh:
            paragraph.is_cache = True
            return
        self.streaming('')
        self.streaming(_('Translating...'))
        text = self.glossary.replace(paragraph.original)
        context = {
            'paragraphs': []  # Will hold up to 3 previous paragraph contexts
        }
        # Collect up to 3 previous translated paragraphs for richer context
        if hasattr(self, 'all_paragraphs') and paragraph.row > 0:
            try:
                prev_p = getattr(paragraph, 'prev_paragraph', None)
                count = 0
                while prev_p and count < 3:
                    if prev_p.translation:
                        context['paragraphs'].insert(0, {
                            'original': prev_p.original[:500] if len(prev_p.original) > 500 else prev_p.original,
                            'translation': prev_p.translation[:500] if len(prev_p.translation) > 500 else prev_p.translation
                        })
                    prev_p = getattr(prev_p, 'prev_paragraph', None)
                    count += 1
            except Exception:
                pass

        glossary_terms = self.glossary.get_terms()
        translation = self.translate_text(paragraph.row, text, context=context, glossary_terms=glossary_terms)
        # Process streaming text
        if isinstance(translation, GeneratorType):
            temp = ''
            try:
                if self.total == 1:
                    # Only for a single translation.
                    clear = True
                    for char in translation:
                        if self.cancel_request():
                            break
                        if clear:
                            self.streaming('')
                            clear = False
                        self.streaming(char)
                        time.sleep(0.05)
                        temp += char
                else:
                    for char in translation:
                        if self.cancel_request():
                            break
                        temp += char
            except Exception as e:
                self.log(_('Streaming error: {}').format(str(e)), True)
            translation = temp
        translation = self.glossary.restore(translation)
        paragraph.translation = translation.strip()
        paragraph.engine_name = self.translator.name
        paragraph.target_lang = self.translator.get_target_lang()
        # paragraph.separator = self.translator.separator
        paragraph.is_cache = False
        
        # Track for dynamic glossary (term detection)
        if self.dynamic_glossary:
            try:
                self.dynamic_glossary.track_translation(
                    paragraph.original, paragraph.translation)
            except Exception:
                pass  # Don't fail translation if tracking fails
        
        # Check if translation was incomplete (non-STOP finish reason)
        finish_reason = getattr(self.translator, 'last_finish_reason', None)
        if finish_reason and finish_reason != 'STOP':
            # Mark as not aligned so it shows yellow in the table
            paragraph.aligned = False
            paragraph.error = f'Incomplete translation ({finish_reason})'
            self.log(_('⚠️ Warning: Translation incomplete - {}').format(finish_reason), True)

    def process_translation(self, paragraph):
        self.progress(
            self.progress_bar.length, _('Translating: {}/{}').format(
                self.progress_bar.count, self.progress_bar.total))

        self.streaming(paragraph)
        self.callback(paragraph)

        row = paragraph.row
        original = paragraph.original.strip()
        if paragraph.error is None:
            self.log(sep())
            if row >= 0:
                self.log(_('Row: {}').format(row))
            self.log(_('Original: {}').format(original))
            self.log(sep('┈'))
            message = _('Translation: {}')
            if paragraph.is_cache:
                message = _('Translation (Cached): {}')
            self.log(message.format(paragraph.translation.strip()))

    def handle(self, paragraphs=[]):
        start_time = time.time()
        char_count = 0
        previous_paragraph = None
        for paragraph in paragraphs:
            paragraph.context = previous_paragraph.original if previous_paragraph else None
            paragraph.prev_paragraph = previous_paragraph
            previous_paragraph = paragraph
            self.total += 1
            char_count += len(paragraph.original)
        
        self.all_paragraphs = paragraphs
        
        # Get engine and model info
        engine_name = self.translator.name
        model_name = getattr(self.translator, 'model', None)
        merge_length = getattr(self.translator, 'merge_length', None)
        if merge_length is None:
            # Try to get from config
            from .config import get_config
            merge_length = get_config().get('merge_length', 0)
        
        # Calculate cost estimate
        cost_value, cost_details, is_free = estimate_cost(char_count, engine_name, model_name)

        self.log(sep())
        self.log(_('Start to translate ebook content'))
        self.log(sep('┈'))
        self.log(_('Item count: {}').format(self.total))
        self.log(_('Character count: {:,}').format(char_count))
        
        # Log engine/model info
        if model_name:
            self.log(_('Engine: {} ({})').format(engine_name, model_name))
        else:
            self.log(_('Engine: {}').format(engine_name))
        
        # Log merge length if applicable
        if merge_length and merge_length > 0:
            self.log(_('Characters per request: ~{} (merge mode)').format(merge_length))
        
        # Log estimated tokens for token-based engines
        if model_name or engine_name in ['Gemini', 'ChatGPT', 'Claude']:
            tokens_estimate = int(char_count / 4)
            self.log(_('Estimated tokens: ~{:,}').format(tokens_estimate))
        
        # Log cost estimate
        self.log(_('Estimated cost: {}').format(cost_details))
        self.log(sep('┈'))

        if self.total < 1:
            raise Exception(_('There is no content need to translate.'))
        self.progress_bar.load(self.total)

        handler = Handler(
            paragraphs, self.translator.concurrency_limit,
            self.translate_paragraph, self.process_translation,
            self.translator.request_interval)
        handler.handle()

        # Calculate final statistics
        consuming = round((time.time() - start_time) / 60, 2)
        
        self.log(sep())
        if self.batch and self.need_stop():
            raise Exception(_('Translation failed.'))
        
        self.log(_('Time consuming: {} minutes').format(consuming))
        self.log(_('Translation completed.'))
        
        # === FINAL SUMMARY ===
        self.log(sep())
        self.log('📋 TRANSLATION SUMMARY')
        self.log(sep('┈'))
        self.log(_('✅ Translated: {} items ({:,} characters)').format(self.total, char_count))
        self.log(_('⏱️ Duration: {} minutes').format(consuming))
        self.log(_('💰 Estimated API cost: {}').format(cost_details))
        
        if model_name:
            self.log(_('🤖 Model used: {}').format(model_name))
        
        # === REVIEW SUGGESTIONS ===
        self.log(sep('┈'))
        self.log('🔍 REVIEW SUGGESTIONS:')
        self.log('  • Check first 2-3 chapters for consistent terminology')
        self.log('  • Verify proper nouns were preserved correctly')
        
        # Romanian-specific suggestions
        if self.translator.target_lang and 'roman' in self.translator.target_lang.lower():
            self.log('  • Verify gender agreement in Romanian pronouns (el/ea)')
            self.log('  • Check for unnatural literal translations')
            self.log('  • Review dialogue passages for natural flow')
        
        # Merge mode warning
        if merge_length and merge_length > 0:
            self.log('  • Merge mode was used - check paragraph boundaries')
        
        self.log(sep())
        
        # Run gender consistency analysis for Romanian translations
        if hasattr(self, 'all_paragraphs') and self.translator.target_lang and 'roman' in self.translator.target_lang.lower():
            try:
                analyzer = GenderAnalyzer()
                analyzer.analyze_paragraphs(self.all_paragraphs)
                report = analyzer.generate_report()
                if report:
                    self.log(report)
            except Exception:
                pass  # Don't fail translation if analysis fails
        
        # Dynamic glossary stats
        if self.dynamic_glossary:
            try:
                stats = self.dynamic_glossary.get_stats()
                if stats['total_unique_terms'] > 0:
                    self.log(sep())
                    self.log('📚 DYNAMIC GLOSSARY STATS')
                    self.log(sep('┈'))
                    self.log(_('  • Unique terms detected: {}').format(stats['total_unique_terms']))
                    self.log(_('  • High-frequency terms (≥3x): {}').format(stats['high_frequency_terms']))
                    if stats['inconsistent_terms'] > 0:
                        self.log(_('  ⚠️ Inconsistent translations: {}').format(stats['inconsistent_terms']))
                    self.log(sep())
            except Exception:
                pass
        
        self.progress(1, _('Translation completed.'))


def get_engine_class(engine_name=None):
    config = get_config()
    engine_name = engine_name or config.get('translate_engine')
    engines: dict[str, type[Base]] = {
        engine.name: engine for engine in builtin_engines}
    custom_engines = config.get('custom_engines')
    if engine_name in engines:
        engine_class = engines[engine_name]
    elif engine_name in custom_engines:
        engine_class = CustomTranslate
        engine_data = json.loads(custom_engines.get(engine_name))
        engine_class.set_engine_data(engine_data)
    else:
        engine_class = GoogleFreeTranslateNew
    engine_preferences = config.get('engine_preferences')
    engine_class.set_config(engine_preferences.get(engine_class.name) or {})
    return engine_class


def get_translator(engine_class=None):
    config = get_config()
    engine_class = engine_class or get_engine_class()
    translator = engine_class()
    translator.set_search_paths(config.get('search_paths'))
    if config.get('proxy_enabled'):
        translator.set_proxy(config.get('proxy_setting'))
    translator.set_merge_enabled(config.get('merge_enabled'))
    return translator


def get_translation(translator, log=None):
    config = get_config()
    glossary = Glossary(translator.placeholder)
    if config.get('glossary_enabled'):
        glossary.load_from_file(config.get('glossary_path'))
    translation = Translation(translator, glossary)
    if get_config().get('log_translation'):
        translation.set_logging(log)
    
    # Enable dynamic glossary for term tracking (enabled by default)
    if config.get('dynamic_glossary_enabled', True):
        translation.set_dynamic_glossary(DynamicGlossary())
    
    return translation

