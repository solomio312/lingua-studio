"""
Configuration system for Lingua standalone app.

Migrated from Calibre plugin lib/config.py.
Changes:
  - calibre.utils.config.JSONConfig → json file in appdirs config dir
  - calibre.constants.config_dir → appdirs.user_config_dir
  - calibre.utils.config_base.plugin_dir → appdirs.user_data_dir
  - All engine references kept identical
"""

import os
import json
import os.path
import shutil

import appdirs

import lingua


# Application directories
APP_NAME = lingua.__app_name__
APP_AUTHOR = lingua.__author__
CONFIG_DIR = appdirs.user_config_dir(APP_NAME, APP_AUTHOR)
DATA_DIR = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
CACHE_DIR = appdirs.user_cache_dir(APP_NAME, APP_AUTHOR)


defaults = {
    'preferred_mode': None,
    'to_library': False,  # Standalone: always export to file
    'output_path': None,
    'translate_engine': None,
    'engine_preferences': {},
    'proxy_enabled': False,
    'proxy_setting': [],
    'cache_enabled': True,
    'cache_path': None,
    'log_translation': True,
    'show_notification': True,
    'translation_position': None,
    'column_gap': {
        '_type': 'percentage',
        'percentage': 10,
        'space_count': 6,
    },
    'original_color': None,
    'translation_color': None,
    'priority_rules': [],
    'rule_mode': 'normal',
    'filter_scope': 'text',
    'filter_rules': [],
    'ignore_rules': [],
    'reserve_rules': ['a[href^="#"]'],
    'custom_engines': {},
    'glossary_enabled': False,
    'glossary_path': None,
    'merge_enabled': False,
    'merge_length': 4000,
    'smart_html_merge': False,
    'chunking_method': 'standard',
    'translator_credit_enabled': False,
    'translator_credit': 'Traducere și adaptare realizată de ManuX',
    'ebook_metadata': {},
    'search_paths': [],
}


class JSONConfigFile:
    """Simple JSON config file that mimics Calibre's JSONConfig interface.

    Provides dict-like access plus refresh/commit for persistence.
    """

    def __init__(self, path, default=None):
        self._path = path
        self._defaults = default or {}
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(self._path):
            try:
                with open(self._path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._data = {}
        # Apply defaults for missing keys
        for k, v in self._defaults.items():
            self._data.setdefault(k, v)

    @property
    def defaults(self):
        return self._defaults

    @defaults.setter
    def defaults(self, value):
        self._defaults = value
        for k, v in value.items():
            self._data.setdefault(k, v)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __contains__(self, key):
        return key in self._data

    def __delitem__(self, key):
        del self._data[key]

    def update(self, *args, **kwargs):
        self._data.update(*args, **kwargs)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def refresh(self):
        """Reload from disk."""
        self._load()

    def commit(self):
        """Write to disk."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)


class Configuration:
    def __init__(self, config=None):
        if config is None:
            config = {}
        self.preferences = config

    def get(self, key, default=None):
        """Get config value with dot flavor. e.g. get('a.b.c')"""
        if key is None:
            return default
        temp = self.preferences
        for k in key.split('.'):
            # Support both dict and dict-like objects (JSONConfigFile)
            if hasattr(temp, '__contains__') and k in temp:
                temp = temp[k] if hasattr(temp, '__getitem__') else temp.get(k)
                continue
            # Fall back to global defaults
            temp = defaults.get(k)
        return default if temp is None else temp

    def set(self, key, value):
        """Set config value with dot flavor. e.g. set('a.b.c', '1')"""
        temp = self.preferences
        keys = key.split('.')
        while len(keys) > 0:
            k = keys.pop(0)
            if len(keys) > 0:
                if k in temp and isinstance(temp.get(k), dict):
                    temp = temp[k]
                    continue
                temp[k] = {}
                temp = temp.get(k)
                continue
        temp[k] = value

    def update(self, *args, **kwargs):
        self.preferences.update(*args, **kwargs)

    def delete(self, key):
        if key in self.preferences:
            del self.preferences[key]
            return True
        return False

    def refresh(self):
        if hasattr(self.preferences, 'refresh'):
            self.preferences.refresh()

    def commit(self):
        if hasattr(self.preferences, 'commit'):
            self.preferences.commit()

    def save(self, *args, **kwargs):
        self.update(*args, **kwargs)
        self.commit()


def get_config():
    """Create and return a Configuration backed by a JSON file."""
    config_path = os.path.join(CONFIG_DIR, 'config.json')
    preferences = JSONConfigFile(config_path, default=defaults)
    return Configuration(preferences)
