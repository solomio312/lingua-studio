"""
Translation cache using SQLite.

Migrated from Calibre plugin lib/cache.py.
Changes:
  - calibre.utils.config.config_dir → appdirs via core.config
  - Removed load_translations() (Calibre i18n)
  - _() calls replaced with plain strings
"""

import os
import re
import json
import shutil
import sqlite3
import os.path
from datetime import datetime
from glob import glob

from .utils import size_by_unit
from .config import get_config, CACHE_DIR


class Paragraph:
    def __init__(
            self, id, md5, raw, original, ignored=False, attributes=None,
            page=None, translation=None, engine_name=None, target_lang=None):
        self.id = id
        self.md5 = md5
        self.raw = raw
        self.original = original
        self.ignored = ignored
        self.attributes = attributes
        self.page = page
        self.translation = translation
        self.engine_name = engine_name
        self.target_lang = target_lang

        self.row = -1
        self.is_cache = False
        self.error = None
        self.aligned = True
        self.incomplete = False

    def get_attributes(self):
        if self.attributes:
            return json.loads(self.attributes)
        return {}

    def is_alignment(self, separator):
        pattern = re.compile(separator)
        count_original = len(pattern.split(self.original.strip()))
        count_translation = len(pattern.split(self.translation.strip()))
        return count_original == count_translation

    def alignment_details(self, separator):
        """Returns detailed alignment diagnostics.

        Returns:
            dict with keys:
                aligned (bool): True if segment counts match
                orig_count (int): number of segments in original
                trans_count (int): number of segments in translation
                orig_parts (list[str]): original segments
                trans_parts (list[str]): translation segments
                missing (list[int]): indices of empty translation segments
                suspicious (list[int]): indices where translation is < 30%
                    of original length (possibly omitted content)
        """
        pattern = re.compile(separator)
        orig_parts = pattern.split(self.original.strip())
        trans_parts = pattern.split(self.translation.strip())

        missing = []
        suspicious = []

        for i in range(min(len(orig_parts), len(trans_parts))):
            orig_len = len(orig_parts[i].strip())
            trans_len = len(trans_parts[i].strip())
            if trans_len == 0 and orig_len > 0:
                missing.append(i)
            elif orig_len > 20 and trans_len < orig_len * 0.3:
                suspicious.append(i)

        if len(trans_parts) < len(orig_parts):
            for i in range(len(trans_parts), len(orig_parts)):
                missing.append(i)

        return {
            'aligned': len(orig_parts) == len(trans_parts),
            'orig_count': len(orig_parts),
            'trans_count': len(trans_parts),
            'orig_parts': orig_parts,
            'trans_parts': trans_parts,
            'missing': missing,
            'suspicious': suspicious,
        }


def default_cache_path():
    """Default cache location using appdirs."""
    path = os.path.join(CACHE_DIR, 'translation_cache')
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path


def cache_path():
    config = get_config()
    path = config.get('cache_path')
    if path and os.path.exists(path):
        return path
    return default_cache_path()


