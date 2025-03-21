#!/usr/bin/env python3
"""
Utility functions for the AI Container Manager
"""
import re

def validate_container_identifier(identifier):
    """
    Validate container identifier format to prevent injection
    
    Args:
        identifier (str): The container identifier to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Only allow alphanumeric chars, dashes and underscores
    if not isinstance(identifier, str):
        return False
    if not re.match(r'^[a-zA-Z0-9_\-]+$', identifier):
        return False
    return True
