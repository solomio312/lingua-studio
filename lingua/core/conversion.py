"""
EPUB conversion pipeline for Lingua standalone app.

Migrated from Calibre plugin lib/conversion.py.
Changes:
  - calibre.ebooks.conversion.plumber.Plumber → ebooklib.epub
  - calibre.gui2.Dispatcher → removed (standalone uses QThread directly)
  - calibre.utils.logging.Log → Python logging
  - calibre.ebooks.metadata → ebooklib metadata
  - calibre.ptempfile → tempfile
  - calibre.sanitize_file_name → own implementation
  - ConversionWorker (Calibre job system) → removed, replaced with direct calls
"""

import os
import re
import logging
import os.path
from typing import Callable, Any
from tempfile import gettempdir

from lxml import etree

import lingua
from .config import get_config
from .utils import sep, uid, open_path, open_file
from .cache import get_cache
from .element import (
    get_element_handler, get_srt_elements, get_page_elements,
    get_pgn_elements)
from .translation import get_translator, get_translation
from .exception import ConversionAbort


log = logging.getLogger('lingua.conversion')


# Helper: identity function replacing Calibre's _() i18n
def _(s):
    return s


def sanitize_file_name(name):
    """Simple filename sanitizer (replaces calibre.sanitize_file_name)."""
    # Remove characters invalid in Windows filenames
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove control characters
    name = re.sub(r'[\x00-\x1f]', '', name)
    return name.strip('. ')


class EpubPage:
    """Wrapper to make ebooklib items look like Calibre OEB pages.
    
    Calibre's OEB system exposes pages with:
      - page.href (str): relative path within EPUB
      - page.data (lxml._Element): parsed HTML/XHTML tree
      - page.id (str): unique identifier
    
    This class provides the same interface for ebooklib items.
    """
    def __init__(self, item):
        self._item = item
        self.href = item.get_name()
        self.id = item.get_id() or self.href
        self._data = None
    
    @property
    def data(self):
        if self._data is None:
            try:
                content = self._item.get_content()
                # Use XML parser first to preserve XHTML namespaces
                # (HTMLParser strips them, which breaks body lookup)
                try:
                    self._data = etree.fromstring(content)
                except etree.XMLSyntaxError:
                    # Fallback to HTML parser for malformed content
                    parser = etree.HTMLParser(encoding='utf-8')
                    self._data = etree.fromstring(content, parser)
            except Exception:
                self._data = None
        return self._data


def extract_epub_pages(epub_path):
    """Extract pages from an EPUB using ebooklib.
    
    Returns a list of EpubPage objects compatible with the Extraction class.
    """
    try:
        from ebooklib import epub, ITEM_DOCUMENT
    except ImportError:
        raise ImportError(
            "ebooklib is required for EPUB processing. "
            "Install with: pip install ebooklib")
    
    book = epub.read_epub(epub_path, options={'ignore_ncx': False})
    pages = []
    
    # Get spine order for reading-order sorting
    spine_ids = [item_id for item_id, linear in book.spine]
    spine_hrefs = []
    for item_id in spine_ids:
        item = book.get_item_with_id(item_id)
        if item:
            spine_hrefs.append(item.get_name())
    
    # Get all document items
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        page = EpubPage(item)
        if page.data is not None:
            pages.append(page)
    
    return pages, spine_hrefs, book


def convert_book(
        input_path, output_path, translation, element_handler, cache,
        debug_info, encoding, notification) -> None:
    """Process EPUB ebooks using ebooklib (replaces Calibre Plumber)."""
    try:
        from ebooklib import epub
    except ImportError:
        raise ImportError("ebooklib is required. Install with: pip install ebooklib")
    
    log.info('Translating ebook content... (this will take a while)')
    log.info(debug_info)
    
    if callable(notification):
        notification(0.0, _('Extracting EPUB content...'))
    
    # Read the EPUB
    pages, spine_hrefs, book = extract_epub_pages(input_path)
    
    # Extract spine order if configured
    spine_order = None
    if get_config().get('use_spine_order', False):
        spine_order = spine_hrefs
    
    # Get elements from pages
    elements = list(get_page_elements(pages, spine_order))
    
    original_group = element_handler.prepare_original(elements)
    cache.save(original_group)
    
    if callable(notification):
        notification(0.1, _('Starting translation...'))
    
    translation.set_progress(notification if callable(notification) else lambda *a: None)
    
    paragraphs = cache.all_paragraphs()
    translation.handle(paragraphs)
    element_handler.add_translations(paragraphs)
    
    log.info(sep())
    log.info(_('Start to convert ebook format...'))
    log.info(sep())
    
    if callable(notification):
        notification(0.9, _('Writing translated EPUB...'))
    
    # Write modified content back to EPUB items
    from ebooklib import ITEM_DOCUMENT
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        # Find matching page and serialize modified XML back
        for page in pages:
            if page.href == item.get_name() and page.data is not None:
                try:
                    content = etree.tostring(
                        page.data, encoding='unicode', method='html')
                    item.set_content(content.encode('utf-8'))
                except Exception as e:
                    log.warning(f'Failed to write page {page.href}: {e}')
                break
    
    # Write output EPUB
    epub.write_epub(output_path, book)
    
    if callable(notification):
        notification(1.0, _('Translation completed.'))


