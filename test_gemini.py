import os
import unittest
from dotenv import load_dotenv

load_dotenv()

class GeminiIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("GEMINI_API_KEY") and os.getenv("RUN_INTEGRATION_TESTS"),
        "Set GEMINI_API_KEY and RUN_INTEGRATION_TESTS=1",
    )
    def test_models_can_be_listed(self):
        from google import genai

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        models = list(client.models.list())
        self.assertTrue(models)