from typing import List, Dict, Any, Optional

def truncate_list(items: List[Any], max_items: int = 20) -> tuple[List[Any], int]:
    """Truncates a list to max_items and returns the truncated list and the number of remaining items."""
    if len(items) <= max_items:
        return items, 0
    return items[:max_items], len(items) - max_items

def render_list(
    title: str,
    items: List[Dict[str, Any]],
    display_field: str = "name",
    secondary_field: Optional[str] = None,
    empty_message: str = "No items found.",
    max_items: int = 20
) -> str:
    """Renders a markdown list from structured data."""
    if not items:
        return empty_message
        
    truncated, remaining = truncate_list(items, max_items)
    
    lines = [f"{title}\n"]
    
    for item in truncated:
        primary = item.get(display_field, "Unknown")
        if secondary_field and item.get(secondary_field):
            lines.append(f"• **{primary}** - {item.get(secondary_field)}")
        else:
            lines.append(f"• **{primary}**")
            
    if remaining > 0:
        lines.append(f"\n_...and {remaining} more._")
        
    return "\n".join(lines)

def render_entity(title: str, data: Dict[str, Any], fields: List[str]) -> str:
    """Renders a markdown key-value entity representation."""
    if not data:
        return f"Could not find {title}."
        
    lines = [f"### {title}\n"]
    for field in fields:
        val = data.get(field)
        if val is not None:
            # Format field name: 'assignee_id' -> 'Assignee Id'
            label = field.replace("_", " ").title()
            lines.append(f"- **{label}:** {val}")
            
    return "\n".join(lines)

def render_success(action: str, message: str = "Operation completed successfully.") -> str:
    return f"✅ **{action}**: {message}"

def render_failure(action: str, message: str = "Operation failed.") -> str:
    return f"❌ **{action}**: {message}"
