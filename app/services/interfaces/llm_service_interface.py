from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    stop_reason: Optional[str] = None


class ILLMService(ABC):
    """Contract for a chat-completion style LLM provider."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def generate(self, system: str, messages: List[Dict[str, str]]) -> LLMResult:
        """
        Run a single completion.
        :param system: system prompt (role + rules)
        :param messages: [{"role": "user"|"assistant", "content": str}, ...]
        """
        pass
