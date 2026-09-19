import os
import unittest
from dotenv import load_dotenv

load_dotenv()


class LangChainIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv("GEMINI_API_KEY") and os.getenv("RUN_INTEGRATION_TESTS"),
        "Set GEMINI_API_KEY and RUN_INTEGRATION_TESTS=1",
    )
    def test_gemini_chat(self):
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
            google_api_key=os.environ["GEMINI_API_KEY"],
        )
        response = llm.invoke("Say hello")
        self.assertTrue(response.content)