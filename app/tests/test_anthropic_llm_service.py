import inspect
import unittest
from types import SimpleNamespace

from django.test import SimpleTestCase

from app.services.implementations.anthropic_llm_service_impl import AnthropicLLMService

try:
    import anthropic
    from anthropic.resources.messages import Messages
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@unittest.skipUnless(HAS_ANTHROPIC, "anthropic SDK not installed")
class AnthropicLLMServiceTests(SimpleTestCase):
    """Offline: checks our call matches the INSTALLED SDK's messages.create() signature."""

    def test_generate_uses_only_supported_kwargs(self):
        captured = {}
        accepted = set(inspect.signature(Messages.create).parameters)

        def fake_create(**kwargs):
            captured.update(kwargs)
            unknown = set(kwargs) - accepted
            if unknown:
                raise TypeError(f"Messages.create() got unexpected keyword arguments {unknown}")
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text="hello")],
                model="claude-test",
                usage=SimpleNamespace(input_tokens=3, output_tokens=1),
                stop_reason="end_turn",
            )

        service = AnthropicLLMService(api_key="sk-test", model="claude-test")
        service._client = SimpleNamespace(messages=SimpleNamespace(create=fake_create))
        result = service.generate(system="sys", messages=[{"role": "user", "content": "hi"}])

        self.assertEqual(result.text, "hello")
        self.assertEqual(result.input_tokens, 3)
        self.assertEqual(captured["system"], "sys")
        self.assertNotIn("temperature", captured)
