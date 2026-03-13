import sys
import os

# Ensure correct path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingua.core.element import get_element_handler, Element
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

class MockElement:
    def __init__(self, content, page_id='p1'):
        self.content = content
        self.page_id = page_id
        self.ignored = False
    def get_content(self): return self.content
    def get_raw(self): return f"<p>{self.content}</p>"
    def get_attributes(self): return {}
    def set_placeholder(self, *args): pass
    def set_position(self, *args): pass
    def set_target_direction(self, *args): pass
    def set_translation_lang(self, *args): pass
    def set_original_color(self, *args): pass
    def set_translation_color(self, *args): pass
    def set_column_gap(self, *args): pass
    def set_remove_pattern(self, *args): pass
    def set_reserve_pattern(self, *args): pass
    def set_registry(self, *args): pass
    def set_id_start(self, *args): pass

def test_strict_30k_split():
    """Verify that a 32k element is strictly split into chunks <= 30k."""
    limit = 30000
    # Create a 32,000 char string
    huge_content = "A" * 32000
    
    mock_prefs = {
        'merge_enabled': False,
        'chunking_method': 'per_file',
        'translate_engine': 'Gemini'
    }
    config = Configuration(mock_prefs)
    handler = get_element_handler('[[id_{}]]', '\n\n', 'ltr', config=config)
    
    # Manually trigger prepare_original with one huge element
    elements = [MockElement(huge_content)]
    originals = handler.prepare_original(elements)
    
    # Should be split into at least 2 chunks
    print(f"    Chunks produced: {len(originals)}")
    for i, (_, _, _, content, *rest) in enumerate(originals):
        print(f"    Chunk {i} size: {len(content)}")
        assert len(content) <= limit + len('\n\n'), f"Chunk {i} exceeds strict limit: {len(content)}"

if __name__ == '__main__':
    print('=== Strict Chunking Verification ===\n')
    test('Strict 30k Split', test_strict_30k_split)
    
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f'\n=== {passed}/{total} tests passed ===')
    sys.exit(0 if passed == total else 1)
