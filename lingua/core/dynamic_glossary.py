# Dynamic Glossary Module
# Tracks recurring terms during translation for consistency and optional export

import re
import json
from collections import defaultdict


class DynamicGlossary:
    """Tracks recurring terms in memory during translation session.
    
    Detects n-grams (1-4 words) from source text and maps them to their
    translations. Suggests high-frequency terms for export to master glossary.
    """
    
    # Common words to exclude from term detection (English)
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
        'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
        'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
        'we', 'they', 'my', 'your', 'his', 'her', 'our', 'their', 'what',
        'which', 'who', 'whom', 'when', 'where', 'why', 'how', 'all', 'each',
        'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
        'if', 'then', 'because', 'while', 'although', 'though', 'after',
        'before', 'since', 'until', 'unless', 'about', 'into', 'through',
        'during', 'above', 'below', 'between', 'under', 'again', 'further',
        'once', 'here', 'there', 'any', 'also', 'even', 'still', 'yet'
    }
    
    def __init__(self):
        """Initialize empty dynamic glossary."""
        # {source_term: {translation: count, ...}}
        self.detected_terms = defaultdict(lambda: defaultdict(int))
        # [(source, target), ...] - terms confirmed for export
        self.confirmed_terms = []
        # Track total occurrences per source term
        self.term_counts = defaultdict(int)
    
    def _tokenize(self, text):
        """Split text into lowercase tokens, removing punctuation."""
        # Remove punctuation except apostrophes within words
        text = re.sub(r"[^\w\s'-]", ' ', text.lower())
        # Split on whitespace
        tokens = text.split()
        return [t.strip("'-") for t in tokens if t.strip("'-")]
    
    def _extract_ngrams(self, tokens, n_min=1, n_max=4):
        """Extract n-grams from token list.
        
        Returns list of (ngram_string, start_idx, end_idx) tuples.
        """
        ngrams = []
        for n in range(n_min, min(n_max + 1, len(tokens) + 1)):
            for i in range(len(tokens) - n + 1):
                ngram_tokens = tokens[i:i + n]
                # Skip if starts or ends with stop word (for n > 1)
                if n > 1:
                    if ngram_tokens[0] in self.STOP_WORDS:
                        continue
                    if ngram_tokens[-1] in self.STOP_WORDS:
                        continue
                # Skip single stop words
                if n == 1 and ngram_tokens[0] in self.STOP_WORDS:
                    continue
                
                ngram_str = ' '.join(ngram_tokens)
                # Skip very short terms
                if len(ngram_str) < 3:
                    continue
                    
                ngrams.append((ngram_str, i, i + n))
        
        return ngrams
    
    def _simple_align(self, source_tokens, target_tokens, source_ngram, start_idx, end_idx):
        """Simple positional alignment for translation mapping.
        
        Maps source n-gram position proportionally to target text.
        Returns the estimated translation span.
        """
        if not target_tokens:
            return ""
        
        # Calculate proportional position
        source_len = len(source_tokens)
        target_len = len(target_tokens)
        
        if source_len == 0:
            return ""
        
        # Map positions proportionally
        ratio = target_len / source_len
        target_start = int(start_idx * ratio)
        target_end = int(end_idx * ratio)
        
        # Ensure at least one token
        if target_end <= target_start:
            target_end = target_start + 1
        
        # Clamp to valid range
        target_start = max(0, min(target_start, target_len - 1))
        target_end = max(target_start + 1, min(target_end, target_len))
        
        return ' '.join(target_tokens[target_start:target_end])
    
    def track_translation(self, original: str, translation: str):
        """Extract n-grams from source and track their translations.
        
        Args:
            original: Source text (before translation)
            translation: Translated text
        """
        if not original or not translation:
            return
        
        source_tokens = self._tokenize(original)
        target_tokens = self._tokenize(translation)
        
        if not source_tokens or not target_tokens:
            return
        
        # Extract n-grams from source
        ngrams = self._extract_ngrams(source_tokens, n_min=2, n_max=4)
        
        for ngram_str, start_idx, end_idx in ngrams:
            # Get aligned translation
            aligned_translation = self._simple_align(
                source_tokens, target_tokens, ngram_str, start_idx, end_idx
            )
            
            if aligned_translation and len(aligned_translation) >= 3:
                self.detected_terms[ngram_str][aligned_translation] += 1
                self.term_counts[ngram_str] += 1
    
    def get_inconsistencies(self) -> list:
        """Find terms with multiple different translations.
        
        Returns:
            List of dicts: [{'source': str, 'translations': {translation: count}}]
        """
        inconsistencies = []
        
        for source, translations in self.detected_terms.items():
            if len(translations) > 1:
                # Sort by count descending
                sorted_trans = sorted(
                    translations.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )
                inconsistencies.append({
                    'source': source,
                    'translations': dict(sorted_trans),
                    'total_occurrences': self.term_counts[source]
                })
        
        # Sort by total occurrences descending
        inconsistencies.sort(key=lambda x: x['total_occurrences'], reverse=True)
        return inconsistencies
    
    def suggest_terms(self, min_occurrences: int = 3) -> list:
        """Get high-frequency terms suitable for export.
        
        Args:
            min_occurrences: Minimum times a term must appear
            
        Returns:
            List of dicts: [{'source': str, 'translation': str, 'count': int}]
        """
        suggestions = []
        
        for source, translations in self.detected_terms.items():
            total_count = self.term_counts[source]
            
            if total_count >= min_occurrences:
                # Get most common translation
                best_translation = max(translations.items(), key=lambda x: x[1])
                suggestions.append({
                    'source': source,
                    'translation': best_translation[0],
                    'count': total_count,
                    'confidence': best_translation[1] / total_count  # How consistent
                })
        
        # Sort by count descending, then by confidence
        suggestions.sort(key=lambda x: (x['count'], x['confidence']), reverse=True)
        return suggestions
    
    def confirm_term(self, source: str, target: str):
        """Mark a term-translation pair for export.
        
        Args:
            source: Source term
            target: Confirmed translation
        """
        pair = (source, target)
        if pair not in self.confirmed_terms:
            self.confirmed_terms.append(pair)
    
    def confirm_terms(self, terms: list):
        """Mark multiple terms for export.
        
        Args:
            terms: List of (source, target) tuples
        """
        for source, target in terms:
            self.confirm_term(source, target)
    
    def export_to_master(self, master_path: str, deduplicate: bool = True) -> dict:
        """Append confirmed terms to master glossary JSON.
        
        Args:
            master_path: Path to glossary_master_ro.json
            deduplicate: Skip terms already in master
            
        Returns:
            Dict with stats: {'added': int, 'skipped': int, 'errors': list}
        """
        result = {'added': 0, 'skipped': 0, 'errors': []}
        
        if not self.confirmed_terms:
            return result
        
        try:
            # Load existing master glossary
            try:
                with open(master_path, 'r', encoding='utf-8') as f:
                    master = json.load(f)
            except FileNotFoundError:
                master = {'metadata': {'name': 'Master Romanian Glossary'}, 'english': {}}
            except json.JSONDecodeError as e:
                result['errors'].append(f"Invalid JSON in master: {e}")
                return result
            
            # Ensure structure exists
            if 'english' not in master:
                master['english'] = {}
            if 'dynamic' not in master['english']:
                master['english']['dynamic'] = {}
            
            # Get existing terms for deduplication
            existing_terms = set()
            if deduplicate:
                for category in master.get('english', {}).values():
                    if isinstance(category, dict):
                        existing_terms.update(k.lower() for k in category.keys())
            
            # Add confirmed terms
            for source, target in self.confirmed_terms:
                source_lower = source.lower()
                if deduplicate and source_lower in existing_terms:
                    result['skipped'] += 1
                    continue
                
                master['english']['dynamic'][source] = target
                existing_terms.add(source_lower)
                result['added'] += 1
            
            # Save updated master
            with open(master_path, 'w', encoding='utf-8') as f:
                json.dump(master, f, ensure_ascii=False, indent=4)
                
        except Exception as e:
            result['errors'].append(str(e))
        
        return result
    
    def clear(self):
        """Reset glossary for new session."""
        self.detected_terms.clear()
        self.confirmed_terms.clear()
        self.term_counts.clear()
    
    def get_stats(self) -> dict:
        """Get current tracking statistics.
        
        Returns:
            Dict with stats about detected terms
        """
        total_unique = len(self.detected_terms)
        high_freq = len([t for t, c in self.term_counts.items() if c >= 3])
        inconsistent = len(self.get_inconsistencies())
        
        return {
            'total_unique_terms': total_unique,
            'high_frequency_terms': high_freq,
            'inconsistent_terms': inconsistent,
            'confirmed_for_export': len(self.confirmed_terms)
        }
