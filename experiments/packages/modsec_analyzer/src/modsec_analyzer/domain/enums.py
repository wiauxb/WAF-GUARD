"""
Domain enumerations for ModSecurity concepts.
"""

from enum import Enum, auto


class Phase(Enum):
    """ModSecurity processing phases."""
    REQUEST_HEADERS = 1
    REQUEST_BODY = 2
    RESPONSE_HEADERS = 3
    RESPONSE_BODY = 4
    LOGGING = 5


class ActionType(Enum):
    """Types of actions in ModSecurity rules."""
    # Disruptive actions
    ALLOW = auto()
    BLOCK = auto()
    DENY = auto()
    DROP = auto()
    PASS = auto()
    PAUSE = auto()
    PROXY = auto()
    REDIRECT = auto()

    # Non-disruptive actions
    CAPTURE = auto()
    CHAIN = auto()
    CTL = auto()
    EXEC = auto()
    EXPIREVAR = auto()
    ID = auto()
    INITCOL = auto()
    LOG = auto()
    LOGDATA = auto()
    MATURITY = auto()
    MSG = auto()
    MULTIMATCHED = auto()
    NOLOG = auto()
    NOAUDITLOG = auto()
    PHASE = auto()
    REV = auto()
    SANITISEMATCHED = auto()
    SETENV = auto()
    SETSID = auto()
    SETUID = auto()
    SETVAR = auto()
    SEVERITY = auto()
    SKIP = auto()
    SKIPAFTER = auto()
    STATUS = auto()
    TAG = auto()
    VER = auto()
    XMLNS = auto()

    # Transformation actions (t:)
    TRANSFORMATION = auto()


class ActionGroup(Enum):
    """Logical groupings of actions by their effect."""
    DISRUPTIVE = auto()      # Actions that affect request flow
    FLOW = auto()            # Actions that control rule flow
    METADATA = auto()        # Actions that add metadata (id, msg, tag, etc.)
    VARIABLE = auto()        # Actions that manipulate variables
    LOGGING = auto()         # Actions related to logging
    DATA = auto()            # Actions that capture/transform data
