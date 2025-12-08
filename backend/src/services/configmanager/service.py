from sqlalchemy.orm import Session
from fastapi import UploadFile
from .repository import ConfigurationRepository
from .storage import ConfigFileStorage
from .schemas import (
    ConfigurationUploadRequest,
    ConfigurationResponse,
    ConfigurationUpdateRequest,
    ConfigTreeResponse
)
from services.waf.service import WAFService
from shared.config import settings
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConfigManagerService:
    """Business logic for configuration management"""
    
    def __init__(self, db: Session):
        self.db = db
        self.config_repo = ConfigurationRepository(db)
        self.storage = ConfigFileStorage(settings.STORAGE_ROOT)
        self.waf_service = WAFService()
    
    async def upload_configuration(
        self,
        user_id: int,
        zip_file: UploadFile,
        request: ConfigurationUploadRequest
    ) -> ConfigurationResponse:
        """
        Upload and store a new configuration.

        Process:
        1. Validate name is unique
        2. Create DB record (to get ID)
        3. Store zip and extract files
        4. Generate dump via WAF
        5. Store dump
        6. Update DB record with paths

        Args:
            user_id: User uploading the configuration
            zip_file: Configuration zip file
            request: Upload request data (name, description)

        Returns:
            ConfigurationResponse

        Raises:
            ValueError: If name already exists or validation fails
            IOError: If file storage fails
            RuntimeError: If WAF service fails
        """
        # Check name doesn't exist
        if self.config_repo.name_exists(request.name):
            raise ValueError(f"Configuration name '{request.name}' already exists")

        # Create initial DB record to get ID
        config = self.config_repo.create(
            name=request.name,
            description=request.description,
            file_path="",  # Will update after storage
            file_hash=None,
            file_size=None,
            created_by_user_id=user_id
        )

        try:
            # Store zip and extract
            storage_info = await self.storage.store_zip(config.id, zip_file)
            
            # Generate dump via WAF
            dump_content = self.waf_service.generate_dump(
                storage_info["zip_path"],
                settings.WAF_URL
            )
            
            # Store dump
            dump_path = self.storage.store_dump(config.id, dump_content)
            
            # Update configuration with file info
            config.file_path = storage_info["zip_path"]
            config.file_hash = storage_info["file_hash"]
            config.file_size = storage_info["file_size"]
            self.config_repo.update(config)
            
            logger.info(f"Uploaded configuration {config.id}: {request.name}")
            
            return ConfigurationResponse.from_orm(config)
        
        except Exception as e:
            # Rollback: delete files and DB record
            logger.error(f"Failed to upload configuration: {e}")
            try:
                self.storage.delete_config_files(config.id)
            except:
                pass
            self.config_repo.delete(config)
            raise
    
    def get_all_configurations(
        self,
        order_by: str = "created_at",
        order_desc: bool = True
    ) -> List[ConfigurationResponse]:
        """
        Get all configurations.
        
        Args:
            order_by: Field to sort by (created_at, name, parsed_at)
            order_desc: Sort descending if True
        
        Returns:
            List of ConfigurationResponse
        """
        configs = self.config_repo.get_all(order_by, order_desc)
        return [ConfigurationResponse.from_orm(c) for c in configs]
    
    def get_configuration_by_id(self, configuration_id: int) -> ConfigurationResponse:
        """
        Get configuration by ID.
        
        Args:
            configuration_id: Configuration ID
        
        Returns:
            ConfigurationResponse
        
        Raises:
            ValueError: If configuration not found
        """
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")
        
        return ConfigurationResponse.from_orm(config)
    
    def get_configuration_by_name(self, name: str) -> ConfigurationResponse:
        """
        Get configuration by name.
        
        Args:
            name: Configuration name
        
        Returns:
            ConfigurationResponse
        
        Raises:
            ValueError: If configuration not found
        """
        config = self.config_repo.get_by_name(name)
        if not config:
            raise ValueError(f"Configuration '{name}' not found")
        
        return ConfigurationResponse.from_orm(config)
    
    def update_configuration_metadata(
        self,
        configuration_id: int,
        updates: ConfigurationUpdateRequest
    ) -> ConfigurationResponse:
        """
        Update configuration metadata.
        
        Args:
            configuration_id: Configuration ID
            updates: Fields to update
        
        Returns:
            ConfigurationResponse
        
        Raises:
            ValueError: If configuration not found or name already exists
        """
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")
        
        # Update name if provided
        if updates.name and updates.name != config.name:
            if self.config_repo.name_exists(updates.name, exclude_id=configuration_id):
                raise ValueError(f"Configuration name '{updates.name}' already exists")
            config.name = updates.name
        
        # Update description if provided
        if updates.description is not None:
            config.description = updates.description
        
        # Update timestamp
        config.updated_at = datetime.utcnow()
        
        self.config_repo.update(config)
        
        logger.info(f"Updated configuration {configuration_id}")
        
        return ConfigurationResponse.from_orm(config)
    
    def delete_configuration(self, configuration_id: int) -> bool:
        """
        Delete configuration and all associated files.
        
        Args:
            configuration_id: Configuration ID
        
        Returns:
            True on success
        
        Raises:
            ValueError: If configuration not found
        """
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")
        
        # Delete files
        self.storage.delete_config_files(configuration_id)
        
        # Delete DB record (cascades to parsing data)
        self.config_repo.delete(config)
        
        logger.info(f"Deleted configuration {configuration_id}")
        
        return True
    
    def get_dump_path(self, configuration_id: int) -> str:
        """
        Get filesystem path to dump file (for ParserService).
        
        Args:
            configuration_id: Configuration ID
        
        Returns:
            Path to dump file
        
        Raises:
            ValueError: If configuration not found
            FileNotFoundError: If dump file not found
        """
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")
        
        return self.storage.get_dump_path(configuration_id)
    
    def get_configuration_tree(
        self,
        configuration_id: int,
        path: str = "/"
    ) -> ConfigTreeResponse:
        """
        Get file tree or file content.
        
        Args:
            configuration_id: Configuration ID
            path: Path within configuration (default: root)
        
        Returns:
            ConfigTreeResponse
        
        Raises:
            ValueError: If configuration not found or path invalid
            FileNotFoundError: If path doesn't exist
        """
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")
        
        tree_data = self.storage.get_file_tree(configuration_id, path)
        
        return ConfigTreeResponse(**tree_data)
    
    def update_file_content(
        self,
        configuration_id: int,
        file_path: str,
        content: str
    ) -> bool:
        """
        Update configuration file content.
        
        Sets parsing_status to 'not_parsed' to trigger re-parsing.
        
        Args:
            configuration_id: Configuration ID
            file_path: Relative path to file
            content: New file content
        
        Returns:
            True on success
        
        Raises:
            ValueError: If configuration not found or path invalid
            FileNotFoundError: If file doesn't exist
        """
        config = self.config_repo.get_by_id(configuration_id)
        if not config:
            raise ValueError(f"Configuration with id {configuration_id} not found")
        
        # Update file
        self.storage.update_file_content(configuration_id, file_path, content)
        
        # Mark as needing re-parsing
        config.parsing_status = "not_parsed"
        config.updated_at = datetime.utcnow()
        self.config_repo.update(config)
        
        logger.info(f"Updated file {file_path} in configuration {configuration_id}")
        
        return True