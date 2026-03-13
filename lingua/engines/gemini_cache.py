"""Gemini Context Caching Manager — Experimental Module

Manages the lifecycle of Gemini API context caches via REST API.
Caches the book text + system instruction on Google's servers so that
each translation chunk references the cached tokens instead of re-sending
the entire prompt, reducing input token costs by ~75%.

REST API reference: https://ai.google.dev/api/caching
"""

import os
import json
import datetime

from ..core.utils import request


# Minimum token count required by Gemini for context caching
MIN_CACHE_TOKENS = 32768
# Approximate characters per token (conservative)
CHARS_PER_TOKEN = 4

CACHE_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/cachedContents'
GENERATE_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models'
METADATA_FILENAME = 'gemini_cache_metadata.json'

# Pricing per 1M tokens (USD) — updated Feb 2026
# source: https://ai.google.dev/pricing
# { model_prefix: (input, cached_input, storage/hr, output, deprecated) }
CACHE_PRICING = {
    'gemini-2.5-flash-lite': (0.10, 0.025, 1.00, 0.40, False),
    'gemini-2.5-flash': (0.15, 0.0375, 1.00, 0.60, False),
    'gemini-2.5-pro':   (1.25, 0.3125, 4.50, 10.00, False),
    'gemini-2.0-flash': (0.10, 0.025,  1.00, 0.40, True),   # EOL: 2026-03-31
    'gemini-1.5-flash': (0.075, 0.01875, 1.00, 0.30, False),
    'gemini-1.5-pro':   (1.25, 0.3125, 4.50, 5.00, False),
}


