"""Summarization engine using OpenAI/Gemini."""

import json
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime


class SummarizationProvider(Enum):
    """Summarization provider options."""
    OPENAI = "openai"
    GEMINI = "gemini"


class Summarizer:
    """Generates summaries from transcripts."""
    
    def __init__(
        self,
        provider: SummarizationProvider = SummarizationProvider.OPENAI,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """Initialize summarizer.
        
        Args:
            provider: Summarization provider
            api_key: API key for the provider
            model: Model name to use
        """
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self._transcript_buffer: List[str] = []
        self._last_summary_time = datetime.now()
    
    def add_transcript_segment(self, text: str):
        """Add a transcript segment to the buffer.
        
        Args:
            text: Transcript text segment
        """
        if text and text.strip():
            self._transcript_buffer.append(text.strip())
    
    def generate_mini_summary(self, transcript_segments: List[str]) -> Optional[Dict]:
        """Generate a mini-summary from recent transcript segments.
        
        Creates a brief bullet-point summary of recent conversation segments.
        Used for live updates during transcription (every 30 seconds).
        
        Args:
            transcript_segments: List of recent transcript segments (should be new segments only)
            
        Returns:
            Summary dictionary with 'bullets' key containing list of bullet points, or None
        """
        if not transcript_segments:
            return None
        
        # Join segments into text (limit to last 20 to avoid API token limits)
        # Segments should already be filtered to only new content
        transcript_text = " ".join(transcript_segments[-20:])
        
        prompt = f"""Generate a brief bullet-point summary of the following meeting transcript segment:

{transcript_text}

Provide 3-5 key bullet points. Format as JSON:
{{
    "bullets": ["point1", "point2", ...]
}}"""
        
        return self._call_api(prompt, is_mini=True)
    
    def generate_full_summary(self, full_transcript: str) -> Optional[Dict]:
        """Generate a comprehensive summary from the full transcript.
        
        Creates a structured summary with key points, decisions, action items,
        people mentioned, and topics. Called at the end of a meeting.
        
        Args:
            full_transcript: Complete meeting transcript text
            
        Returns:
            Summary dictionary with keys: key_points, decisions, action_items,
            people_mentioned, topics, summary
        """
        if not full_transcript:
            return None
        
        # Prompt for structured summary generation
        prompt = f"""Generate a comprehensive meeting summary from the following transcript:

{full_transcript}

Provide a structured summary in JSON format:
{{
    "key_points": ["point1", "point2", ...],
    "decisions": ["decision1", "decision2", ...],
    "action_items": [
        {{
            "task": "task description",
            "assignee": "person name or 'TBD'",
            "deadline": "date or 'TBD'"
        }}
    ],
    "people_mentioned": ["person1", "person2", ...],
    "topics": ["topic1", "topic2", ...],
    "summary": "Overall meeting summary paragraph"
}}"""
        
        return self._call_api(prompt, is_mini=False)
    
    def _call_api(self, prompt: str, is_mini: bool = False) -> Optional[Dict]:
        """Call the summarization API.
        
        Args:
            prompt: Prompt text
            is_mini: Whether this is a mini-summary
            
        Returns:
            Summary dictionary or None
        """
        try:
            if self.provider == SummarizationProvider.OPENAI:
                return self._call_openai(prompt, is_mini)
            elif self.provider == SummarizationProvider.GEMINI:
                return self._call_gemini(prompt, is_mini)
        except Exception as e:
            print(f"Error generating summary: {e}")
            return None
    
    def _call_openai(self, prompt: str, is_mini: bool) -> Optional[Dict]:
        """Call OpenAI API for summarization.
        
        Args:
            prompt: Prompt text
            is_mini: Whether this is a mini-summary
            
        Returns:
            Summary dictionary or None
        """
        try:
            from openai import OpenAI
            
            if not self.api_key:
                return None
            
            client = OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a meeting summarization assistant. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if content:
                return json.loads(content)
            
            return None
            
        except ImportError:
            print("openai package not installed. Install with: pip install openai")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return None
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None
    
    def _call_gemini(self, prompt: str, is_mini: bool) -> Optional[Dict]:
        """Call Gemini API for summarization.
        
        Args:
            prompt: Prompt text
            is_mini: Whether this is a mini-summary
            
        Returns:
            Summary dictionary or None
        """
        try:
            import google.generativeai as genai
            
            if not self.api_key:
                return None
            
            genai.configure(api_key=self.api_key)
            # Try the requested model, with fallbacks
            model_name = self.model
            
            # Try the requested model first
            try:
                model = genai.GenerativeModel(model_name)
            except Exception as e:
                # If that fails, try fallback models (prioritize free tier friendly models)
                fallback_models = ['gemini-2.5-flash', 'gemini-pro', 'gemini-3-pro-preview']
                model = None
                for fallback in fallback_models:
                    try:
                        model = genai.GenerativeModel(fallback)
                        print(f"Using model: {fallback} (requested '{model_name}' not available)")
                        break
                    except:
                        continue
                
                if model is None:
                    raise Exception(f"Could not find any working Gemini model. Tried: {model_name}, {', '.join(fallback_models)}. Error: {e}")
            
            full_prompt = f"{prompt}\n\nRespond with JSON only, no markdown formatting."
            
            response = model.generate_content(full_prompt)
            
            # Extract JSON from response
            text = response.text.strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
            
        except ImportError:
            print("google-generativeai package not installed. Install with: pip install google-generativeai")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            return None
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return None
    
    def get_full_transcript(self) -> str:
        """Get the complete transcript from buffer.
        
        Returns:
            Full transcript text
        """
        return " ".join(self._transcript_buffer)
    
    def clear_buffer(self):
        """Clear the transcript buffer."""
        self._transcript_buffer = []