class TranslationCache:
    fresh = True
    dir_path = cache_path()
    cache_path = os.path.join(dir_path, 'cache')
    temp_path = os.path.join(dir_path, 'temp')

    def __init__(self, identity, persistence=True):
        """:persistence: We use two types of cache, one is used temporarily for
        communication, and another one is used to cache translations, which
        avoids the need for retranslation.
        """
        self.identity = identity
        self.persistence = persistence
        self.file_path = self._path(identity)
        if os.path.exists(self.file_path) and self.size() > 50000:
            self.fresh = False
        self.cache_only = False
        self.connection = sqlite3.connect(
            self.file_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS cache('
            'id UNIQUE, md5 UNIQUE, raw, original, ignored, '
            'attributes DEFAULT NULL, page DEFAULT NULL,'
            'translation DEFAULT NULL, engine_name DEFAULT NULL, '
            'target_lang DEFAULT NULL)')
        self.cursor.execute(
            'CREATE TABLE IF NOT EXISTS info(key UNIQUE, value)')

    @classmethod
    def move(cls, dest):
        for dir_path in glob(os.path.join(cls.dir_path, '*')):
            os.path.exists(dir_path) and shutil.move(dir_path, dest)
        cls.dir_path = dest
        cls.cache_path = os.path.join(dest, 'cache')
        cls.temp_path = os.path.join(dest, 'temp')

    @classmethod
    def count(cls):
        total = 0
        for file_path in glob(os.path.join(cls.cache_path, '*.db')):
            total += os.path.getsize(file_path)
        return size_by_unit(total, 'MB')

    @classmethod
    def remove(cls, filename):
        file_path = os.path.join(cls.cache_path, filename)
        os.path.exists(file_path) and os.remove(file_path)

    @classmethod
    def clean(cls):
        for filename in os.listdir(cls.cache_path):
            cls.remove(filename)

    @classmethod
    def get_list(cls):
        names = []
        for file_path in glob(os.path.join(cls.cache_path, '*.db')):
            name = os.path.basename(file_path)
            cache = cls(os.path.splitext(name)[0])
            title = cache.get_info('title') or '[Unknown]'
            engine = cache.get_info('engine_name')
            lang = cache.get_info('target_lang')
            merge = int(cache.get_info('merge_length') or 0)
            size = size_by_unit(os.path.getsize(file_path), 'MB')
            time = datetime.fromtimestamp(os.path.getmtime(file_path)) \
                .strftime('%Y-%m-%d %H:%M:%S')
            names.append((title, engine, lang, merge, size, time, name))
            cache.close()
        return names

    def _path(self, name):
        if not os.path.exists(self.dir_path):
            os.mkdir(self.dir_path)
        cache_dir = self.cache_path
        if not self.is_persistence():
            cache_dir = self.temp_path
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)
        return os.path.join(cache_dir, '%s.db' % name)

    def size(self):
        return os.path.getsize(self.file_path)

    def is_fresh(self):
        return self.fresh

    def get_identity(self):
        return self.identity

    def is_persistence(self):
        return self.persistence

    def set_cache_only(self, cache_only):
        self.cache_only = cache_only

    def set_info(self, key, value):
        self.cursor.execute(
            'INSERT INTO info VALUES (?1, ?2) '
            'ON CONFLICT (KEY) DO UPDATE SET value=excluded.value',
            (key, value))
        self.connection.commit()

    def get_info(self, key):
        resource = self.cursor.execute(
            'SELECT value FROM info WHERE key=?', (key,))
        result = resource.fetchone()
        return result[0] if result else None

    def del_info(self, key):
        self.cursor.execute(
            'DELETE FROM info WHERE key=?', (key,))
        self.connection.commit()

    def save(self, original_group):
        existing_translations = {}
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                'SELECT original, translation, engine_name, target_lang '
                'FROM cache WHERE translation IS NOT NULL AND translation != ""')
            rows = cursor.fetchall()

            def strip_placeholders(text):
                text = re.sub(r'\[\[id_\d+\]\]', '', text)
                text = re.sub(r'{{id_\d+}}', '', text)
                text = re.sub(r'\[', '', text)
                text = re.sub(r'{{', '', text)
                return text.strip()

            for row in rows:
                orig, trans, eng, lang = row
                stripped = strip_placeholders(orig)
                if stripped:
                    existing_translations[stripped] = (trans, eng, lang)
        except Exception:
            pass

        for original_unit in original_group:
            original_text = original_unit[3]
            self.add(*original_unit)
            stripped_new = strip_placeholders(original_text)
            if stripped_new in existing_translations:
                trans, eng, lang = existing_translations[stripped_new]
                self.update(
                    original_unit[0], translation=trans,
                    engine_name=eng, target_lang=lang)

        self.connection.commit()

    def all(self, include_ignored=False):
        if include_ignored:
            resource = self.cursor.execute('SELECT * FROM cache')
        else:
            resource = self.cursor.execute(
                'SELECT * FROM cache WHERE NOT ignored')
        return resource.fetchall()

    def get(self, ids):
        placeholders = ', '.join(['?'] * len(ids))
        resource = self.cursor.execute(
            'SELECT * FROM cache WHERE id IN (%s) ' % placeholders,
            tuple(ids))
        return resource.fetchall()

    def first(self, **kwargs):
        if kwargs:
            data = ' AND '.join(['%s=?' % column for column in kwargs])
            resource = self.cursor.execute(
                'SELECT * FROM cache WHERE %s' % data,
                tuple(kwargs.values()))
        else:
            resource = self.cursor.execute('SELECT * FROM cache LIMIT 1')
        return resource.fetchone()

    def add(self, id, md5, raw, original, ignored=False, attributes=None,
            page=None):
        self.cursor.execute(
            'INSERT INTO cache VALUES ('
            '?1, ?2, ?3, ?4, ?5, ?6, ?7, NULL, NULL, NULL'
            ') ON CONFLICT DO NOTHING',
            (id, md5, raw, original, ignored, attributes, page))

    def update(self, ids, **kwargs):
        ids = ids if isinstance(ids, list) else [ids]
        data = ', '.join(['%s=?' % column for column in kwargs.keys()])
        placeholders = ', '.join(['?'] * len(ids))
        self.cursor.execute(
            'UPDATE cache SET %s WHERE id IN (%s)' % (data, placeholders),
            tuple(list(kwargs.values()) + ids))
        self.connection.commit()

    def ignore(self, ids):
        self.update(ids, ignored=True)

    def delete(self, ids):
        placeholders = ', '.join(['?'] * len(ids))
        self.cursor.execute(
            'DELETE FROM cache WHERE id IN (%s)' % placeholders, tuple(ids))
        self.connection.commit()

    def clear(self):
        """Clear all content from the cache table (used before fresh extraction)."""
        self.cursor.execute('DELETE FROM cache')
        self.connection.commit()

    def close(self):
        try:
            if hasattr(self, 'cursor') and self.cursor:
                self.cursor.close()
            if hasattr(self, 'connection') and self.connection:
                try:
                    self.connection.commit()
                except:
                    pass
                self.connection.close()
        except:
            pass

    def destroy(self):
        self.close()
        os.path.exists(self.file_path) and os.remove(self.file_path)

    def done(self):
        self.persistence or self.destroy()

    def paragraph(self, id=None):
        return Paragraph(*self.first(id=id))

    def get_paragraphs(self, ids):
        return [Paragraph(*item) for item in self.get(ids)]

    def all_paragraphs(self, cache_only=None, include_ignored=False):
        if cache_only is None:
            cache_only = self.cache_only

        paragraphs = []
        for item in self.all(include_ignored=include_ignored):
            paragraph = Paragraph(*item)
            if cache_only and not paragraph.translation:
                continue
            paragraphs.append(paragraph)
        return paragraphs

    def update_paragraph(self, paragraph):
        self.update(
            paragraph.id, translation=paragraph.translation,
            engine_name=paragraph.engine_name,
            target_lang=paragraph.target_lang)

    def delete_paragraphs(self, paragraphs):
        self.delete([paragraph.id for paragraph in paragraphs])

    def ignore_paragraphs(self, paragraphs):
        self.ignore([paragraph.id for paragraph in paragraphs])

    def replace_paragraphs(self, old_ids, new_paragraphs):
        """Delete old paragraphs and insert new ones (for re-chunking)."""
        self.delete(old_ids)
        for p in new_paragraphs:
            self.add(p.id, p.md5, p.raw, p.original,
                     p.ignored, p.attributes, p.page)
        self.connection.commit()


def get_cache(uid):
    return TranslationCache(uid, get_config().get('cache_enabled'))
