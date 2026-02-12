"""
General helper utilities
"""
from datetime import datetime, timedelta
from typing import Any, Dict
import json


def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string

    Args:
        dt: Datetime object
        format: Datetime format string

    Returns:
        Formatted datetime string
    """
    return dt.strftime(format)


def calculate_time_ago(dt: datetime) -> str:
    """
    Calculate human-readable time ago string

    Args:
        dt: Datetime object

    Returns:
        Time ago string (e.g., "2 hours ago")
    """
    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


def to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case to camelCase

    Args:
        snake_str: Snake case string

    Returns:
        Camel case string
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def to_snake_case(camel_str: str) -> str:
    """
    Convert camelCase to snake_case

    Args:
        camel_str: Camel case string

    Returns:
        Snake case string
    """
    import re
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', camel_str).lower()


def serialize_dict(data: Dict[str, Any]) -> str:
    """
    Serialize dictionary to JSON string

    Args:
        data: Dictionary to serialize

    Returns:
        JSON string
    """
    return json.dumps(data, default=str)


def deserialize_dict(json_str: str) -> Dict[str, Any]:
    """
    Deserialize JSON string to dictionary

    Args:
        json_str: JSON string

    Returns:
        Dictionary
    """
    return json.loads(json_str)
