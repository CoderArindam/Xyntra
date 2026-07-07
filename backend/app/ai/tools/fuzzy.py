"""
Centralized fuzzy entity matching for AI tools.
Normalizes and fuzzy-matches board names, user names, task titles, column names.
"""
import re
from typing import Any, Callable, Dict, List, Optional, Tuple


def normalize(text: str) -> str:
    """Strip, lowercase, remove dashes/underscores/extra spaces."""
    text = text.strip().lower()
    text = re.sub(r'[-_]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def fuzzy_score(query: str, candidate: str) -> float:
    """Simple fuzzy similarity: exact > contains > starts_with > partial token overlap."""
    q = normalize(query)
    c = normalize(candidate)
    
    if not q or not c:
        return 0.0
    
    if q == c:
        return 1.0
    
    # Also compare with all spaces removed (handles 'back end' vs 'backend')
    q_collapsed = q.replace(" ", "")
    c_collapsed = c.replace(" ", "")
    if q_collapsed == c_collapsed:
        return 0.95
    
    if c.startswith(q) or q.startswith(c):
        return 0.9
    if q in c or c in q:
        return 0.8
    if q_collapsed in c_collapsed or c_collapsed in q_collapsed:
        return 0.75

    q_tokens = set(q.split())
    c_tokens = set(c.split())
    if q_tokens and c_tokens:
        overlap = q_tokens & c_tokens
        if overlap:
            return 0.6 * len(overlap) / max(len(q_tokens), len(c_tokens))
    
    return 0.0


def find_best_match(
    query: str,
    candidates: List[Any],
    key_fn: Callable[[Any], str],
    threshold: float = 0.5
) -> Tuple[Optional[Any], float]:
    """Find the best fuzzy match from a list of candidates.
    
    Returns (best_match, score). Returns (None, 0.0) if no match above threshold.
    """
    best = None
    best_score = 0.0
    
    for candidate in candidates:
        name = key_fn(candidate)
        score = fuzzy_score(query, name)
        if score > best_score:
            best_score = score
            best = candidate
    
    if best_score >= threshold:
        return best, best_score
    return None, 0.0


def find_all_matches(
    query: str,
    candidates: List[Any],
    key_fn: Callable[[Any], str],
    threshold: float = 0.5
) -> List[Tuple[Any, float]]:
    """Find all fuzzy matches above threshold, sorted by score descending."""
    results = []
    for candidate in candidates:
        name = key_fn(candidate)
        score = fuzzy_score(query, name)
        if score >= threshold:
            results.append((candidate, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def resolve_board(query: str, boards: list) -> Optional[Any]:
    """Resolve a board name query to a board object with fuzzy matching."""
    match, score = find_best_match(
        query, boards,
        key_fn=lambda b: b.name if hasattr(b, 'name') else b.get('name', ''),
        threshold=0.5
    )
    return match


def resolve_user(query: str, users: list) -> Optional[dict]:
    """Resolve a user name/email query to a user dict with fuzzy matching."""
    best = None
    best_score = 0.0
    
    q = normalize(query)
    
    for u in users:
        first = u.get("first_name") or ""
        last = u.get("last_name") or ""
        email = u.get("email") or ""
        full_name = f"{first} {last}".strip()
        
        # Check multiple fields
        for field in [first, last, full_name, email]:
            score = fuzzy_score(query, field)
            if score > best_score:
                best_score = score
                best = u
        
        # Special: "me" keyword handled upstream, not here
    
    if best_score >= 0.5:
        return best
    return None


def resolve_column(query: str, columns: list) -> Optional[Any]:
    """Resolve a status/column query to a column object with fuzzy matching."""
    q = normalize(query)
    
    # First try exact match on name or column_type
    for col in columns:
        col_name = normalize(col.name if hasattr(col, 'name') else col.get('name', ''))
        col_type = normalize(col.column_type if hasattr(col, 'column_type') else col.get('column_type', ''))
        if q == col_name or q == col_type:
            return col
    
    # Then fuzzy match on name
    match, score = find_best_match(
        query, columns,
        key_fn=lambda c: c.name if hasattr(c, 'name') else c.get('name', ''),
        threshold=0.5
    )
    return match
