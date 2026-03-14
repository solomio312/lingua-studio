"""
Background workers for the Lingua UI.

Contains QThread-based workers to perform heavy I/O operations (like API requests)
without blocking the main PySide6 event loop.
"""

import os
import logging
import time
import traceback
from types import GeneratorType

from PySide6.QtCore import QObject, Signal

import lingua
from lingua.core.translation import get_engine_class, get_translator, estimate_cost
from lingua.core.exception import TranslationCanceled
from lingua.core.config import get_config
from lingua.core.utils import uid
from lingua.core.cache import get_cache
from lingua.core.element import get_element_handler, get_page_elements
from lingua.core.conversion import extract_epub_pages

print(f"DEBUG WORKER: Workers module loaded from {__file__}", flush=True)


class TranslationWorker(QObject):
    """
    Worker that processes a list of EPUB elements and translates them asynchronously.
    """
    # Signals to communicate with the main UI thread safely
    progress_updated = Signal(int, int)  # current, total
    row_completed = Signal(object, str)  # Paragraph object, status
    error_occurred = Signal(str)
    log_message = Signal(str)  # For the Log tab
    finished = Signal()

    STATUS_TRANSLATING = "translating"
    STATUS_DONE = "done"
    STATUS_CACHED = "cached"
    STATUS_ERROR = "error"
    STATUS_CANCELED = "canceled"

    def __init__(self, elements, engine_name, source_lang="Auto", target_lang="Romanian", force=False):
        super().__init__()
        self.elements = elements
        self.engine_name = engine_name
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.force = force
        self._is_canceled = False
        self.model_name = engine_name
        self.total_cost = None
        self.cost_details = "N/A"

    def cancel(self):
        """Request the worker to stop processing."""
        self._is_canceled = True

    def _check_canceled(self):
        """Internal helper to raise cancellation exception if signal received."""
        if self._is_canceled:
            raise TranslationCanceled("Canceled by user")

    def run(self):
        """Main loop executed in the background thread."""
        start_time = time.time()
        items_translated = 0
        chars_translated = 0

        try:
            print(f"DEBUG WORKER: TranslationWorker starting. Mode: {self.engine_name}, Items: {len(self.elements)}", flush=True)
            
            # 1. Initialize the specified translation engine
            engine_class = get_engine_class(self.engine_name)
            translator = get_translator(engine_class)
            translator.set_source_lang(self.source_lang)
            translator.set_target_lang(self.target_lang)

            # Defensive checker assignment
            if hasattr(translator, "set_cancel_checker"):
                translator.set_cancel_checker(lambda: self._is_canceled)
            else:
                translator.cancel_request = lambda: self._is_canceled

            # Determine specific model for accurate pricing
            self.model_name = getattr(translator, "model", self.engine_name)

            total = len(self.elements)
            self.progress_updated.emit(0, total)

            # --- STARTUP LOG SUMMARY ---
            total_chars = sum(len(getattr(e, "original", "") or getattr(e, "raw", "") or "") for e in self.elements)
            self.total_cost, self.cost_details, _ = estimate_cost(total_chars, self.engine_name, self.model_name)

            self.log_message.emit(
                "\n".join([
                    "Start to translate ebook content",
                    "-" * 50,
                    f"Item count: {total}",
                    f"Character count: {total_chars}",
                    f"Engine: {self.engine_name} ({self.model_name})",
                    f"Estimated cost: {self.cost_details}",
                    "-" * 50,
                    ""
                ])
            )

            # 2. Process each paragraph
            for i, elem in enumerate(self.elements):
                self._check_canceled()

                # Fast path: If already translated, skip API call unless forced
                existing_trans = getattr(elem, "translation", None)
                if existing_trans is not None and existing_trans != "" and not self.force:
                    print(f"DEBUG WORKER: [Row {i}] Using cached translation.", flush=True)
                    self.row_completed.emit(elem, self.STATUS_CACHED)
                    self.progress_updated.emit(i + 1, total)
                    continue

                # Get original text to translate
                original_text = getattr(elem, "original", "") or getattr(elem, "raw", "")
                if not original_text or not original_text.strip():
                    print(f"DEBUG WORKER: [Row {i}] Skipping EMPTY row.", flush=True)
                    self.row_completed.emit(elem, self.STATUS_DONE)
                    self.progress_updated.emit(i + 1, total)
                    continue

                # Notify UI that this row started translating
                print(f"DEBUG WORKER: [Row {i}] Starting translation... (id={id(elem)})", flush=True)
                elem._temp_status = self.STATUS_TRANSLATING
                self.row_completed.emit(elem, self.STATUS_TRANSLATING)
                self.log_message.emit(f"Row: {getattr(elem, 'row', i)}\nOriginal: {original_text}")

                try:
                    # 3. Blocking HTTP API Call
                    translated = translator.translate(original_text)

                    # Consume generator if the engine streams
                    if isinstance(translated, GeneratorType):
                        parts = []
                        for chunk in translated:
                            self._check_canceled()
                            parts.append(chunk)
                        translated = "".join(parts)

                    self._check_canceled()

                    # Save result back to memory
                    elem.translation = translated
                    elem.engine_name = self.engine_name
                    elem.target_lang = self.target_lang
                    elem.error = None
                    elem._temp_status = self.STATUS_DONE

                    self.log_message.emit(f"Translation: {translated}\n{'-' * 50}\n")

                    items_translated += 1
                    chars_translated += len(original_text)

                    # Notify UI that this row is ready
                    self.row_completed.emit(elem, self.STATUS_DONE)
                    self.progress_updated.emit(i + 1, total)

                except TranslationCanceled:
                    print(f"DEBUG WORKER: [Row {i}] Translation Canceled in loop.", flush=True)
                    elem._temp_status = self.STATUS_CANCELED
                    self.row_completed.emit(elem, self.STATUS_CANCELED)
                    self.log_message.emit(f"Translation canceled by user at row {i}.")
                    break

                except Exception as api_err:
                    print(f"DEBUG WORKER: [Row {i}] API FAILED: {api_err}", flush=True)
                    elem.error = str(api_err)
                    elem._temp_status = self.STATUS_ERROR
                    self.row_completed.emit(elem, self.STATUS_ERROR)
                    self.log_message.emit(f"⚠️ Row {i} FAILED: {api_err}\n{'-' * 50}\n")
                    continue

        except Exception as e:
            logging.exception("Translation worker failed")
            self.error_occurred.emit(str(e))

        finally:
            end_time = time.time()
            duration_mins = (end_time - start_time) / 60.0
            
            if self.total_cost is not None:
                summary_parts = [
                    f"Time consuming: {duration_mins:.2f} minutes",
                    "Translation completed.",
                    "-" * 50,
                    "📑 TRANSLATION SUMMARY",
                    "-" * 50,
                    f"✅ Translated: {items_translated} items ({chars_translated} characters)",
                    f"⏱ Duration: {duration_mins:.2f} minutes",
                    f"💰 Estimated API cost: {self.cost_details}",
                    f"🤖 Model used: {self.model_name}",
                    "-" * 50,
                ]
                self.log_message.emit("\n".join(summary_parts))
                
            self.finished.emit()

