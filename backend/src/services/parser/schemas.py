from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# Request Schemas
class ParseRequest(BaseModel):
    """Options for a parse run"""
    force_reparse: bool = Field(
        default=False,
        description="Parse even if the configuration is already parsed or currently parsing",
    )


# Response Schemas
class ParseResponse(BaseModel):
    """
    Returned on accept (202). The parse has been scheduled, not finished — poll
    /parser/status/{id} for the outcome.
    """
    configuration_id: int
    parsing_status: str  # "parsing" on accept
    parsing_error: Optional[str] = None
    parsed_at: Optional[datetime] = None  # last successful parse, if any

    class Config:
        from_attributes = True


class ParseStatusResponse(BaseModel):
    """Poll target. Counts are populated only once parsing_status == 'parsed'."""
    configuration_id: int
    parsing_status: str  # not_parsed | parsing | parsed | error
    parsing_error: Optional[str] = None
    parsed_at: Optional[datetime] = None
    total_directives: Optional[int] = None
    total_symbols: Optional[int] = None
    total_macros: Optional[int] = None
    total_macro_calls: Optional[int] = None

    class Config:
        from_attributes = True
