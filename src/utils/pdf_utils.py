"""Utilities for enhanced PDF text extraction."""
import re
from typing import Any

def extract_interleaved_elements(page) -> list[dict[str, Any]]:
    """Extract words and interactive values with their coordinates."""
    # 1. Get words
    words = page.extract_words()
    
    # 2. Get annots with values
    annots = []
    for a in (page.annots or []):
        data = a.get('data', a)
        v = data.get('V')
        if v:
            try:
                if isinstance(v, bytes):
                    if b'\xfe\xff' in v:
                        v_str = v.decode('utf-16')
                    else:
                        v_str = v.decode('utf-8', errors='ignore')
                else:
                    v_str = str(v)
            except Exception:
                v_str = str(v)
                
            rect = data.get('Rect', [0,0,0,0])
            annots.append({
                'text': v_str.strip(),
                'x0': rect[0],
                'x1': rect[2],
                'top': page.height - rect[3],
                'bottom': page.height - rect[1]
            })
    
    # 3. Combine
    elements = []
    for w in words:
        elements.append({
            'type': 'text',
            'text': w['text'],
            'x0': w['x0'],
            'x1': w['x1'],
            'top': w['top'],
            'bottom': w['bottom']
        })
    for a in annots:
        elements.append({
            'type': 'value',
            'text': a['text'],
            'x0': a['x0'],
            'x1': a['x1'],
            'top': a['top'],
            'bottom': a['bottom']
        })
    
    # Sort primarily by row and then by column
    elements.sort(key=lambda e: (round(e['top']), e['x0']))
    return elements


def extract_interleaved_text(page) -> str:
    """Legacy wrapper for simple text stream extraction."""
    elements = extract_interleaved_elements(page)
    lines = []
    current_line = []
    last_snapped_y = -1
    
    for e in elements:
        snapped_y = round(e['top'] / 2) * 2
        text = f"[[VAL:{e['text']}]]" if e['type'] == 'value' else e['text']
        if last_snapped_y != -1 and snapped_y != last_snapped_y:
            lines.append(" ".join(current_line))
            current_line = []
        current_line.append(text)
        last_snapped_y = snapped_y
    
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)
