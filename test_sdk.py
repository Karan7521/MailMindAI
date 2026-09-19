import os
import unittest
from dotenv import load_dotenv

load_dotenv()

class GeminiSdkIntegrationTests(unittest.TestCase):
	@unittest.skipUnless(
		os.getenv("GEMINI_API_KEY") and os.getenv("RUN_INTEGRATION_TESTS"),
		"Set GEMINI_API_KEY and RUN_INTEGRATION_TESTS=1",
	)
	def test_generate_content(self):
		from google import genai

		client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
		response = client.models.generate_content(
			model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"), contents="Say Hello"
		)
		self.assertTrue(response.text)