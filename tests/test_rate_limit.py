import sys
import os
import unittest
import time
from unittest.mock import MagicMock, patch, mock_open

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock heavy deps
sys.modules['transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['llama_cpp'] = MagicMock()
sys.modules['bitsandbytes'] = MagicMock()
sys.modules['accelerate'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()

from core.services.llm_service import LLMClient
from config import Config

class TestRateLimitHandling(unittest.TestCase):
    def setUp(self):
        # Disable caching for logic tests to avoid collisions
        Config.enable_cache = False
        Config.max_retries = 2
        Config.backoff_factor = 0.1 # Small backoff for fast tests

    @patch('core.services.llm_service.OpenAI')
    @patch('core.services.llm_service.local_llm_service')
    def test_exponential_backoff(self, mock_local, mock_openai):
        client = LLMClient()
        # Mock 429 error twice, then success
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Success"
        mock_openai.return_value.chat.completions.create.side_effect = [
            Exception("Rate limit 429 error"),
            Exception("Rate limit 429 error"),
            mock_response
        ]
        
        with patch('time.sleep', return_value=None) as mock_sleep:
            res = client.generate("test prompt")
            self.assertEqual(res, "Success")
            self.assertEqual(mock_openai.return_value.chat.completions.create.call_count, 3)
            self.assertEqual(mock_sleep.call_count, 2)

    @patch('core.services.llm_service.OpenAI')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"content": "Cached Result"}')
    def test_caching_logic(self, mock_file, mock_exists, mock_openai):
        Config.enable_cache = True
        mock_exists.return_value = True
        client = LLMClient()
        
        res = client.generate("test prompt")
        
        self.assertEqual(res, "Cached Result")
        # Ensure API was NOT called
        mock_openai.return_value.chat.completions.create.assert_not_called()

    @patch('core.services.llm_service.OpenAI')
    @patch('core.services.llm_service.local_llm_service')
    def test_fallback_after_max_retries(self, mock_local, mock_openai):
        client = LLMClient()
        # Mock 429 infinitely
        mock_openai.return_value.chat.completions.create.side_effect = Exception("Rate limit 429 error")
        mock_local.generate_thinker.return_value = "Local Fallback"
        mock_local.generate_planner.return_value = "Local Fallback"
        with patch('time.sleep', return_value=None):
            res = client.generate("test prompt")
            self.assertEqual(res, "Local Fallback")
            # Should have tried API 1 initial + Config.max_retries times
            self.assertEqual(mock_openai.return_value.chat.completions.create.call_count, 1 + Config.max_retries)
            # Either thinker or planner should be called based on target_model == self.coder_model
            total_local_calls = mock_local.generate_thinker.call_count + mock_local.generate_planner.call_count
            self.assertEqual(total_local_calls, 1)

if __name__ == '__main__':
    unittest.main()
