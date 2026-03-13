"""
Background workers for the Lingua UI.

Contains QThread-based workers to perform heavy I/O operations (like API requests)
without blocking the main PySide6 event loop.
"""

import logging
from PySide6.QtCore import QObject, Signal

from lingua.core.translation import get_engine_class, get_translator

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

    def __init__(self, elements, engine_name, source_lang='Auto', target_lang='Romanian', force=False):
        super().__init__()
        self.elements = elements
        self.engine_name = engine_name
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.force = force
        self._is_canceled = False

    def cancel(self):
        """Request the worker to stop processing."""
        self._is_canceled = True

    def run(self):
        """Main loop executed in the background thread."""
        import time
        try:
            print(f"DEBUG WORKER: TranslationWorker starting. Mode: {self.engine_name}, Items: {len(self.elements)}", flush=True)
            start_time = time.time()
            items_translated = 0
            chars_translated = 0
            
            # 1. Initialize the specified translation engine
            engine_class = get_engine_class(self.engine_name)
            translator = get_translator(engine_class)
            translator.set_source_lang(self.source_lang)
            translator.set_target_lang(self.target_lang)
            translator.cancel_request = lambda: self._is_canceled
            
            # Determine specific model for accurate pricing
            self.model_name = getattr(translator, 'model', self.engine_name)
            
            total = len(self.elements)
            self.progress_updated.emit(0, total)
            
            # --- STARTUP LOG SUMMARY ---
            total_chars = sum(len(getattr(e, 'original', '') or getattr(e, 'raw', '') or '') for e in self.elements)
            
            # Use dynamic pricing from core logic
            from lingua.core.translation import estimate_cost
            self.total_cost, self.cost_details, _ = estimate_cost(total_chars, self.engine_name, self.model_name)
            
            log_parts = [
                "Start to translate ebook content",
                "-" * 50,
                f"Item count: {total}",
                f"Character count: {total_chars}",
                f"Engine: {self.engine_name} ({self.model_name})",
                f"Estimated cost: {self.cost_details}",
                "-" * 50,
                ""
            ]
            self.log_message.emit("\n".join(log_parts))
            # ---------------------------

            # 2. Process each paragraph
            for i, elem in enumerate(self.elements):
                if self._is_canceled:
                    self.log_message.emit(f"Translation canceled by user at row {i}.")
                    break
                
                # Update status to "Translating..." in the UI
                setattr(elem, '_temp_status', 'Translating...')
                self.row_completed.emit(elem, 'Translating...')
                
                # Fast path: If already translated (from cache or previous run), skip API call
                # ONLY if we are not in "force" mode (e.g. ad-hoc single row translation)
                existing_trans = getattr(elem, 'translation', None)
                if existing_trans and not self.force:
                    print(f"DEBUG WORKER: [Row {i}] Using cached translation.", flush=True)
                    self.row_completed.emit(elem, 'cached')
                    self.progress_updated.emit(i + 1, total)
                    continue

                # Get original text to translate
                original_text = getattr(elem, 'original', '') or getattr(elem, 'raw', '')
                if not original_text.strip() or original_text.isspace():
                    # Empty or pure whitespace tags
                    print(f"DEBUG WORKER: [Row {i}] Skipping EMPTY row.", flush=True)
                    self.row_completed.emit(elem, 'done')
                    self.progress_updated.emit(i + 1, total)
                    continue

                # 2.5 Notify UI that this row started translating
                print(f"DEBUG WORKER: [Row {i}] Starting translation... (id={id(elem)})", flush=True)
                elem._temp_status = 'Translating...'
                self.row_completed.emit(elem, 'translating')
                
                # Emit row log
                self.log_message.emit(f"Row: {getattr(elem, 'row', i)}\nOriginal: {original_text}")

                # 3. Blocking HTTP API Call (safe here because we are in a QThread)
                print(f"DEBUG WORKER: [Row {i}] Calling API: {self.engine_name}", flush=True)
                try:
                    translated_text = translator.translate(original_text)
                    print(f"DEBUG WORKER: [Row {i}] API Success. Result len: {len(translated_text or '')}", flush=True)
                    
                    # Consume generator if the engine streams the response
                    from types import GeneratorType
                    if isinstance(translated_text, GeneratorType):
                        parts = []
                        for chunk in translated_text:
                            if self._is_canceled:
                                break
                            parts.append(chunk)
                        translated_text = "".join(parts)
                    
                    # Save it back to the element in memory so export can use it
                    elem.translation = translated_text
                    elem.engine_name = self.engine_name
                    elem.target_lang = self.target_lang
                    elem.error = None
                    
                    # Report Translation to log
                    self.log_message.emit(f"Translation: {translated_text}\n{'-' * 50}\n")
                    
                    items_translated += 1
                    chars_translated += len(original_text)
                    
                    # 4. Notify UI that this row is ready
                    print(f"DEBUG WORKER: [Row {i}] Emitting row_completed(elem, status=done)", flush=True)
                    self.row_completed.emit(elem, 'done')
                    self.progress_updated.emit(i + 1, total)

                except Exception as api_err:
                    print(f"DEBUG WORKER: [Row {i}] API FAILED: {api_err}", flush=True)
                    elem.error = str(api_err)
                    elem._temp_status = 'Error'
                    self.row_completed.emit(elem, 'error')
                    self.log_message.emit(f"⚠️ Row {i} FAILED: {api_err}\n{'-' * 50}\n")
                    # We DON'T raise here, so we continue to the next row!
                    continue

        except Exception as e:
            logging.exception("Translation worker failed")
            self.error_occurred.emit(str(e))
        finally:
            end_time = time.time()
            duration_mins = (end_time - start_time) / 60.0
            
            # Print Final Summary if anything was processed
            if hasattr(self, 'total_cost'):
                summary_parts = [
                    f"Time consuming: {duration_mins:.2f} minutes",
                    "Translation completed.",
                    "-" * 50,
                    "📑 TRANSLATION SUMMARY",
                    "-" * 50,
                    f"✅ Translated: {items_translated} items ({chars_translated} characters)",
                    f"⏱ Duration: {duration_mins:.2f} minutes",
                    f"💰 Estimated API cost: {getattr(self, 'cost_details', 'N/A')}",
                    f"🤖 Model used: {getattr(self, 'model_name', self.engine_name)}",
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
