from .openai import ChatgptTranslate
from lingua.core.i18n import _

class OllamaTranslate(ChatgptTranslate):
    """
    Ollama integration using its OpenAI-compatible API.
    By default, it uses http://localhost:11434/v1/chat/completions.
    """
    name = 'Ollama'
    alias = 'Ollama (Local AI)'
    endpoint = 'http://localhost:11434/v1/chat/completions'
    
    # Ollama is local, so it doesn't need an API key
    need_api_key = False
    api_key_hint = 'Not required for local Ollama'
    api_key_errors = []
    
    # Fast local interval
    request_interval = 0.5
    concurrency_limit = 1 # Better for local hardware unless user has beefy GPU
    request_timeout = 60.0
    
    # Optimized prompt for local models (Safe for Llama3/Aya)
    prompt = _(
        'You are an expert literary translator. Translate from <slang> into <tlang>. '
        'Use a literary, natural style adapted to context. '
        'Respond ONLY with the translation, no extra text. '
        'Keep URLs and web addresses unchanged.'
    )

    def __init__(self):
        super().__init__()
        # Override with host from config if available
        self.endpoint = self.config.get('endpoint', self.endpoint)
        # Ensure it ends with /v1/chat/completions for compatibility
        if not self.endpoint.endswith('/chat/completions'):
            if self.endpoint.endswith('/v1'):
                self.endpoint += '/chat/completions'
            elif self.endpoint.endswith('/v1/'):
                self.endpoint += 'chat/completions'
            else:
                self.endpoint = self.endpoint.rstrip('/') + '/v1/chat/completions'

    def get_models(self):
        """Fetch models from Ollama."""
        try:
            import json
            from ..core.utils import request
            
            # Use the OpenAI-compatible endpoint to list models
            base_url = self.endpoint.split('/v1/')[0]
            models_url = f"{base_url}/v1/models"
            
            response = request(models_url, method='GET', timeout=5.0, proxy_uri=self.proxy_uri)
            data = json.loads(response)
            return [m['id'] for m in data.get('data', [])]
        except Exception:
            # Fallback to some common models if server is unreachable
            return ['aya:8b', 'llama3:8b', 'mistral', 'gemma:7b']

    def get_headers(self):
        # Ollama doesn't need Auth by default, but we keep the structure
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