class ExportWorker(QObject):
    """
    Worker that builds the final output file asynchronously.
    """
    progress = Signal(int, str)  # percentage, status_text
    error = Signal(str)
    finished = Signal(str)       # final_output_path

    def __init__(self, original_path, output_path, cache, format="EPUB"):
        super().__init__()
        self.original_path = original_path
        self.output_path = output_path
        self.cache = cache
        self.format = format.upper()
        
    def run(self):
        try:
            print(f"DEBUG EXPORT: Starting worker for {self.format}...")
            if self.format == "EPUB":
                from lingua.core.export import ZipEpubBuilder
                builder = ZipEpubBuilder(self.original_path, self.output_path, self.cache)
            elif self.format == "SRT":
                from lingua.core.export import SrtBuilder
                builder = SrtBuilder(self.cache, self.output_path)
            elif self.format == "TXT":
                from lingua.core.export import TextBuilder
                builder = TextBuilder(self.cache, self.output_path)
            elif self.format in ["AZW3", "DOCX", "PDF", "MOBI"]:
                from lingua.core.export import CalibreBuilder
                builder = CalibreBuilder(self.original_path, self.output_path, self.cache, format=self.format)
            else:
                self.error.emit(f"Format {self.format} not implemented yet.")
                return
            
            # Pass our worker's emit function directly as the progress callback
            output = builder.build(progress_callback=self.progress.emit)
            
            self.finished.emit(output)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logging.exception(f"Export worker failed for format {self.format}")
            self.error.emit(str(e))


