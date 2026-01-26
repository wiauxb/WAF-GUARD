"""
Parsing layer - Convert external formats to domain models.

This module handles parsing ModSecurity configurations using
msc_pyparser and converting them to domain objects.
"""

from .msc_adapter import parse_file

__all__ = ["parse_file"]
