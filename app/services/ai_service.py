import json
import logging
import re
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

class AiService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                logger.info("Gemini AI successfully configured.")
            except Exception as e:
                logger.error(f"Error configuring Gemini AI: {e}")
        else:
            logger.warning("GEMINI_API_KEY is not set. AiService will operate in MOCK fallback mode.")

    def is_mock_mode(self) -> bool:
        """
        Check if the service is in mock mode (no API key configured).
        """
        return not bool(self.api_key)

    def generate_text(self, prompt: str) -> str:
        """
        Generates text using Gemini 2.5 Flash based on the given prompt.
        Throws ValueError if no API key is present.
        """
        if self.is_mock_mode():
            raise ValueError("AiService is in mock mode. Cannot generate text from Gemini.")
            
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            logger.info("Sending prompt to Gemini 2.5 Flash for text generation...")
            response = model.generate_content(prompt)
            
            result = response.text.strip()
            logger.info(f"Generated text: {result}")
            return result
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {e}")
            raise e

    def generate_json(self, prompt: str, image_bytes: bytes = None, mime_type: str = "image/jpeg") -> dict:
        """
        Generates and parses JSON using Gemini 2.5 Flash based on the given prompt and optional image.
        Throws ValueError if no API key is present.
        """
        if self.is_mock_mode():
            raise ValueError("AiService is in mock mode. Cannot generate JSON from Gemini.")

        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            contents = []
            if image_bytes:
                image_part = {
                    "mime_type": mime_type,
                    "data": image_bytes
                }
                contents.append(image_part)
                logger.info(f"Sending prompt and image ({mime_type}) to Gemini 2.5 Flash...")
            else:
                logger.info("Sending prompt to Gemini 2.5 Flash...")
                
            contents.append(prompt)
            
            response = model.generate_content(contents)
            
            response_text = response.text.strip()
            logger.info(f"Raw response from Gemini: {response_text}")

            parsed_data = self._clean_and_parse_json(response_text)
            return parsed_data

        except Exception as e:
            logger.error(f"Error parsing JSON response with Gemini: {e}")
            raise e

    def _clean_and_parse_json(self, text: str) -> dict:
        """
        Helper to extract and parse JSON from the model response, 
        even if it wraps it in markdown code blocks.
        """
        cleaned = text
        if "```json" in text:
            match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
            if match:
                cleaned = match.group(1)
        elif "```" in text:
            match = re.search(r"```\s*([\s\S]*?)\s*```", text)
            if match:
                cleaned = match.group(1)
                
        cleaned = cleaned.strip()
        
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as jde:
            logger.error(f"Failed to parse text as JSON. Text: {cleaned}. Error: {jde}")
            raise ValueError("Respons dari AI tidak berformat JSON yang valid")

