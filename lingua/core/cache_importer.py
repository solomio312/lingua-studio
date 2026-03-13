"""
Logic for importing translation caches from the legacy Calibre plugin.
Scans for SQLite databases in the Calibre configuration folder and 
migrates them to Lingua's internal storage.
"""

import os
import shutil
import sqlite3
import logging
from glob import glob
from lingua.core.config import CACHE_DIR
from lingua.core.i18n import _

def get_legacy_cache_dir():
    """Locate the legacy Calibre plugin cache directory."""
    appdata = os.environ.get('APPDATA')
    if not appdata:
        return None
    
    # Standard path for Calibre plugins (ebook_translator_cache)
    path = os.path.join(appdata, 'calibre', 'plugins', 'ebook_translator_cache', 'cache')
    if os.path.exists(path):
        return path
    return None

class CacheImporter:
    """Handles scanning and migrating database files."""
    
    @staticmethod
    def scan_legacy_caches():
        """Returns a list of tuples (filename, size_mb, title)."""
        legacy_dir = get_legacy_cache_dir()
        if not legacy_dir:
            return []
            
        found = []
        for db_file in glob(os.path.join(legacy_dir, "*.db")):
            size_mb = os.path.getsize(db_file) / (1024 * 1024)
            filename = os.path.basename(db_file)
            
            # Try to get book title from info table
            title = "[Unknown]"
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM info WHERE key='title'")
                row = cursor.fetchone()
                if row:
                    title = row[0]
                conn.close()
            except Exception:
                pass
                
            found.append({
                'filename': filename,
                'path': db_file,
                'size': f"{size_mb:.2f} MB",
                'title': title
            })
            
        return found

    @staticmethod
    def migrate_all(progress_callback=None):
        """Copies all legacy databases to Lingua's cache folder."""
        legacy_dir = get_legacy_cache_dir()
        if not legacy_dir:
            return 0
            
        target_dir = os.path.join(CACHE_DIR, 'translation_cache', 'cache')
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
        caches = CacheImporter.scan_legacy_caches()
        count = 0
        
        for i, cache in enumerate(caches):
            src = cache['path']
            dst = os.path.join(target_dir, cache['filename'])
            
            # Only copy if it doesn't exist or is different size
            if not os.path.exists(dst) or os.path.getsize(src) > os.path.getsize(dst):
                try:
                    shutil.copy2(src, dst)
                    count += 1
                except Exception as e:
                    logging.error(f"Failed to migrate {src}: {e}")
            
            if progress_callback:
                progress_callback(i + 1, len(caches))
                
        return count
