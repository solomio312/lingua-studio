import sys
import os

# Ensure correct path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingua.core.element import get_element_handler
from lingua.core.config import Configuration

RESULTS = []

def test(name, fn):
    try:
        fn()
        RESULTS.append((name, True, ''))
        print(f'  [PASS] {name}')
    except Exception as e:
        RESULTS.append((name, False, str(e)))
        print(f'  [FAIL] {name}: {e}')
        import traceback
        traceback.print_exc()

def test_per_file_default_limit():
    """Verify that Per-File uses 30000 when merge_enabled is False."""
    mock_prefs = {
        'merge_enabled': False,
        'chunking_method': 'per_file',
        'translate_engine': 'Gemini',
        'translation_position': 'below'
    }
    config = Configuration(mock_prefs)
    handler = get_element_handler('[[id_{}]]', '\n\n', 'ltr', config=config)
    
    assert handler.get_merge_length() == 30000, f"Expected 30000, got {handler.get_merge_length()}"

def test_chapter_aware_default_limit():
    """Verify that Chapter-Aware uses 15000 when merge_enabled is False."""
    mock_prefs = {
        'merge_enabled': False,
        'chunking_method': 'chapter_aware',
        'translate_engine': 'Gemini',
        'translation_position': 'below'
    }
    config = Configuration(mock_prefs)
    handler = get_element_handler('[[id_{}]]', '\n\n', 'ltr', config=config)
    
    assert handler.get_merge_length() == 15000, f"Expected 15000, got {handler.get_merge_length()}"

def test_merge_override_limit():
    """Verify that merge_length overrides specific limits when merge_enabled is True."""
    mock_prefs = {
        'merge_enabled': True,
        'merge_length': 13000,
        'chunking_method': 'per_file',
        'translate_engine': 'Gemini',
        'translation_position': 'below'
    }
    config = Configuration(mock_prefs)
    handler = get_element_handler('[[id_{}]]', '\n\n', 'ltr', config=config)
    
    assert handler.get_merge_length() == 13000, f"Expected 13000, got {handler.get_merge_length()}"

def test_standard_limit_with_merge_disabled():
    """Standard handler should have its default (0/unlimited) when merge is disabled."""
    mock_prefs = {
        'merge_enabled': False,
        'chunking_method': 'standard',
        'translate_engine': 'Gemini',
        'translation_position': 'below'
    }
    config = Configuration(mock_prefs)
    handler = get_element_handler('[[id_{}]]', '\n\n', 'ltr', config=config)
    
    # Standard handler doesn't set a default in its __init__, so it should be the parent default (0)
    assert handler.get_merge_length() == 0, f"Expected 0, got {handler.get_merge_length()}"

if __name__ == '__main__':
    print('=== Chunking Logic Isolation Tests ===\n')
    
    test('Per-File default limit (30k)', test_per_file_default_limit)
    test('Chapter-Aware default limit (15k)', test_chapter_aware_default_limit)
    test('Merge override (13k)', test_merge_override_limit)
    test('Standard limit disabled', test_standard_limit_with_merge_disabled)
    
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f'\n=== {passed}/{total} tests passed ===')
    sys.exit(0 if passed == total else 1)
