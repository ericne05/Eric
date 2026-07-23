"""
Browser Memory Pipeline.
Transforms HTML into semantic Markdown blocks.
"""
from typing import List, Dict, Any
import markdownify

class BrowserMemoryPipeline:
    def __init__(self):
        pass
        
    def process(self, html: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extracts HTML -> Cleans -> Chunks -> Adds Metadata.
        """
        # 1. HTML -> Markdown
        md_text = markdownify.markdownify(html, heading_style="ATX")
        
        # 2. Semantic Chunking (Simplistic header chunking for now)
        chunks = []
        current_chunk = []
        current_header = ""
        
        for line in md_text.splitlines():
            if line.startswith("#"):
                if current_chunk:
                    chunks.append({
                        "header": current_header,
                        "content": "\n".join(current_chunk).strip(),
                        "metadata": metadata
                    })
                current_header = line.strip()
                current_chunk = []
            else:
                if line.strip():
                    current_chunk.append(line)
                    
        # Append last chunk
        if current_chunk:
            chunks.append({
                "header": current_header,
                "content": "\n".join(current_chunk).strip(),
                "metadata": metadata
            })
            
        return chunks
