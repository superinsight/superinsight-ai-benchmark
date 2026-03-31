"""
Source Index for mapping citations to source text.

This module provides utilities for indexing source text
by page/file for efficient lookup during validation.
"""

import re
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class SourceExcerpt:
    """A section of source text with metadata."""
    file: str
    file_id: str
    page: int
    text: str
    paragraph_ref: str = ""


class SourceIndex:
    """
    Index source text by page/file for quick lookup.
    
    The source text is expected to contain citation markers
    that delimit sections of text.
    """
    
    def __init__(self, source_text: str = ""):
        self.pages: Dict[Tuple[str, int], SourceExcerpt] = {}
        self.by_file_id: Dict[str, List[SourceExcerpt]] = {}
        self.by_paragraph_ref: Dict[str, SourceExcerpt] = {}
        self._full_text: str = source_text  # Store original text
        
        if source_text:
            self._parse_source(source_text)
    
    def get_full_text(self) -> str:
        """Return the full source text."""
        return self._full_text
    
    def _parse_source(self, source_text: str) -> None:
        """Parse source text and build index."""
        # Pattern for source citations
        citation_pattern = r'<!--\s*Source:\s*(.*?)-->'
        
        # Find all citations and their positions
        citations = []
        for match in re.finditer(citation_pattern, source_text, re.DOTALL | re.IGNORECASE):
            citation_text = match.group(1)
            pos = match.end()
            
            # Parse citation fields
            fields = self._parse_citation_fields(citation_text)
            if fields.get('file') and fields.get('page'):
                citations.append({
                    'pos': pos,
                    'fields': fields,
                })
        
        # Extract text between citations
        for i, citation in enumerate(citations):
            # Find end of this section (start of next citation or end of text)
            if i + 1 < len(citations):
                next_citation = citations[i + 1]
                # Try to find the citation marker to calculate its length
                search_start = max(0, next_citation['pos'] - 200)
                search_end = min(len(source_text), next_citation['pos'] + 100)
                next_match = re.search(
                    citation_pattern, 
                    source_text[search_start:search_end],
                    re.DOTALL | re.IGNORECASE
                )
                if next_match:
                    end_pos = next_citation['pos'] - len(next_match.group(0))
                else:
                    # Fallback: use the position of next citation
                    end_pos = next_citation['pos']
            else:
                end_pos = len(source_text)
            
            # Get text for this section
            text = source_text[citation['pos']:end_pos].strip()
            
            # Create excerpt
            fields = citation['fields']
            try:
                page = int(fields.get('page', '0'))
            except ValueError:
                page = 0
            
            excerpt = SourceExcerpt(
                file=fields.get('file', ''),
                file_id=fields.get('file_id', ''),
                page=page,
                text=text,
                paragraph_ref=fields.get('paragraph_ref', ''),
            )
            
            # Index by different keys
            key = (fields.get('file', ''), page)
            self.pages[key] = excerpt
            
            file_id = fields.get('file_id', '')
            if file_id:
                if file_id not in self.by_file_id:
                    self.by_file_id[file_id] = []
                self.by_file_id[file_id].append(excerpt)
            
            para_ref = fields.get('paragraph_ref', '')
            if para_ref:
                self.by_paragraph_ref[para_ref] = excerpt
    
    def _parse_citation_fields(self, citation_text: str) -> Dict[str, str]:
        """Parse citation text into fields."""
        fields = {}
        
        patterns = {
            'file': r'file:\s*([^,\n]+)',
            'page': r'page:\s*([^,\n]+)',
            'file_id': r'file_id:\s*([^,\n]+)',
            'paragraph_ref': r'paragraph_ref:\s*([^,\n]+)',
            'bookmark': r'bookmark:\s*([^,\n]+)',
        }
        
        for field, pattern in patterns.items():
            match = re.search(pattern, citation_text, re.IGNORECASE)
            if match:
                fields[field] = match.group(1).strip()
        
        return fields
    
    def get_excerpt(self, file: str, page: int) -> Optional[str]:
        """
        Get source text for a given file and page.
        
        Args:
            file: Source file name
            page: Page number
            
        Returns:
            Source text excerpt or None if not found
        """
        key = (file, page)
        excerpt = self.pages.get(key)
        return excerpt.text if excerpt else None
    
    def get_by_file_id(self, file_id: str, page: Optional[int] = None) -> Optional[str]:
        """
        Get source text by file ID.
        
        Args:
            file_id: The file_id from citation
            page: Optional page number to filter
            
        Returns:
            Source text or None
        """
        excerpts = self.by_file_id.get(file_id, [])
        if not excerpts:
            return None
        
        if page is not None:
            for excerpt in excerpts:
                if excerpt.page == page:
                    return excerpt.text
        
        # Return first excerpt if no page specified
        return excerpts[0].text if excerpts else None
    
    def get_by_paragraph_ref(self, paragraph_ref: str) -> Optional[str]:
        """
        Get source text by paragraph reference.
        
        Args:
            paragraph_ref: The paragraph_ref from citation
            
        Returns:
            Source text or None
        """
        excerpt = self.by_paragraph_ref.get(paragraph_ref)
        return excerpt.text if excerpt else None
    
    def search(self, query: str, limit: int = 5) -> List[SourceExcerpt]:
        """
        Search for text in source index.
        
        Args:
            query: Text to search for
            limit: Maximum results to return
            
        Returns:
            List of matching excerpts
        """
        results = []
        query_lower = query.lower()
        
        for excerpt in self.pages.values():
            if query_lower in excerpt.text.lower():
                results.append(excerpt)
                if len(results) >= limit:
                    break
        
        return results
    
    def __len__(self) -> int:
        """Return number of indexed pages."""
        return len(self.pages)