class ExtractionWorker(QObject):
    """Worker to extract EPUB paragraphs in a background thread."""
    finished = Signal(object)   # emits a dict with context
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, epub_path):
        super().__init__()
        self.epub_path = epub_path

    def run(self):
        try:
            print(f"DEBUG WORKER: ExtractionWorker starting for {self.epub_path}")
            self.progress.emit('Extracting paragraphs...')
            
            config = get_config()
            target_lang = config.get('target_lang', 'Romanian')
            chunking_method = config.get('chunking_method', 'standard')
            engine_name = config.get('translate_engine', 'Google(Free)New')
            
            engine_class = get_engine_class(engine_name)
            translator = get_translator(engine_class)
            
            # Create Element Handler
            element_handler = get_element_handler(
                translator.placeholder, translator.separator, 'ltr', chunking_method)
            element_handler.set_translation_lang(
                translator.get_iso639_target_code(target_lang))

            merge_length = str(element_handler.get_merge_length())
            cache_id = uid(
                self.epub_path + translator.name + target_lang + merge_length 
                + 'utf-8' + chunking_method + 'norm_v1')
            
            cache = get_cache(cache_id)
            cache.set_info('title', os.path.basename(self.epub_path))
            cache.set_info('engine_name', translator.name)
            cache.set_info('target_lang', target_lang)
            cache.set_info('merge_length', merge_length)
            cache.set_info('chunking_method', chunking_method)
            cache.set_info('app_version', getattr(lingua, '__version__', '1.0.0'))

            # 1. Essential Extraction (needed for book metadata/images regardless of cache)
            pages, spine_hrefs, book = extract_epub_pages(self.epub_path)
            
            # 2. Check if cache is already populated
            paragraphs = cache.all_paragraphs()
            
            if paragraphs:
                print(f"DEBUG WORKER: Cache already populated with {len(paragraphs)} items. skipping element extraction.")
            else:
                # 3. Full Extraction and Chunking (only if cache is empty)
                self.progress.emit('Performing full text extraction...')
                spine_order = spine_hrefs if config.get('use_spine_order', False) else None
                elements = list(get_page_elements(pages, spine_order))
                
                # Prepare originals and save to cache
                original_group = element_handler.prepare_original(elements)
                
                # We NO LONGER call cache.clear() here. 
                # cache.save() handles intelligent merging/updating.
                cache.save(original_group)
                paragraphs = cache.all_paragraphs()

            print(f"DEBUG WORKER: Extraction done. Found {len(paragraphs)} paragraphs.")
            
            context = {
                'book': book,
                'pages': pages,
                'element_handler': element_handler,
                'cache': cache,
                'paragraphs': paragraphs
            }
            self.finished.emit(context)
        except Exception as e:
            print(f"DEBUG WORKER: Extraction ERROR: {e}")
            traceback.print_exc()
            logging.exception('Extraction failed')
            self.error.emit(str(e))
