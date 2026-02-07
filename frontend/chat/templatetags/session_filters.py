# Custom template filters for session formatting

from django import template
import re

register = template.Library()


@register.filter
def format_session_name(name):
    """
    Format session names for display.
    
    - User-defined names: display as-is
    - Default batch names (batch_tts_eval_HH_MM_SS_DD_MM_YYYY): "Batch Session HH:MM DD/MM/YYYY"
    - Default single names (tts_eval_HH_MM_SS_DD_MM_YYYY): "Single Session HH:MM DD/MM/YYYY"
    """
    if not name:
        return "Unnamed Session"
    
    # Check for batch session default format: batch_tts_eval_HH_MM_SS_DD_MM_YYYY
    batch_pattern = r'^batch_tts_eval_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{4})$'
    batch_match = re.match(batch_pattern, name)
    if batch_match:
        hour, minute, second, day, month, year = batch_match.groups()
        return f"Batch Session {hour}:{minute} {day}/{month}/{year}"
    
    # Check for single session default format: tts_eval_HH_MM_SS_DD_MM_YYYY
    single_pattern = r'^tts_eval_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{4})$'
    single_match = re.match(single_pattern, name)
    if single_match:
        hour, minute, second, day, month, year = single_match.groups()
        return f"Single Session {hour}:{minute} {day}/{month}/{year}"
    
    # User-defined name - return as-is
    return name
