from django import template

register = template.Library()

@register.filter
def format_duration(milliseconds):
    """
    Convierte milisegundos a formato M:SS o H:MM:SS
    """
    if not milliseconds or milliseconds == 0:
        return "0:00"
    
    try:
        total_seconds = int(milliseconds) // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    except (ValueError, TypeError):
        return "0:00"