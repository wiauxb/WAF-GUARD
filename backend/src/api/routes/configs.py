from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import Optional, List
from services.configmanager.service import ConfigManagerService
from services.configmanager.schemas import (
    ConfigurationUploadRequest,
    ConfigurationResponse,
    ConfigurationUpdateRequest,
    ConfigTreeResponse,
    FileUpdateRequest
)
from services.auth.schemas import UserInfo
from shared.schemas import SuccessResponse
from api.dependencies import get_current_user, get_config_manager

router = APIRouter(prefix="/configurations", tags=["configurations"])

@router.post("", response_model=ConfigurationResponse, status_code=status.HTTP_201_CREATED)
async def upload_configuration(
    file: UploadFile = File(..., description="Configuration zip file"),
    name: str = Form(..., min_length=1, max_length=255),
    description: Optional[str] = Form(None, max_length=2000),
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    Upload a new configuration.
    
    - **file**: Configuration zip file (required)
    - **name**: Unique configuration name (required)
    - **description**: Optional description
    
    Process:
    1. Validates and stores zip file
    2. Extracts contents
    3. Generates dump via WAF service
    4. Creates database record
    
    Returns configuration metadata with status 'not_parsed'.
    """
    try:
        request = ConfigurationUploadRequest(name=name, description=description)
        return await config_manager.upload_configuration(current_user.id, file, request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except IOError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("", response_model=List[ConfigurationResponse])
async def list_configurations(
    order_by: str = Query("created_at", regex="^(created_at|name|parsed_at)$"),
    order_desc: bool = Query(True),
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    List all configurations.
    
    - **order_by**: Field to sort by (created_at, name, parsed_at)
    - **order_desc**: Sort descending if true (default: true)
    
    Returns list of all configurations sorted as requested.
    """
    return config_manager.get_all_configurations(order_by, order_desc)

@router.get("/{id}", response_model=ConfigurationResponse)
async def get_configuration(
    id: int,
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    Get configuration by ID.
    
    Returns full configuration metadata.
    """
    try:
        return config_manager.get_configuration_by_id(id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/by-name/{name}", response_model=ConfigurationResponse)
async def get_configuration_by_name(
    name: str,
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    Get configuration by name.
    
    Returns full configuration metadata.
    """
    try:
        return config_manager.get_configuration_by_name(name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{id}", response_model=ConfigurationResponse)
async def update_configuration(
    id: int,
    updates: ConfigurationUpdateRequest,
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    Update configuration metadata.
    
    - **name**: New name (optional)
    - **description**: New description (optional)
    
    At least one field must be provided.
    """
    try:
        return config_manager.update_configuration_metadata(id, updates)
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        elif "already exists" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{id}", response_model=SuccessResponse)
async def delete_configuration(
    id: int,
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    Delete a configuration.
    
    Deletes:
    - Configuration files (zip, dump, extracted)
    - Database record
    - All associated parsing data (cascaded)
    
    This operation cannot be undone.
    """
    try:
        config_manager.delete_configuration(id)
        return SuccessResponse(message=f"Configuration {id} deleted successfully")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{id}/tree", response_model=ConfigTreeResponse)
async def get_configuration_tree(
    id: int,
    path: str = Query("/", description="Path within configuration"),
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    Get configuration file tree or file content.
    
    - **path**: Path within configuration (default: root "/")
    
    If path is a directory: Returns list of files/folders
    If path is a file: Returns file content
    """
    try:
        return config_manager.get_configuration_tree(id, path)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.put("/{id}/files/{file_path:path}", response_model=SuccessResponse)
async def update_file_content(
    id: int,
    file_path: str,
    request: FileUpdateRequest,
    current_user: UserInfo = Depends(get_current_user),
    config_manager: ConfigManagerService = Depends(get_config_manager)
):
    """
    Update configuration file content.
    
    - **content**: New file content
    
    Note: Sets configuration parsing_status to 'not_parsed'.
    You'll need to re-parse the configuration after editing.
    """
    try:
        config_manager.update_file_content(id, file_path, request.content)
        return SuccessResponse(
            message=f"File '{file_path}' updated successfully. Configuration marked for re-parsing."
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))