class GeminiCacheManager:
    """Manages Gemini API context caches via raw REST API calls."""

    def __init__(self, api_key, proxy_uri=None):
        self.api_key = api_key
        self.proxy_uri = proxy_uri

    def _headers(self):
        return {'Content-Type': 'application/json'}

    def _url(self, path=''):
        base = CACHE_ENDPOINT
        if path:
            base = f'{base}/{path}'
        return f'{base}?key={self.api_key}'

    def count_tokens(self, text, model, system_instruction=''):
        """Count tokens for text using the Gemini countTokens API.

        This is a FREE API call.
        Retries without system_instruction if the first call fails with 400.
        Splits text into chunks if > 500k chars to avoid payload limits.

        Args:
           text: The text to count tokens for
           model: Model name
           system_instruction: Optional system instruction text

        Returns:
           int: Total token count
        """
        # Chunking for large texts to avoid HTTP 400 / Payload Too Large
        CHUNK_SIZE = 500_000
        if len(text) > CHUNK_SIZE:
            total_tokens = 0
            # Helper to generate chunks
            chunks = [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]
            
            # Count system instruction once (add to first chunk or separately)
            sys_tokens = 0
            if system_instruction:
                try:
                    sys_tokens = self._count_tokens_raw('', model, system_instruction)
                except Exception:
                     # Ignore system instruction error if standalone fails, 
                     # or try to count it with the first chunk (riskier if 400 loop).
                     # Simple approach: estimate or skip. 
                     # Better: Try to count it alone. If fails 400, assume 0 or unsupported.
                     pass

            for i, chunk in enumerate(chunks):
                # We don't send system_instruction per chunk to avoid double counting
                # and to keep requests simple.
                try:
                    total_tokens += self._count_tokens_raw(chunk, model, None)
                except Exception as e:
                    # Fallback or error
                    raise Exception(f'Token counting failed on chunk {i+1}/{len(chunks)}: {str(e)}')
            
            return total_tokens + sys_tokens

        # Normal flow for small texts
        try:
            return self._count_tokens_raw(text, model, system_instruction)
        except Exception as e:
            if system_instruction and '400' in str(e):
                try:
                    return self._count_tokens_raw(text, model, None)
                except Exception:
                    raise e
            raise e

    def _count_tokens_raw(self, text, model, system_instruction=None):
        body = {
            'contents': [{
                'parts': [{'text': text}],
                'role': 'user'
            }]
        }
        if system_instruction:
            # Try top-level structure first (v1beta)
            body['systemInstruction'] = {
                'parts': [{'text': system_instruction}]
            }

        url = (f'{GENERATE_ENDPOINT}/{model}:countTokens'
               f'?key={self.api_key}')

        response = request(
            url=url,
            data=json.dumps(body),
            headers=self._headers(),
            method='POST',
            timeout=60,
            proxy_uri=self.proxy_uri
        )

        result = json.loads(response)
        if 'error' in result:
            msg = result["error"].get("message", str(result["error"]))
            raise Exception(f'Token counting failed: {msg}')

        return result.get('totalTokens', 0)

    def create_cache(self, book_text, system_instruction, model,
                     display_name='BookTranslation', ttl_hours=24):
        """Create a new context cache on Google's servers.

        Args:
            book_text: Full text of the book to cache
            system_instruction: The system prompt/instruction to cache
            model: Versioned model name (e.g., 'gemini-2.5-flash-001')
            display_name: Human-readable name for the cache
            ttl_hours: How long the cache persists (hours)

        Returns:
            dict with cache metadata (name, model, usageMetadata, etc.)

        Raises:
            Exception if content is too small or API call fails
        """
        # Validate minimum size
        estimated_tokens = len(book_text) / CHARS_PER_TOKEN
        if estimated_tokens < MIN_CACHE_TOKENS:
            raise ValueError(
                f'Content too small for caching: ~{int(estimated_tokens)} tokens '
                f'(minimum: {MIN_CACHE_TOKENS}). '
                f'Need at least ~{MIN_CACHE_TOKENS * CHARS_PER_TOKEN:,} characters.')

        ttl_seconds = int(ttl_hours * 3600)

        body = json.dumps({
            'model': f'models/{model}',
            'displayName': display_name[:128],
            'contents': [
                {
                    'parts': [{'text': book_text}],
                    'role': 'user'
                }
            ],
            'systemInstruction': {
                'parts': [{'text': system_instruction}]
            },
            'ttl': f'{ttl_seconds}s'
        })

        response = request(
            url=self._url(),
            data=body,
            headers=self._headers(),
            method='POST',
            timeout=300,  # Large payload may take time
            proxy_uri=self.proxy_uri
        )

        result = json.loads(response)
        if 'error' in result:
            raise Exception(
                f'Gemini cache creation failed: {result["error"].get("message", str(result["error"]))}')

        return result

    def get_cache(self, cache_name):
        """Get metadata for a specific cache.

        Args:
            cache_name: Cache resource name (e.g., 'cachedContents/abc123')

        Returns:
            dict with cache metadata
        """
        response = request(
            url=self._url(cache_name.replace('cachedContents/', '')),
            headers=self._headers(),
            method='GET',
            timeout=30,
            proxy_uri=self.proxy_uri
        )
        return json.loads(response)

    def list_caches(self):
        """List all existing caches.

        Returns:
            list of cache metadata dicts
        """
        response = request(
            url=self._url(),
            headers=self._headers(),
            method='GET',
            timeout=30,
            proxy_uri=self.proxy_uri
        )
        result = json.loads(response)
        return result.get('cachedContents', [])

    def update_cache_ttl(self, cache_name, ttl_hours):
        """Extend the TTL of an existing cache.

        Args:
            cache_name: Cache resource name
            ttl_hours: New TTL in hours
        """
        cache_id = cache_name.replace('cachedContents/', '')
        ttl_seconds = int(ttl_hours * 3600)

        body = json.dumps({
            'ttl': f'{ttl_seconds}s'
        })

        url = (f'{CACHE_ENDPOINT}/{cache_id}'
               f'?key={self.api_key}&updateMask=ttl')

        response = request(
            url=url,
            data=body,
            headers=self._headers(),
            method='PATCH',
            timeout=30,
            proxy_uri=self.proxy_uri
        )
        return json.loads(response)

    def delete_cache(self, cache_name):
        """Delete a cache.

        Args:
            cache_name: Cache resource name
        """
        cache_id = cache_name.replace('cachedContents/', '')
        response = request(
            url=self._url(cache_id),
            headers=self._headers(),
            method='DELETE',
            timeout=30,
            proxy_uri=self.proxy_uri
        )
        # DELETE returns empty on success
        return response if response else {'status': 'deleted'}

    def is_cache_valid(self, cache_name):
        """Check if a cache exists and hasn't expired.

        Args:
            cache_name: Cache resource name

        Returns:
            tuple (is_valid: bool, info: str)
        """
        try:
            cache = self.get_cache(cache_name)
            if 'error' in cache:
                return False, cache['error'].get('message', 'Cache not found')

            expire_time = cache.get('expireTime', '')
            if expire_time:
                # Parse ISO timestamp
                expire_dt = datetime.datetime.fromisoformat(
                    expire_time.replace('Z', '+00:00'))
                now = datetime.datetime.now(datetime.timezone.utc)
                if now >= expire_dt:
                    return False, 'Cache has expired'

                remaining = expire_dt - now
                hours = remaining.total_seconds() / 3600
                token_count = cache.get('usageMetadata', {}).get(
                    'totalTokenCount', 0)
                return True, (
                    f'Cache active: {int(hours)}h {int(remaining.total_seconds() % 3600 / 60)}m remaining, '
                    f'{token_count:,} tokens cached')

            return True, 'Cache exists (no expiration info)'
        except Exception as e:
            return False, f'Error checking cache: {str(e)}'


