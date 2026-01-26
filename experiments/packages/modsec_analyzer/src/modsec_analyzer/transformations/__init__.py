"""
Transformations layer - Apply domain transformations to output formats.

This module handles converting domain transformations back to
ModSecurity configuration format.
"""

from .msc_applier import MscApplier

__all__ = ["MscApplier"]
