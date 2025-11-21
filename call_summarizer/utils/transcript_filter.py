"""Filter and clean transcript text."""

import re
from typing import List


class TranscriptFilter:
    """Filters and cleans transcript text."""
    
    # Common repetitive phrases to filter (video watermarks, etc.)
    FILTER_PATTERNS = [
        r'(?i)transcribed by eso',
        r'(?i)thanks?\s+(you\s+)?for\s+watching',  # "thanks for watching", "thank you for watching"
        r'(?i)thanks?\s+(you\s+)?for\s+watching\s+\w*',  # Catch "thanks for watching vide", "thanks for watching video", etc.
        r'(?i)thanks?\s+(you\s+)?for\s+watching\s*$',  # Catch incomplete phrases ending with "thanks for watching"
        r'(?i)watching\s+vide',  # Catch "watching vide" or "watching video"
        r'(?i)subscribe\s+to.*channel',
        r'(?i)like.*subscribe',
        r'(?i)don\'t\s+forget\s+to\s+subscribe',
        r'(?i)hit\s+the\s+like\s+button',
        r'(?i)ring\s+the\s+bell',
        r'(?i)^\s*(thanks?|thank)\s+(you\s+)?for\s+(watching|viewing)',  # Catch variations
        r'(?i)transcribe\s+accurately\s+with\s+proper\s+punctuation',  # Filter Whisper prompt text
        r'(?i)transcribe\s+accurately',  # Partial match
        r'(?i)proper\s+punctuation\s+and\s+spelling',  # Filter Whisper prompt text
        r'(?i)if\s+you\s+have\s+any\s+questions',  # Video watermark
        r'(?i)please\s+post\s+them\s+in\s+the\s+comments',  # Video watermark
        r'(?i)comments?\s+section?\s+below',  # Video watermark
        r'(?i)post\s+.*\s+in\s+.*\s+comments?',  # Video watermark variations
        r'(?i)sign\s+up\s+for\s+.*\s+meeting',  # Video watermark
        r'(?i)give\s+.*\s+warm\s+welcome',  # Video watermark
        r'(?i)thank\s+you\s+for\s+being\s+here',  # Repetitive meeting phrases
        r'(?i)thank\s+you\s+for\s+being\s+here\s+today',  # Repetitive meeting phrases
        # Filter repetitive number sequences (likely noise or system sounds)
        r'^\s*\d+(\s*,\s*\d+){10,}',  # More than 10 numbers in sequence
        r'(\d+\s*,\s*\d+\s*){5,}',  # Repeated number pairs like "51, 52" 5+ times
        r'^\s*\d+\s*,\s*\d+\s*,\s*\d+',  # Number sequences starting with 3+ numbers
        r'^\s*[0-9\s,]+$',  # Text that is only numbers and commas
        r'^\s*$',  # Empty lines
    ]
    
    # Minimum length for valid transcript segments
    MIN_LENGTH = 3
    
    def __init__(self):
        self._recent_segments: List[str] = []
        self._max_recent = 15  # Track last 15 segments for duplicate detection
        self._duplicate_threshold = 0.7  # Similarity threshold for duplicates (70% match - more aggressive)
        self._repetition_count = {}  # Track how many times we've seen similar phrases
    
    def filter_text(self, text: str) -> str:
        """Filter and clean transcript text.
        
        Args:
            text: Raw transcript text
            
        Returns:
            Filtered text or None if should be skipped
        """
        if not text:
            return None
        
        # Strip whitespace
        text = text.strip()
        
        # Check minimum length
        if len(text) < self.MIN_LENGTH:
            return None
        
        # Check against filter patterns
        for pattern in self.FILTER_PATTERNS:
            if re.search(pattern, text):
                return None
        
        # Check for duplicates in recent segments (exact match)
        text_lower = text.lower().strip()
        recent_lower = [s.lower().strip() for s in self._recent_segments]
        
        # Count exact duplicates
        exact_count = recent_lower.count(text_lower)
        if exact_count >= 1:  # If we've seen this exact phrase before, filter it
            return None
        
        # Check for similar/repetitive phrases (fuzzy match)
        # If text is very similar to recent segments, filter it out
        similar_count = 0
        for recent in recent_lower:
            if self._is_similar(text_lower, recent):
                similar_count += 1
                # If we've seen similar phrases 2+ times, filter this one
                if similar_count >= 2:
                    return None
        
        # Check for repetitive patterns within the text itself
        if self._has_repetitive_pattern(text_lower):
            return None
        
        # Add to recent segments
        self._recent_segments.append(text_lower)
        if len(self._recent_segments) > self._max_recent:
            self._recent_segments.pop(0)
        
        return text
    
    def clean_text(self, text: str) -> str:
        """Clean text for better readability.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Capitalize first letter
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        
        # Add period if missing
        if text and not text[-1] in '.!?':
            text = text + '.'
        
        return text.strip()
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """Check if two texts are similar (for duplicate detection).
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            True if texts are similar enough to be considered duplicates
        """
        if not text1 or not text2:
            return False
        
        # Exact match
        if text1 == text2:
            return True
        
        # Check if one contains the other (for partial matches)
        if len(text1) > 5 and len(text2) > 5:
            if text1 in text2 or text2 in text1:
                # Calculate similarity ratio
                shorter = min(len(text1), len(text2))
                longer = max(len(text1), len(text2))
                if shorter / longer >= self._duplicate_threshold:
                    return True
        
        # Check word overlap for very short phrases
        words1 = set(text1.split())
        words2 = set(text2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            if overlap >= self._duplicate_threshold and len(words1) <= 5:
                return True
        
        return False
    
    def _has_repetitive_pattern(self, text: str) -> bool:
        """Check if text contains repetitive patterns (like repeating number sequences).
        
        Args:
            text: Text to check
            
        Returns:
            True if text has repetitive patterns
        """
        if not text or len(text) < 10:
            return False
        
        # Check for repeating number sequences (e.g., "51, 52, 51, 52, 51, 52")
        # Look for patterns that repeat at least 3 times
        words = text.split()
        if len(words) >= 6:
            # Check if we have repeating 2-word patterns
            for i in range(len(words) - 4):
                pattern = ' '.join(words[i:i+2])
                # Check if this pattern repeats
                count = text.count(pattern)
                if count >= 3:
                    return True
        
        # Check for repeating single words/phrases
        # If a word appears 5+ times in a short text, it's likely noise
        word_counts = {}
        for word in words:
            if len(word) > 2:  # Ignore very short words
                word_counts[word] = word_counts.get(word, 0) + 1
                if word_counts[word] >= 5:
                    return True
        
        # Check for number sequences that are too long
        # If text is mostly numbers and commas, it's likely noise
        non_numeric = sum(1 for c in text if c.isalpha() or c.isspace())
        if len(text) > 20 and non_numeric < len(text) * 0.3:  # Less than 30% non-numeric
            return True
        
        return False