# --- Cost Estimation ---

def get_model_pricing(model_name):
    """Get pricing for a model by matching its prefix.

    Args:
        model_name: Full model name (e.g., 'gemini-2.5-flash-001')

    Returns:
        tuple (input, cached, storage/hr, output, deprecated) or None
    """
    for prefix, pricing in CACHE_PRICING.items():
        if model_name.startswith(prefix):
            return pricing
    return None


def estimate_cache_cost(token_count, model_name, ttl_hours=24):
    """Estimate caching costs, savings, and output costs.

    Args:
        token_count: Number of tokens to cache (input context)
        model_name: Model name
        ttl_hours: How long the cache will be kept

    Returns:
        dict with full cost breakdown or None if pricing unknown
    """
    pricing = get_model_pricing(model_name)
    if not pricing:
        return None

    input_per_1m, cached_per_1m, storage_per_1m_per_hour, output_per_1m, deprecated = pricing
    millions = token_count / 1_000_000

    storage_cost_per_hour = millions * storage_per_1m_per_hour
    storage_cost_total = storage_cost_per_hour * ttl_hours
    savings_per_request = millions * (input_per_1m - cached_per_1m)

    return {
        'token_count': token_count,
        'storage_cost_per_hour': storage_cost_per_hour,
        'storage_cost_total': storage_cost_total,
        'savings_per_request': savings_per_request,
        'input_cost_normal': millions * input_per_1m,
        'input_cost_cached': millions * cached_per_1m,
        'output_per_1m': output_per_1m,
        'discount_pct': int((1 - cached_per_1m / input_per_1m) * 100),
        'deprecated': deprecated,
    }


def estimate_session_cost(token_count, model_name, ttl_hours=1,
                          output_tokens_estimate=None):
    """Estimate total session cost for translating a book with caching.

    Calculates: creation + storage + estimated output.

    Args:
        token_count: Cached content token count
        model_name: Model name
        ttl_hours: Expected session duration in hours
        output_tokens_estimate: Estimated output tokens (default: ~same as input)

    Returns:
        dict with session cost breakdown or None
    """
    pricing = get_model_pricing(model_name)
    if not pricing:
        return None

    input_per_1m, cached_per_1m, storage_per_1m_per_hour, output_per_1m, deprecated = pricing
    in_millions = token_count / 1_000_000

    # Output is roughly same size as input for translation
    if output_tokens_estimate is None:
        output_tokens_estimate = token_count
    out_millions = output_tokens_estimate / 1_000_000

    creation_cost = in_millions * input_per_1m
    storage_cost = in_millions * storage_per_1m_per_hour * ttl_hours
    output_cost = out_millions * output_per_1m

    total_with_cache = creation_cost + storage_cost + output_cost
    total_without_cache = (in_millions * input_per_1m) + output_cost

    return {
        'creation_cost': creation_cost,
        'storage_cost': storage_cost,
        'output_cost': output_cost,
        'total_with_cache': total_with_cache,
        'total_without_cache': total_without_cache,
        'output_per_1m': output_per_1m,
        'deprecated': deprecated,
    }


# --- Local Metadata Persistence ---

def get_metadata_path(book_path):
    """Get the metadata JSON file path for a book.

    Args:
        book_path: Path to the ebook file

    Returns:
        Path to the metadata JSON file (next to the book file)
    """
    book_dir = os.path.dirname(os.path.abspath(book_path))
    return os.path.join(book_dir, METADATA_FILENAME)


def save_cache_metadata(book_path, cache_name, model, display_name,
                        ttl_hours, token_count=0):
    """Save cache metadata to a JSON file next to the book.

    Args:
        book_path: Path to the ebook file
        cache_name: Cache resource name from API
        model: Model name used
        display_name: Human-readable cache name
        ttl_hours: TTL in hours
        token_count: Number of cached tokens
    """
    metadata = {
        'cache_name': cache_name,
        'model': model,
        'display_name': display_name,
        'created_at': datetime.datetime.now(
            datetime.timezone.utc).isoformat(),
        'ttl_hours': ttl_hours,
        'token_count': token_count,
        'book_path': os.path.abspath(book_path)
    }

    path = get_metadata_path(book_path)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    return path


def load_cache_metadata(book_path):
    """Load cache metadata from the JSON file next to the book.

    Args:
        book_path: Path to the ebook file

    Returns:
        dict with metadata or None if not found
    """
    path = get_metadata_path(book_path)
    if not os.path.exists(path):
        return None

    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def delete_cache_metadata(book_path):
    """Delete the cache metadata file.

    Args:
        book_path: Path to the ebook file
    """
    path = get_metadata_path(book_path)
    if os.path.exists(path):
        os.remove(path)
