from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from api.dependencies import get_current_user, get_parser_service
from services.auth.schemas import UserInfo
from services.parser.schemas import ParseRequest, ParseResponse, ParseStatusResponse
from services.parser.service import ParserService
from shared.schemas import SuccessResponse

router = APIRouter(prefix="/parser", tags=["Parser"])


@router.post(
    "/parse/{id}",
    response_model=ParseResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def parse_configuration(
    id: int,
    background_tasks: BackgroundTasks,
    request: ParseRequest = ParseRequest(),
    current_user: UserInfo = Depends(get_current_user),
    parser: ParserService = Depends(get_parser_service),
):
    """
    Start parsing a configuration.

    - **force_reparse**: parse even if a parse is already running

    Returns 202 immediately with `parsing_status: "parsing"`. Parsing a large
    configuration takes minutes — poll `GET /parser/status/{id}` for the outcome.
    """
    try:
        return parser.parse_configuration(id, background_tasks, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/status/{id}", response_model=ParseStatusResponse)
async def get_parsing_status(
    id: int,
    current_user: UserInfo = Depends(get_current_user),
    parser: ParserService = Depends(get_parser_service),
):
    """
    Get parsing status for a configuration.

    `parsing_status` is one of `not_parsed`, `parsing`, `parsed`, `error`.
    The `total_*` counts are populated only once the status is `parsed`.
    """
    try:
        return parser.get_parsing_status(id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/reparse/{id}",
    response_model=ParseResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reparse_configuration(
    id: int,
    background_tasks: BackgroundTasks,
    current_user: UserInfo = Depends(get_current_user),
    parser: ParserService = Depends(get_parser_service),
):
    """
    Clear existing parsed data and parse again.

    Use after editing configuration files, which resets `parsing_status` to
    `not_parsed`. Returns 202; poll `GET /parser/status/{id}`.
    """
    try:
        return parser.reparse_configuration(id, background_tasks)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/data/{id}", response_model=SuccessResponse)
async def clear_parsed_data(
    id: int,
    current_user: UserInfo = Depends(get_current_user),
    parser: ParserService = Depends(get_parser_service),
):
    """
    Drop a configuration's parsed data from Neo4j and PostgreSQL.

    The configuration itself and its files are kept; `parsing_status` returns to
    `not_parsed`.
    """
    try:
        parser.clear_parsed_data(id)
        return SuccessResponse(
            message=f"Parsed data for configuration {id} cleared successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
