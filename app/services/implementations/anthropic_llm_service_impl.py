import logging
from typing import Dict, List

from app.config.app_config import AIConfigConstants
from app.exceptions.custom_exceptions import LLMNotConfiguredException, LLMServiceException
from app.services.interfaces.llm_service_interface import ILLMService, LLMResult

logger = logging.getLogger(__name__)


class AnthropicLLMService(ILLMService):
    """Claude via the official `anthropic` Python SDK (Messages API)."""

    def __init__(self, api_key: str, model: str,
                 max_tokens: int = AIConfigConstants.LLM_MAX_TOKENS,
                 temperature: float = AIConfigConstants.LLM_TEMPERATURE,
                 timeout: float = AIConfigConstants.LLM_TIMEOUT_SECONDS):
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if not self._api_key:
            raise LLMNotConfiguredException()
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise LLMNotConfiguredException(f"anthropic SDK is not installed: {exc}")
            self._client = anthropic.Anthropic(api_key=self._api_key, timeout=self._timeout, max_retries=2)
        return self._client

    def generate(self, system: str, messages: List[Dict[str, str]]) -> LLMResult:
        client = self._get_client()
        import anthropic

        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=system,
                messages=messages,
            )
        except anthropic.AuthenticationError:
            logger.exception("Anthropic authentication failed")
            raise LLMNotConfiguredException("ANTHROPIC_API_KEY was rejected by the provider.")
        except anthropic.RateLimitError:
            logger.warning("Anthropic rate limit hit")
            raise LLMServiceException("LLM provider rate limit reached. Please retry shortly.")
        except anthropic.APIError as exc:
            logger.exception("Anthropic API error")
            raise LLMServiceException(f"LLM provider error: {getattr(exc, 'message', str(exc))}")

        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
        usage = getattr(response, "usage", None)
        return LLMResult(
            text=text,
            model=getattr(response, "model", self._model),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            stop_reason=getattr(response, "stop_reason", None),
        )
