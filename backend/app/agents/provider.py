"""Provider boundary: bounded input, no privileged tools, validated JSON output."""
import json
from pathlib import Path
import httpx
from pydantic import BaseModel
from app.core.config import settings

class ProviderError(RuntimeError):
    pass

class StructuredProvider:
    def generate(self, agent: str, context: dict, schema: type[BaseModel]) -> BaseModel:
        if settings.demo_mode or settings.ai_provider == 'local':
            raise ProviderError('Structured AI requires live mode and a configured provider.')
        if not settings.openai_api_key:
            raise ProviderError('AI provider credential is not configured.')
        prompt = (Path(__file__).parents[1] / 'prompts' / f'{agent}.md').read_text()
        endpoint = settings.ai_endpoint.rstrip('/')
        headers = {'api-key': settings.openai_api_key} if settings.ai_provider == 'azure' else {'Authorization': f'Bearer {settings.openai_api_key}'}
        payload = {'model': settings.openai_model, 'messages': [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': json.dumps(context, default=str)[:40000]}],
            'response_format': {'type': 'json_schema', 'json_schema': {'name': agent, 'strict': True, 'schema': schema.model_json_schema()}},
            'max_completion_tokens': 2500}
        try:
            with httpx.Client(timeout=45) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
                return schema.model_validate_json(response.json()['choices'][0]['message']['content'])
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError('AI generation failed or returned invalid structured output; retry after reviewing provider configuration.') from exc
