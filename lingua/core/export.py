"""
Zip-based EPUB exporter for Lingua.
By directly manipulating the EPUB archive as a ZIP file, we preserve all original
CSS, font configurations, and structural metadata that ebooklib often breaks.
"""

import os
import zipfile
import shutil
import logging
import subprocess
from lxml import etree
import tempfile
import re

from lingua.core.element import get_page_elements, get_element_handler
from lingua.core.config import get_config
from lingua.core.cache import get_cache
from lingua.core.utils import uid
from lingua.core.translation import get_engine_class, get_translator

log = logging.getLogger('lingua.export')

class ZipEpubBuilder:
    def __init__(self, original_epub_path, output_epub_path, cache=None):
        self.original_epub_path = original_epub_path
        self.output_epub_path = output_epub_path
        self.cache = cache
        self.config = get_config()

        self.source_lang = self.config.get('source_lang', 'Auto')
        self.target_lang = self.config.get('target_lang', 'Romanian')
        self.chunking_method = self.config.get('chunking_method', 'standard')
        
    def _get_element_handler(self):
        engine_name = self.config.get('translate_engine', 'Google(Free)New')
        engine_class = get_engine_class(engine_name)
        translator = get_translator(engine_class)
        
        handler = get_element_handler(
            translator.placeholder, translator.separator, 'ltr', self.chunking_method)
        handler.set_translation_lang(
            translator.get_iso639_target_code(self.target_lang))
        return handler

    def build(self, progress_callback=None):
        """Build the translated EPUB."""
        if not self.cache:
            log.error("No cache provided to ZipEpubBuilder")
            raise ValueError("Cache is required for export")

        if progress_callback:
            progress_callback(0, "Pregătire fișier export...")

        shutil.copy2(self.original_epub_path, self.output_epub_path)
        
        from lingua.core.conversion import extract_epub_pages
        pages, spine_hrefs, _ = extract_epub_pages(self.original_epub_path)
        spine_order = spine_hrefs if self.config.get('use_spine_order', False) else None
        
        elements = list(get_page_elements(pages, spine_order))
        handler = self._get_element_handler()
        handler.prepare_original(elements)
        
        paragraphs = self.cache.all_paragraphs(include_ignored=True)
        handler.add_translations(paragraphs)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract everything first
            with zipfile.ZipFile(self.original_epub_path, 'r') as zin:
                zin.extractall(temp_dir)
            
            # Write modified pages back to the temp directory
            for page in pages:
                if page.data is not None:
                    # page.href is the path relative to the root inside the EPUB
                    # which is usually inside an OEBPS folder, ebooklib uses get_name()
                    file_path = os.path.join(temp_dir, page.href)
                    
                    # Ensure directory exists (though extractall should have created it)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    
                    try:
                        content = etree.tostring(
                            page.data, encoding='utf-8', method='xml', xml_declaration=True)
                        with open(file_path, 'wb') as f:
                            f.write(content)
                    except Exception as e:
                        log.error(f'Failed to rewrite modified page {page.href}: {e}')

            if progress_callback:
                progress_callback(90, "Împachetare rețetă originală EPUB...")

            # Re-zip keeping the standard epub mimetype requirements
            # 1. mimetype must be the first file, and uncompressed
            with zipfile.ZipFile(self.output_epub_path, 'w') as zout:
                mimetype_path = os.path.join(temp_dir, 'mimetype')
                if os.path.exists(mimetype_path):
                    zout.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
                
                # 2. Add the rest
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file == 'mimetype' and root == temp_dir:
                            continue
                        
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        # Make sure slashes are correct for EPUB spec
                        arcname = arcname.replace('\\', '/')
                        zout.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)

        if progress_callback:
            progress_callback(100, "Export Finalizat!")
        
        return self.output_epub_path

class TextBuilder:
    def __init__(self, cache, output_path):
        self.cache = cache
        self.output_path = output_path

    def build(self, progress_callback=None):
        if progress_callback:
            progress_callback(10, "Extreagere traduceri din cache...")
            
        paragraphs = self.cache.all_paragraphs(include_ignored=False)
        
        content = []
        for i, p in enumerate(paragraphs):
            if p.translation:
                # Strip placeholders like [[id_00001]] or {{id_00001}}
                try:
                    clean_text = re.sub(r'\[\[id_\d+\]\]', '', p.translation)
                    clean_text = re.sub(r'{{id_\d+}}', '', clean_text)
                    content.append(clean_text)
                except Exception as e:
                    print(f"DEBUG EXPORT: Regex error on paragraph {i}: {e}")
            
            if progress_callback and i % 10 == 0:
                pct = 10 + int((i / total) * 80)
                progress_callback(pct, f"Procesare segment {i}/{total}...")
        
        print(f"DEBUG EXPORT: Writing {len(content)} translated segments to {self.output_path}")
        if progress_callback:
            progress_callback(95, "Salvare fișier text...")
            
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(content))

        print(f"DEBUG EXPORT: TextBuilder.build finished successfully.")
        if progress_callback:
            progress_callback(100, "Export TXT Finalizat!")
        return self.output_path

