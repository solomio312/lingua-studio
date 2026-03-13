# EPUB Normalizer Module
# Preprocesses problematic EPUB HTML structures for better paragraph extraction
# Addresses issues like: inline content, empty <p> tags, missing paragraph wrappers

import re
from lxml import etree


class EpubNormalizer:
    """
    Normalizes problematic EPUB HTML structures to improve paragraph extraction.
    
    Common issues addressed:
    1. Text content directly inside body/div without <p> wrappers
    2. Empty <p> tags used for spacing
    3. Text in 'tail' property after inline elements like <a>, <span>
    4. Text after </p> that should be in its own paragraph
    """
    
    # Minimum text length to consider for wrapping
    MIN_TEXT_LENGTH = 20
    
    # Block-level elements that should contain text in <p> tags
    CONTAINER_TAGS = {'body', 'div', 'section', 'article', 'main', 'aside'}
    
    # Inline elements whose tail text needs wrapping
    INLINE_TAGS = {'a', 'span', 'strong', 'b', 'em', 'i', 'u', 'small',
                   'mark', 'del', 'ins', 'sub', 'sup', 'code', 'br', 'img'}
    
    def __init__(self):
        self.stats = {
            'empty_p_removed': 0,
            'text_wrapped': 0,
            'tail_wrapped': 0,
            'files_processed': 0
        }
    
    def normalize_html(self, html_content: str) -> str:
        """
        Normalize HTML content for better paragraph extraction.
        """
        try:
            # Parse as HTML (more forgiving)
            parser = etree.HTMLParser(encoding='utf-8')
            tree = etree.fromstring(html_content.encode('utf-8'), parser)
            
            body = tree.find('.//body')
            if body is None:
                body = tree.find('.//{http://www.w3.org/1999/xhtml}body')
            
            if body is not None:
                # Apply normalizations in order
                self._remove_empty_paragraphs(body)
                self._wrap_paragraph_tails(body)
                self._wrap_inline_tails(body)
                self._wrap_loose_text(body)
            
            result = etree.tostring(tree, encoding='unicode', method='html')
            self.stats['files_processed'] += 1
            return result
            
        except Exception as e:
            print(f"[EpubNormalizer] Error: {e}")
            return html_content
    
    def _get_tag_name(self, element) -> str:
        """Get the local tag name without namespace."""
        tag = element.tag
        if isinstance(tag, str) and '}' in tag:
            return tag.split('}')[1].lower()
        return str(tag).lower() if tag else ''
    
    def _remove_empty_paragraphs(self, root):
        """Remove <p> elements that are empty or contain only whitespace."""
        to_remove = []
        
        for p in root.iter():
            tag_name = self._get_tag_name(p)
            if tag_name != 'p':
                continue
            
            text_content = ''.join(p.itertext()).strip()
            style = p.get('style', '')
            is_spacer = 'height:' in style and ('0pt' in style or '1em' in style)
            
            if not text_content or (len(text_content) <= 1 and is_spacer):
                to_remove.append(p)
        
        for p in to_remove:
            parent = p.getparent()
            if parent is not None:
                # Preserve important tail text
                if p.tail and len(p.tail.strip()) > 0:
                    prev = p.getprevious()
                    if prev is not None:
                        prev.tail = (prev.tail or '') + p.tail
                    else:
                        parent.text = (parent.text or '') + p.tail
                parent.remove(p)
                self.stats['empty_p_removed'] += 1
    
    def _wrap_paragraph_tails(self, root):
        """
        Wrap text that appears after </p> in a new <p>.
        This is a common issue in magazine-style EPUBs.
        """
        # We need to iterate carefully because we're modifying the tree
        for p in list(root.iter()):
            tag_name = self._get_tag_name(p)
            if tag_name != 'p':
                continue
            
            # Check if there's significant tail text after this </p>
            if p.tail and len(p.tail.strip()) >= self.MIN_TEXT_LENGTH:
                parent = p.getparent()
                if parent is None:
                    continue
                
                tail_text = p.tail
                p.tail = None  # Remove tail from original
                
                # Create new paragraph for the tail content
                new_p = etree.Element('p')
                new_p.set('class', 'normalized-tail')
                new_p.text = tail_text
                
                # Insert after current paragraph
                p_index = list(parent).index(p)
                parent.insert(p_index + 1, new_p)
                self.stats['tail_wrapped'] += 1
    
    def _wrap_inline_tails(self, root):
        """
        Wrap tail text after inline elements (<a>, <span>, etc.) in <p> tags.
        """
        for element in list(root.iter()):
            tag_name = self._get_tag_name(element)
            
            # Only process inline elements
            if tag_name not in self.INLINE_TAGS:
                continue
            
            # Check for significant tail text
            if not element.tail or len(element.tail.strip()) < self.MIN_TEXT_LENGTH:
                continue
            
            parent = element.getparent()
            if parent is None:
                continue
            
            parent_tag = self._get_tag_name(parent)
            
            # Only wrap if parent is a container, not already a <p>
            if parent_tag == 'p':
                continue
            
            if parent_tag not in self.CONTAINER_TAGS:
                continue
            
            tail_text = element.tail
            element.tail = None
            
            # Create new paragraph
            new_p = etree.Element('p')
            new_p.set('class', 'normalized-inline-tail')
            new_p.text = tail_text
            
            # Insert after the inline element
            el_index = list(parent).index(element)
            parent.insert(el_index + 1, new_p)
            self.stats['tail_wrapped'] += 1
    
    def _wrap_loose_text(self, root):
        """Wrap loose text directly in container elements."""
        for element in list(root.iter()):
            tag_name = self._get_tag_name(element)
            
            if tag_name not in self.CONTAINER_TAGS:
                continue
            
            # Wrap direct text content
            if element.text and len(element.text.strip()) >= self.MIN_TEXT_LENGTH:
                text = element.text
                element.text = None
                
                new_p = etree.Element('p')
                new_p.set('class', 'normalized')
                new_p.text = text
                element.insert(0, new_p)
                self.stats['text_wrapped'] += 1
    
    def get_stats(self) -> dict:
        return self.stats.copy()
    
    def reset_stats(self):
        self.stats = {
            'empty_p_removed': 0,
            'text_wrapped': 0,
            'tail_wrapped': 0,
            'files_processed': 0
        }


def normalize_epub_html(html_content: str) -> str:
    """Convenience function to normalize EPUB HTML content."""
    normalizer = EpubNormalizer()
    return normalizer.normalize_html(html_content)
