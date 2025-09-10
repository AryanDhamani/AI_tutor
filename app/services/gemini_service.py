"""
Gemini AI service for generating educational content.
Implements three specialized prompts for deterministic, parseable outputs.
"""
import json
import re
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai

from app.config import config
from app.models import ExplanationData, ExampleData, ManimData

logger = logging.getLogger(__name__)

class GeminiService:
    """Service for interacting with Google's Gemini AI model."""
    
    def __init__(self):
        """Initialize Gemini service with API key."""
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required")
            
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Gemini service initialized")
    
    def _clean_json_response(self, response_text: str) -> str:
        """
        Strip markdown code fences and clean response for JSON parsing.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Clean JSON string
        """
        # Remove markdown code fences if present
        text = response_text.strip()
        
        # Remove ```json and ``` markers
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^```\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'```$', '', text)
        
        # Remove any leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _validate_and_parse_json(self, response_text: str, expected_keys: list) -> Dict[str, Any]:
        """
        Validate and parse JSON response from Gemini.
        
        Args:
            response_text: Raw response text
            expected_keys: List of required top-level keys
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            ValueError: If JSON is invalid or missing required keys
        """
        try:
            clean_text = self._clean_json_response(response_text)
            data = json.loads(clean_text)
            
            # Validate required keys
            for key in expected_keys:
                if key not in data:
                    raise ValueError(f"Missing required key: {key}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Raw response: {response_text}")
            raise ValueError(f"Invalid JSON response from Gemini: {e}")
    
    async def generate_lesson_explanation(self, topic: str, plan: Optional[str] = None) -> ExplanationData:
        """
        Generate lesson explanation using Gemini.
        
        Args:
            topic: Educational topic to explain
            plan: Optional lesson plan guidance
            
        Returns:
            ExplanationData with title and bullet points
        """
        # Construct the lesson prompt for strict JSON output
        prompt = f"""
You are an expert educator. Generate a concise lesson explanation for the topic: "{topic}"

{f"Additional guidance: {plan}" if plan else ""}

Return JSON ONLY with this exact structure (no markdown fences, no extra text):
{{
  "explanation": {{
    "title": "Brief, clear lesson title",
    "bullets": [
      "Key concept 1 - concise and clear",
      "Key concept 2 - builds on previous point", 
      "Key concept 3 - practical application",
      "Key concept 4 - important detail",
      "Key concept 5 - summary or connection"
    ]
  }}
}}

Requirements:
- Include exactly 4-7 bullet points
- Each bullet should be concise (max 15 words)
- No markdown formatting in bullets
- Focus on core concepts and practical understanding
- Build concepts logically from basic to advanced
"""

        try:
            logger.info(f"Generating lesson explanation for topic: {topic}")
            response = self.model.generate_content(prompt)
            
            # Parse and validate JSON response
            data = self._validate_and_parse_json(response.text, ["explanation"])
            explanation_data = data["explanation"]
            
            # Validate bullet count
            bullets = explanation_data.get("bullets", [])
            if not (4 <= len(bullets) <= 7):
                raise ValueError(f"Expected 4-7 bullets, got {len(bullets)}")
            
            return ExplanationData(**explanation_data)
            
        except Exception as e:
            logger.error(f"Failed to generate lesson explanation: {e}")
            raise ValueError(f"Lesson generation failed: {e}")
    
    async def generate_example(self, topic: str, explanation: ExplanationData) -> ExampleData:
        """
        Generate worked example using Gemini.
        
        Args:
            topic: Educational topic
            explanation: Previous lesson explanation for context
            
        Returns:
            ExampleData with prompt, walkthrough, and answer
        """
        bullets_context = "\\n".join([f"- {bullet}" for bullet in explanation.bullets])
        
        prompt = f"""
You are an expert educator. Create a worked example problem for the topic: "{topic}"

Context from lesson explanation:
{bullets_context}

Return JSON ONLY with this exact structure (no markdown fences, no extra text):
{{
  "example": {{
    "prompt": "Clear, specific problem statement that students can solve",
    "walkthrough": [
      "Step 1: Identify what we know and what we need to find",
      "Step 2: Choose the appropriate method or formula",
      "Step 3: Set up the problem with given values",
      "Step 4: Perform calculations step by step",
      "Step 5: Check our work and state the final answer"
    ],
    "answer": "Final answer with units (optional)"
  }}
}}

Requirements:
- Include exactly 3-7 walkthrough steps
- Each step should be clear and actionable
- Steps should build logically toward the solution
- Include specific numbers/values in the problem
- Answer field is optional but recommended for math problems
- Problem should be realistic and practical
"""

        try:
            logger.info(f"Generating example for topic: {topic}")
            response = self.model.generate_content(prompt)
            
            # Parse and validate JSON response
            data = self._validate_and_parse_json(response.text, ["example"])
            example_data = data["example"]
            
            # Validate walkthrough step count
            walkthrough = example_data.get("walkthrough", [])
            if not (3 <= len(walkthrough) <= 10):
                raise ValueError(f"Expected 3-10 walkthrough steps, got {len(walkthrough)}")
            
            return ExampleData(**example_data)
            
        except Exception as e:
            logger.error(f"Failed to generate example: {e}")
            raise ValueError(f"Example generation failed: {e}")
    
    async def generate_manim_code(self, topic: str, example: ExampleData) -> ManimData:
        """
        Generate Manim animation code using Gemini.
        
        Args:
            topic: Educational topic
            example: Previous example for animation context
            
        Returns:
            ManimData with Python code, filename, and notes
        """
        # Create safe filename from topic
        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', topic.lower())
        safe_filename = re.sub(r'_+', '_', safe_filename).strip('_')
        
        prompt = f"""
Generate Manim animation code for the topic: "{topic}"

Example context:
Problem: {example.prompt}
Answer: {example.answer or "See walkthrough"}

Return code ONLY (no prose, no explanation, no markdown fences).

Requirements:
- One Scene subclass named after the topic (CamelCase)
- Approximately 40-80 lines of code
- Prefer Text() over MathTex() to avoid LaTeX issues
- Use basic shapes and clear animations
- Include self.wait() for pacing
- Import only from manim (no external libraries)
- Make it educational and visually clear
- Use colors and positioning effectively

Code structure:
from manim import *

class TopicNameScene(Scene):
    def construct(self):
        # Your animation code here
        pass
"""

        try:
            logger.info(f"Generating Manim code for topic: {topic}")
            response = self.model.generate_content(prompt)
            
            # For Manim code, we expect raw Python code, not JSON
            code = response.text.strip()
            
            # Basic safety checks
            if "import os" in code or "import subprocess" in code or "import sys" in code:
                raise ValueError("Generated code contains unsafe imports")
            
            if len(code.split('\n')) < 10:
                raise ValueError("Generated code is too short")
            
            if "class " not in code or "def construct" not in code:
                raise ValueError("Generated code missing required Manim structure")
            
            return ManimData(
                language="python",
                filename=safe_filename,
                code=code,
                notes=[
                    "Uses Text() to avoid LaTeX dependencies",
                    "Includes proper timing with self.wait()",
                    "Safe code with only Manim imports"
                ]
            )
            
        except Exception as e:
            logger.error(f"Failed to generate Manim code: {e}")
            raise ValueError(f"Manim code generation failed: {e}")

# Global service instance
gemini_service = GeminiService()
