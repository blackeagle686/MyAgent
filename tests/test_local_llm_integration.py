import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock heavy libraries to prevent accidents
sys.modules['transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['llama_cpp'] = MagicMock()
sys.modules['bitsandbytes'] = MagicMock()
sys.modules['accelerate'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

from core.services.local_llm_service import LocalLLMService, local_llm_service
from core.services.llm_service import LLMClient

class TestLocalLLMIntegration(unittest.TestCase):
    def test_singleton(self):
        """Verify that LocalLLMService follows the singleton pattern."""
        service1 = LocalLLMService()
        service2 = LocalLLMService()
        self.assertIs(service1, service2)
        self.assertIs(service1, local_llm_service)

    def test_lazy_loading_structure(self):
        """Verify that models are not loaded until needed."""
        service = LocalLLMService()
        self.assertIsNone(service.thinker_model)
        self.assertIsNone(service.planner_model)
        self.assertIsNone(service.embedding_model)

    @patch('core.services.llm_service.OpenAI')
    @patch('core.services.llm_service.local_llm_service')
    def test_fallback_logic(self, mock_local_service, mock_openai):
        """Verify that LLMClient falls back to local_llm_service on error."""
        # Setup mock to fail
        mock_openai.return_value.chat.completions.create.side_effect = Exception("OpenRouter Down")
        
        client = LLMClient()
        prompt = "test prompt"
        
        # Test thinker fallback
        client.generate(prompt, model="some-model")
        mock_local_service.generate_thinker.assert_called_once()
        
        # Test planner fallback (assuming Config.coder_model matches)
        from config import Config
        client.coder_model = "coder-model"
        client.generate(prompt, model="coder-model")
        mock_local_service.generate_planner.assert_called_once()

    @patch('core.services.llm_service.OpenAI')
    @patch('core.services.llm_service.local_llm_service')
    def test_embedding_fallback_logic(self, mock_local_service, mock_openai):
        """Verify that LLMClient falls back to local_llm_service for embeddings on error."""
        # Setup mock to fail
        mock_openai.return_value.embeddings.create.side_effect = Exception("OpenRouter Embedding Down")
        
        client = LLMClient()
        client.embed("test text")
        mock_local_service.embed.assert_called_once_with("test text")

if __name__ == '__main__':
    unittest.main()
