"""Phase 1 integration tests — settings panel, config persistence, engine list, project cards."""

import sys
import os

# Ensure correct path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

RESULTS = []

def test(name, fn):
    try:
        fn()
        RESULTS.append((name, True, ''))
        print(f'  [PASS] {name}')
    except Exception as e:
        RESULTS.append((name, False, str(e)))
        print(f'  [FAIL] {name}: {e}')


def test_config_roundtrip():
    from lingua.core.config import get_config
    c = get_config()
    c.set('translate_engine', 'Google(Free)')
    c.set('cache_enabled', True)
    c.set('merge_length', 2000)
    c.commit()

    c2 = get_config()
    assert c2.get('translate_engine') == 'Google(Free)', \
        f"Expected 'Google(Free)', got {c2.get('translate_engine')}"
    assert c2.get('cache_enabled') == True
    assert c2.get('merge_length') == 2000


def test_engine_registry():
    from lingua.engines import builtin_engines
    names = [e.name for e in builtin_engines]
    assert len(names) >= 19, f'Expected >=19 engines, got {len(names)}'
    for req in ['Google(Free)', 'Gemini', 'ChatGPT', 'DeepL']:
        assert req in names, f'Missing engine: {req}'


def test_settings_panel_import():
    from lingua.ui.settings_panel import SettingsPanel
    assert hasattr(SettingsPanel, '_build_general')
    assert hasattr(SettingsPanel, '_build_engine')
    assert hasattr(SettingsPanel, '_build_content')
    assert hasattr(SettingsPanel, '_build_styles')
    assert hasattr(SettingsPanel, '_save_all')
    assert hasattr(SettingsPanel, '_test_engine')


def test_project_card_import():
    from lingua.ui.widgets.project_card import ProjectCard
    assert hasattr(ProjectCard, 'clicked')


def test_main_window_import():
    from lingua.ui.main_window import MainWindow
    assert hasattr(MainWindow, '_build_dashboard')
    assert hasattr(MainWindow, '_add_epub_project')
    assert hasattr(MainWindow, 'dragEnterEvent')
    assert hasattr(MainWindow, 'dropEvent')


def test_config_engine_preferences():
    from lingua.core.config import get_config
    c = get_config()
    prefs = {'Gemini': {'api_keys': ['key1', 'key2'], 'model': 'gemini-2.0-flash'}}
    c.set('engine_preferences', prefs)
    c.commit()

    c2 = get_config()
    loaded = c2.get('engine_preferences')
    assert loaded is not None, 'engine_preferences is None'
    gem = loaded.get('Gemini', {})
    assert gem.get('api_keys') == ['key1', 'key2'], f"Keys: {gem.get('api_keys')}"
    assert gem.get('model') == 'gemini-2.0-flash'


def test_recent_projects():
    from lingua.core.config import get_config
    c = get_config()
    projects = [{'path': 'test.epub', 'title': 'Test', 'author': 'A', 'progress': 0}]
    c.set('recent_projects', projects)
    c.commit()

    c2 = get_config()
    loaded = c2.get('recent_projects')
    assert loaded is not None
    assert len(loaded) >= 1
    assert loaded[0]['title'] == 'Test'


if __name__ == '__main__':
    # Use UTF-8 output
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    print('=== Phase 1 Integration Tests ===\n')

    test('Config round-trip', test_config_roundtrip)
    test('Engine registry (19+)', test_engine_registry)
    test('SettingsPanel import', test_settings_panel_import)
    test('ProjectCard import', test_project_card_import)
    test('MainWindow import', test_main_window_import)
    test('Engine preferences persistence', test_config_engine_preferences)
    test('Recent projects persistence', test_recent_projects)

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f'\n=== {passed}/{total} tests passed ===')
    sys.exit(0 if passed == total else 1)
