"""
Markdown Parser for extracting structured data from output.

This module parses the output markdown into structured
sections and entries for validation.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Entry:
    """Represents a single entry in the output."""
    header: str
    content: str
    citations: List[str] = field(default_factory=list)
    line_number: int = 0
    
    # Parsed fields
    date: Optional[str] = None
    provider: Optional[str] = None
    facility: Optional[str] = None


@dataclass
class Section:
    """Represents a section in the output."""
    name: str
    level: int  # 1 for #, 2 for ##, 3 for ###
    entries: List[Entry] = field(default_factory=list)
    subsections: List['Section'] = field(default_factory=list)
    line_number: int = 0


class MarkdownParser:
    """
    Parse output markdown into structured sections and entries.
    """
    
    def __init__(self, output_md: str):
        self.output_md = output_md
        self.lines = output_md.split('\n')
        self.sections: List[Section] = []
    
    def parse(self) -> List[Section]:
        """
        Parse the markdown into sections.
        
        Returns:
            List of Section objects
        """
        self.sections = []
        current_section = None
        current_subsection = None
        current_entry = None
        entry_lines = []
        
        for i, line in enumerate(self.lines):
            stripped = line.strip()
            
            # Check for section headers
            if stripped.startswith('# ') and not stripped.startswith('## '):
                # Main section
                if current_section:
                    self._finalize_entry(current_entry, entry_lines, current_subsection or current_section)
                    self.sections.append(current_section)
                
                current_section = Section(
                    name=stripped[2:].strip(),
                    level=1,
                    line_number=i + 1,
                )
                current_subsection = None
                current_entry = None
                entry_lines = []
            
            elif stripped.startswith('## '):
                # Section level 2
                if current_entry:
                    self._finalize_entry(current_entry, entry_lines, current_subsection or current_section)
                
                if current_section is None:
                    current_section = Section(name="Root", level=0)
                
                section = Section(
                    name=stripped[3:].strip().rstrip(':'),
                    level=2,
                    line_number=i + 1,
                )
                current_section.subsections.append(section)
                current_subsection = section
                current_entry = None
                entry_lines = []
            
            elif stripped.startswith('### '):
                # Subsection level 3
                if current_entry:
                    self._finalize_entry(current_entry, entry_lines, current_subsection or current_section)
                
                section = Section(
                    name=stripped[4:].strip(),
                    level=3,
                    line_number=i + 1,
                )
                if current_subsection:
                    current_subsection.subsections.append(section)
                elif current_section:
                    current_section.subsections.append(section)
                
                current_entry = None
                entry_lines = []
            
            elif stripped.startswith('**<u>'):
                # Entry header
                if current_entry:
                    self._finalize_entry(current_entry, entry_lines, current_subsection or current_section)
                
                current_entry = Entry(
                    header=stripped,
                    content="",
                    line_number=i + 1,
                )
                # Parse date from header
                date_match = re.search(r'\d{2}/\d{2}/\d{2,4}', stripped)
                if date_match:
                    current_entry.date = date_match.group(0)
                
                entry_lines = [line]
            
            elif stripped.startswith('<!--') and 'Source:' in stripped:
                # Citation
                if current_entry:
                    current_entry.citations.append(stripped)
            
            elif current_entry:
                # Continue entry content
                entry_lines.append(line)
        
        # Finalize last entry and section
        if current_entry:
            self._finalize_entry(current_entry, entry_lines, current_subsection or current_section)
        if current_section:
            self.sections.append(current_section)
        
        return self.sections
    
    def _finalize_entry(
        self, 
        entry: Optional[Entry], 
        lines: List[str],
        section: Optional[Section]
    ) -> None:
        """Finalize an entry and add to section."""
        if entry is None or section is None:
            return
        
        # Combine lines into content
        content_lines = []
        for line in lines:
            if not line.strip().startswith('<!--'):
                content_lines.append(line)
        
        entry.content = '\n'.join(content_lines).strip()
        section.entries.append(entry)
    
    def get_all_entries(self) -> List[Entry]:
        """Get all entries from all sections."""
        entries = []
        
        def collect(sections: List[Section]):
            for section in sections:
                entries.extend(section.entries)
                collect(section.subsections)
        
        collect(self.sections)
        return entries
    
    def get_entries_by_section(self, section_name: str) -> List[Entry]:
        """Get entries for a specific section."""
        def find(sections: List[Section]) -> List[Entry]:
            for section in sections:
                if section.name.upper() == section_name.upper():
                    return section.entries
                result = find(section.subsections)
                if result:
                    return result
            return []
        
        return find(self.sections)
    
    def count_entries(self) -> Dict[str, int]:
        """Count entries per section."""
        counts = {}
        
        def count(sections: List[Section], prefix: str = ""):
            for section in sections:
                name = f"{prefix}{section.name}" if prefix else section.name
                if section.entries:
                    counts[name] = len(section.entries)
                count(section.subsections, f"{name} > ")
        
        count(self.sections)
        return counts


def parse_output(output_md: str) -> List[Section]:
    """
    Convenience function to parse output markdown.
    
    Args:
        output_md: Output markdown string
        
    Returns:
        List of Section objects
    """
    parser = MarkdownParser(output_md)
    return parser.parse()