def convert_srt(
        input_path, output_path, translation, element_handler, cache,
        debug_info, encoding, notification) -> None:
    log.info('Translating subtitles content... (this will take a while)')
    log.info(debug_info)

    elements = get_srt_elements(input_path, encoding)
    original_group = element_handler.prepare_original(elements)
    cache.save(original_group)

    paragraphs = cache.all_paragraphs()
    translation.set_progress(notification if callable(notification) else lambda *a: None)
    translation.handle(paragraphs)
    element_handler.add_translations(paragraphs)

    log.info(sep())
    log.info(_('Starting to output subtitles file...'))
    log.info(sep())

    with open(output_path, 'w') as file:
        file.write('\n\n'.join([e.get_translation() for e in elements]))

    log.info(_('The translation of the subtitles file was completed.'))


def convert_pgn(
        input_path, output_path, translation, element_handler, cache,
        debug_info, encoding, notification) -> None:
    log.info('Translating PGN content... (this may take a while)')
    log.info(debug_info)

    elements = get_pgn_elements(input_path, encoding)
    original_group = element_handler.prepare_original(elements)
    cache.save(original_group)

    paragraphs = cache.all_paragraphs()
    translation.set_progress(notification if callable(notification) else lambda *a: None)
    translation.handle(paragraphs)
    element_handler.add_translations(paragraphs)

    log.info(sep())
    log.info(_('Starting to output PGN file...'))
    log.info(sep())

    pgn_content = open_file(input_path, encoding)
    for element in elements:
        pgn_content = pgn_content.replace(
            element.get_raw(), element.get_translation(), 1)
    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(pgn_content)

    log.info(_('The translation of the PGN file was completed.'))


extra_formats = {
    'srt': {
        'extractor': get_srt_elements,
        'convertor': convert_srt,
    },
    'pgn': {
        'extractor': get_pgn_elements,
        'convertor': convert_pgn,
    }
}


def extract_item(input_path, input_format, encoding, callback=None):
    """Extract elements from an ebook for preview/preparation."""
    handler = extra_formats.get(input_format)
    if handler is not None:
        extractor = handler.get('extractor')
        return extractor(input_path, encoding)
    else:
        return extract_book(input_path, encoding)


def extract_book(input_path, encoding=None):
    """Extract elements from an EPUB using ebooklib."""
    pages, spine_hrefs, book = extract_epub_pages(input_path)
    
    spine_order = None
    if get_config().get('use_spine_order', False):
        spine_order = spine_hrefs
    
    elements = list(get_page_elements(pages, spine_order))
    return elements


def convert_item(
        ebook_title, input_path, output_path, source_lang, target_lang,
        cache_only, is_batch, format, encoding, direction, notification=None):
    """Main entry point for translating an ebook.
    
    Replaces the Calibre job system version with direct synchronous execution.
    """
    config = get_config()
    translator = get_translator()
    translator.set_source_lang(source_lang)
    translator.set_target_lang(target_lang)

    # Get chunking method from config
    chunking_method = config.get('chunking_method', 'standard')
    
    element_handler = get_element_handler(
        translator.placeholder, translator.separator, direction, chunking_method)
    element_handler.set_translation_lang(
        translator.get_iso639_target_code(target_lang))

    merge_length = str(element_handler.get_merge_length())
    _encoding = ''
    if encoding.lower() != 'utf-8':
        _encoding = encoding.lower()
    
    # Include chunking_method and normalizer version in cache_id
    cache_id = uid(
        input_path + translator.name + target_lang + merge_length 
        + _encoding + chunking_method + 'norm_v1')
    cache = get_cache(cache_id)
    cache.set_cache_only(cache_only)
    cache.set_info('title', ebook_title)
    cache.set_info('engine_name', translator.name)
    cache.set_info('target_lang', target_lang)
    cache.set_info('merge_length', merge_length)
    cache.set_info('chunking_method', chunking_method)
    cache.set_info('app_version', lingua.__version__)

    translation = get_translation(
        translator, lambda text, error=False: log.info(text))
    translation.set_batch(is_batch)
    translation.set_callback(cache.update_paragraph)

    debug_info = '{0}\n| Diagnosis Information\n{0}'.format(sep())
    debug_info += '\n| Lingua Version: %s\n' % lingua.__version__
    debug_info += '| Translation Engine: %s\n' % translator.name
    debug_info += '| Source Language: %s\n' % source_lang
    debug_info += '| Target Language: %s\n' % target_lang
    debug_info += '| Encoding: %s\n' % encoding
    debug_info += '| Cache Enabled: %s\n' % cache.is_persistence()
    debug_info += '| Chunking Method: %s\n' % chunking_method
    debug_info += '| Merging Length: %s\n' % element_handler.merge_length
    debug_info += '| Concurrent requests: %s\n' % translator.concurrency_limit
    debug_info += '| Request Interval: %s\n' % translator.request_interval
    debug_info += '| Request Attempt: %s\n' % translator.request_attempt
    debug_info += '| Request Timeout: %s\n' % translator.request_timeout
    # Show context cache status if using Gemini
    cached_name = getattr(translator, 'cached_content_name', '')
    if cached_name:
        debug_info += '| ⚡ Context Cache: ACTIVE (%s)\n' % cached_name
    debug_info += '| Input Path: %s\n' % input_path
    debug_info += '| Output Path: %s' % output_path

    handler = extra_formats.get(format)
    convertor = convert_book if handler is None else handler['convertor']
    convertor(
        input_path, output_path, translation, element_handler, cache,
        debug_info, encoding, notification)
    cache.done()
