"""
Text splitting utilities for processing large documents
"""

from typing import List, Optional
import re


class TextSplitter:
    """Split text into chunks for processing"""

    def __init__(self, chunk_size: int = 3000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks
        Tries to split at sentence boundaries when possible
        """
        if not text:
            return []

        # Clean text
        text = self._clean_text(text)

        # If text is short enough, return as single chunk
        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        current_pos = 0

        while current_pos < len(text):
            # Determine chunk end position
            chunk_end = min(current_pos + self.chunk_size, len(text))

            # If not at the end, try to find a sentence boundary
            if chunk_end < len(text):
                # Look for sentence endings
                sentence_end = self._find_sentence_boundary(
                    text[current_pos:chunk_end]
                )

                if sentence_end != -1:
                    chunk_end = current_pos + sentence_end

            # Extract chunk
            chunk = text[current_pos:chunk_end].strip()
            if chunk:
                chunks.append(chunk)

            # Move position with overlap
            if chunk_end >= len(text):
                break

            current_pos = chunk_end - self.chunk_overlap

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')

        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        return text.strip()

    def _find_sentence_boundary(self, text: str) -> int:
        """
        Find the last sentence boundary in text
        Returns -1 if no boundary found
        """
        # Look for sentence endings (., !, ?)
        sentence_endings = ['.', '!', '?']

        last_boundary = -1
        for i in range(len(text) - 1, max(len(text) - 500, -1), -1):
            if text[i] in sentence_endings:
                # Check if it's likely a real sentence ending
                if i + 1 < len(text) and text[i + 1] in ' \n':
                    last_boundary = i + 1
                    break

        return last_boundary

    def split_by_sections(self, text: str) -> dict:
        """
        Split text by common academic paper sections
        Returns a dictionary of section_name: content
        """
        sections = {}

        # Common section patterns
        section_patterns = [
            r'(?i)^abstract',
            r'(?i)^introduction',
            r'(?i)^background',
            r'(?i)^related\s+work',
            r'(?i)^methodology',
            r'(?i)^methods',
            r'(?i)^results',
            r'(?i)^discussion',
            r'(?i)^conclusion',
            r'(?i)^references',
        ]

        lines = text.split('\n')
        current_section = 'content'
        current_content = []

        for line in lines:
            # Check if line matches a section pattern
            is_section = False
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    # Save previous section
                    if current_content:
                        sections[current_section] = '\n'.join(current_content).strip()

                    # Start new section
                    current_section = line.strip().lower()
                    current_content = []
                    is_section = True
                    break

            if not is_section:
                current_content.append(line)

        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections