from typing import List, Dict, Any
import re


def split_text_into_chunks(text: str, max_tokens: int = 4000) -> List[str]:
    """
    Split text into chunks of approximately max_tokens tokens
    Using a simple approximation: 1 token ≈ 4 characters
    
    Args:
        text: The text to split
        max_tokens: Maximum number of tokens per chunk
        
    Returns:
        List of text chunks
    """
    # Convert max tokens to approximate character count
    max_chars = max_tokens * 4
    
    # Split text into paragraphs
    paragraphs = text.split("\n\n")
    
    chunks = []
    current_chunk = ""
    current_chunk_size = 0
    
    for paragraph in paragraphs:
        paragraph_size = len(paragraph)
        
        if current_chunk_size + paragraph_size > max_chars:
            # Current chunk is full, add it to chunks and start a new one
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = paragraph
            current_chunk_size = paragraph_size
        else:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
            current_chunk_size += paragraph_size
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def extract_metadata_from_text(text: str) -> Dict[str, List[str]]:
    """
    Extract metadata from text using regex patterns
    
    Args:
        text: The text to extract metadata from
        
    Returns:
        Dictionary of extracted metadata
    """
    metadata = {
        "dates": [],
        "links": [],
        "references": [],
        "people": [],
        "organizations": [],
        "key_topics": [],
        "other_info": []
    }
    
    # Extract dates (common formats)
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY or DD-MM-YYYY
        r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4}\b',  # Month DD, YYYY
        r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s+\d{4}\b'  # DD Month YYYY
    ]
    
    for pattern in date_patterns:
        dates = re.findall(pattern, text, re.IGNORECASE)
        metadata["dates"].extend(dates)
    
    # Extract links/URLs
    link_pattern = r'https?://\S+|www\.\S+'
    links = re.findall(link_pattern, text)
    metadata["links"] = list(set(links))
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    metadata["other_info"].extend(emails)
    
    # Extract references (simple pattern, can be improved)
    reference_patterns = [
        r'(?:reference|ref|cited in|source):\s+([^,.;]+)',
        r'(?:book|article|paper|publication|journal):\s+([^,.;]+)'
    ]
    
    for pattern in reference_patterns:
        references = re.findall(pattern, text, re.IGNORECASE)
        metadata["references"].extend(references)
    
    # Remove duplicates
    for key in metadata:
        metadata[key] = list(set(metadata[key]))
    
    return metadata


def format_summary(summary: str, metadata: Dict[str, List[str]]) -> str:
    """
    Format the final summary with metadata
    
    Args:
        summary: The summary text
        metadata: Dictionary of extracted metadata
        
    Returns:
        Formatted summary with metadata section
    """
    formatted_summary = summary
    
    # Add metadata section if there's any metadata
    has_metadata = any(len(items) > 0 for items in metadata.values())
    
    if has_metadata:
        formatted_summary += "\n\n## Additional Information\n"
        
        if metadata["dates"]:
            formatted_summary += "\n### Dates Mentioned\n"
            for date in metadata["dates"]:
                formatted_summary += f"- {date}\n"
        
        if metadata["links"]:
            formatted_summary += "\n### Links/URLs\n"
            for link in metadata["links"]:
                formatted_summary += f"- {link}\n"
        
        if metadata["references"]:
            formatted_summary += "\n### References\n"
            for ref in metadata["references"]:
                formatted_summary += f"- {ref}\n"
        
        if metadata["people"]:
            formatted_summary += "\n### People Mentioned\n"
            for person in metadata["people"]:
                formatted_summary += f"- {person}\n"
        
        if metadata["organizations"]:
            formatted_summary += "\n### Organizations Mentioned\n"
            for org in metadata["organizations"]:
                formatted_summary += f"- {org}\n"
        
        if metadata["key_topics"]:
            formatted_summary += "\n### Key Topics\n"
            for topic in metadata["key_topics"]:
                formatted_summary += f"- {topic}\n"
        
        if metadata["other_info"]:
            formatted_summary += "\n### Other Relevant Information\n"
            for info in metadata["other_info"]:
                formatted_summary += f"- {info}\n"
    
    return formatted_summary
