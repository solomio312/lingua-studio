"""Phase 0 Checkpoint 3 — End-to-end verification tests."""

import io
import os
import sys
import tempfile

# ── Test 1: Core imports ──
def test_core_imports():
    import lingua
    from lingua.core.config import get_config, JSONConfigFile
    from lingua.core.exception import TranslationFailed, TranslationCanceled
    from lingua.core.utils import request, uid, sep, trim
    from lingua.core.handler import Handler
    from lingua.core.cache import TranslationCache, Paragraph
    from lingua.core.element import (
        Element, PageElement, Extraction, ElementHandler,
        ElementHandlerMerge, get_element_handler)
    from lingua.core.translation import (
        Translation, Glossary, get_engine_class, get_translator,
        get_translation, estimate_cost, GenderAnalyzer)
    from lingua.core.conversion import (
        extract_epub_pages, convert_item, sanitize_file_name, EpubPage)
    print("[PASS] Test 1: All core imports OK")


# ── Test 2: All 19 engines ──
def test_engine_imports():
    from lingua.engines import builtin_engines
    engine_names = [e.name for e in builtin_engines]
    assert len(builtin_engines) == 19, f"Expected 19 engines, got {len(builtin_engines)}"
    print(f"[PASS] Test 2: All {len(builtin_engines)} engines import OK")
    for name in engine_names:
        print(f"   - {name}")


# ── Test 3: Config system ──
def test_config():
    from lingua.core.config import JSONConfigFile, defaults
    # Create temp config
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
        f.write('{}')
        tmp = f.name
    try:
        cfg = JSONConfigFile(tmp)
        cfg['test_key'] = 'test_value'
        assert cfg.get('test_key') == 'test_value'
        # Test defaults exist
        assert isinstance(defaults, dict)
        assert 'cache_enabled' in defaults
        print("[PASS] Test 3: Config system OK")
    finally:
        os.unlink(tmp)


# ── Test 4: Cache system ──
def test_cache():
    from lingua.core.cache import TranslationCache, Paragraph
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = TranslationCache('test_book', persistence=True)
        # Override paths for test
        cache.dir_path = tmpdir
        cache.cache_path = os.path.join(tmpdir, 'cache')
        cache.temp_path = os.path.join(tmpdir, 'temp')

        cache.set_info('title', 'Test Book')
        assert cache.get_info('title') == 'Test Book'
        
        # Test paragraph handling
        p = Paragraph(id=1, md5='abc123', raw='<p>Hello</p>', original='Hello')
        p.translation = 'Salut'
        p.engine_name = 'TestEngine'
        assert p.original == 'Hello'
        assert p.translation == 'Salut'
        
        cache.close()
        print("[PASS] Test 4: Cache system OK")


# ── Test 5: EPUB extraction (if available) ──
def test_epub_extraction():
    epub_candidates = [
        r'c:\Users\vrusu\Translate\two options ebook translator\Peace Be with You! - Pope Leo XIV.epub',
        r'c:\Users\vrusu\Translate\Test anatomy - John Marriott.epub',
    ]
    epub_path = None
    for path in epub_candidates:
        if os.path.exists(path):
            epub_path = path
            break
    
    if epub_path is None:
        print("[SKIP] Test 5: SKIPPED -- no EPUB file found")
        return
    
    from lingua.core.conversion import extract_epub_pages
    from lingua.core.element import get_page_elements

    pages, spine_hrefs, book = extract_epub_pages(epub_path)
    assert len(pages) > 0, "No pages extracted"
    assert len(spine_hrefs) > 0, "No spine items"

    # Verify pages have data
    pages_with_data = sum(1 for p in pages if p.data is not None)
    assert pages_with_data > 0, "No pages with parsed data"

    # Extract elements
    elements = list(get_page_elements(pages))
    assert len(elements) > 0, "No elements extracted"

    # Verify elements have text
    texts = [e.get_text() for e in elements[:5] if e.get_text()]
    assert len(texts) > 0, "No text in elements"

    print(f"[PASS] Test 5: EPUB extraction OK")
    print(f"   - File: {os.path.basename(epub_path)}")
    print(f"   - Pages: {len(pages)} ({pages_with_data} with data)")
    print(f"   - Spine: {len(spine_hrefs)} items")
    print(f"   - Elements: {len(elements)}")
    print(f"   - Sample: {texts[0][:80]}...")


# ── Test 6: Translation utilities ──
def test_translation_utils():
    from lingua.core.translation import estimate_cost, Glossary, GenderAnalyzer
    
    # Cost estimation
    cost, details, is_free = estimate_cost(10000, 'Google(Free)New')
    assert is_free, "Google Free should be free"
    assert cost == 0
    
    cost, details, is_free = estimate_cost(100000, 'Gemini', 'gemini-2.0-flash')
    assert not is_free
    assert cost > 0
    
    # Glossary
    g = Glossary(('{{{{id_{}}}}}', r'({{\s*)+id\s*_\s*{}\s*(\s*}})+'))
    assert g.glossary == []
    
    # Gender analyzer
    ga = GenderAnalyzer()
    # Need 2+ markers difference for dominance
    strong_masc = "El a spus el că bărbatul este fericit."
    masc, fem = ga.get_gender_score(strong_masc)
    assert masc > 0, f"Expected masculine markers, got {masc}"
    gender = ga.get_dominant_gender(strong_masc)
    assert gender == 'M', f"Expected M, got {gender} (masc={masc}, fem={fem})"
    
    print("[PASS] Test 6: Translation utilities OK")


# ── Test 7: Element handler ──
def test_element_handler():
    from lingua.core.element import ElementHandler, ElementHandlerMerge
    
    placeholder = ('{{{{id_{}}}}}', r'({{\s*)+id\s*_\s*{}\s*(\s*}})+')
    handler = ElementHandler(placeholder, '\n\n', 'below')
    assert handler.separator == '\n\n'
    assert handler.position == 'below'
    
    merge_handler = ElementHandlerMerge(placeholder, '\n\n', 'below')
    merge_handler.set_merge_length(5000)
    assert merge_handler.merge_length == 5000
    
    print("[PASS] Test 7: Element handler OK")


# ── Test 8: Sanitize filename ──
def test_sanitize():
    from lingua.core.conversion import sanitize_file_name
    assert sanitize_file_name('test<file>:name') == 'test_file__name'
    assert sanitize_file_name('normal.epub') == 'normal.epub'
    print("[PASS] Test 8: Sanitize filename OK")


# ── Run all ──
if __name__ == '__main__':
    # Force UTF-8 output on Windows
    import sys
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    print("=" * 60)
    print("  Lingua -- Phase 0 Checkpoint 3 Verification Tests")
    print("=" * 60)
    
    tests = [
        test_core_imports,
        test_engine_imports,
        test_config,
        test_cache,
        test_epub_extraction,
        test_translation_utils,
        test_element_handler,
        test_sanitize,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    sys.exit(1 if failed > 0 else 0)