class SrtBuilder:
    def __init__(self, cache, output_path):
        self.cache = cache
        self.output_path = output_path

    def build(self, progress_callback=None):
        if progress_callback:
            progress_callback(30, "Exporting SRT...")
            
        paragraphs = self.cache.all_paragraphs(include_ignored=False)
        total_rows = len(paragraphs)
        
        entries = []
        for i, p in enumerate(paragraphs):
            if p.translation:
                # Strip placeholders first
                try:
                    clean_trans = re.sub(r'\[\[id_\d+\]\]', '', p.translation)
                    clean_trans = re.sub(r'{{id_\d+}}', '', clean_trans)
                    
                    if p.raw and p.original:
                        block = p.raw.replace(p.original, clean_trans)
                        entries.append(block)
                    else:
                        entries.append(clean_trans) # Fallback
                except Exception as e:
                    print(f"DEBUG EXPORT: Regex error on SRT segment {i}: {e}")
            else:
                entries.append(p.raw or "")
            
            if progress_callback and i % 5 == 0:
                pct = 10 + int((i / total) * 80)
                progress_callback(pct, f"Procesare subtitrare {i}/{total}...")

        print(f"DEBUG EXPORT: Writing {len(entries)} SRT blocks to {self.output_path}")
        if progress_callback:
            progress_callback(95, "Salvare fișier SRT...")
            
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write('\n\n'.join(entries))

        print(f"DEBUG EXPORT: SrtBuilder.build finished successfully.")
        if progress_callback:
            progress_callback(100, "Export SRT Finalizat!")
        return self.output_path

class CalibreBuilder:
    """Uses Calibre's ebook-convert CLI to convert a translated EPUB to various formats."""
    
    CALIBRE_PATH = r"C:\Program Files\Calibre2\ebook-convert.exe"

    def __init__(self, original_epub_path, output_path, cache, format):
        self.original_epub_path = original_epub_path
        self.output_path = output_path
        self.cache = cache
        self.format = format.lower()

    def build(self, progress_callback=None):
        if not os.path.exists(self.CALIBRE_PATH):
            raise FileNotFoundError(f"Calibre was not found at {self.CALIBRE_PATH}. Please install Calibre to use {self.format.upper()} export.")

        # 1. First, build a translated EPUB as source for Calibre
        if progress_callback:
            progress_callback(10, f"Pregătire document pentru conversie {self.format.upper()}...")
            
        temp_epub = os.path.join(tempfile.gettempdir(), f"lingua_temp_{uid(self.original_epub_path)}.epub")
        
        try:
            epub_builder = ZipEpubBuilder(self.original_epub_path, temp_epub, self.cache)
            epub_builder.build(progress_callback=lambda pct, msg: progress_callback(int(pct * 0.5), msg) if progress_callback else None)
            
            # 2. Convert using CLI
            if progress_callback:
                progress_callback(60, f"Conversie Calibre către {self.format.upper()} (vă rugăm așteptați)...")
            
            cmd = [self.CALIBRE_PATH, temp_epub, self.output_path]
            
            if self.format == 'pdf':
                # Simplify for debugging: remove templates
                cmd.extend(['--paper-size', 'a4', '--pdf-default-font-size', '12'])

            print(f"DEBUG EXPORT: Launching Calibre (isolated)...")
            import sys; sys.stdout.flush()
            
            # Use a log file instead of memory capture to prevent buffer-related crashes
            log_path = os.path.join(tempfile.gettempdir(), f"calibre_log_{uid(self.output_path)}.txt")
            
            with open(log_path, 'w', encoding='utf-8', errors='replace') as log_file:
                print(f"DEBUG EXPORT: Command: {' '.join(cmd)}")
                sys.stdout.flush()
                
                # Use shell=True and direct redirection to avoid memory buffering in Python
                process = subprocess.Popen(
                    cmd, 
                    stdout=log_file, 
                    stderr=subprocess.STDOUT,
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                
                print(f"DEBUG EXPORT: Calibre process started (PID: {process.pid}). Waiting...")
                sys.stdout.flush()
                
                return_code = process.wait()
            
            if return_code != 0:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    err_msg = f.read()
                print(f"DEBUG EXPORT: Calibre FAILED with code {return_code}")
                print(f"DEBUG EXPORT: Log content: {err_msg[:500]}...")
                sys.stdout.flush()
                raise RuntimeError(f"Calibre conversion failed (code {return_code}). Check logs.")
                
            print(f"DEBUG EXPORT: Calibre conversion finished successfully.")
            import sys; sys.stdout.flush()
            
            try: os.remove(log_path)
            except: pass
            
        finally:
            if os.path.exists(temp_epub):
                try: os.remove(temp_epub)
                except: pass

        if progress_callback:
            progress_callback(100, f"Export {self.format.upper()} Finalizat!")
        return self.output_path
