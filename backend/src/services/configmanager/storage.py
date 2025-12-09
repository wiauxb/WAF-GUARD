from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil
import zipfile
import hashlib
import gzip
import io
from fastapi import UploadFile
import logging

logger = logging.getLogger(__name__)

class ConfigFileStorage:
    """Helper class for configuration filesystem operations"""
    
    def __init__(self, storage_root: str):
        self.storage_root = Path(storage_root)
        self.configs_dir = self.storage_root / "configs"
        
        # Ensure storage directories exist
        self.configs_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_config_dir(self, config_id: int) -> Path:
        """Get directory path for a configuration"""
        return self.configs_dir / f"config_{config_id}"
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def store_zip(self, config_id: int, zip_file: UploadFile) -> Dict[str, Any]:
        """
        Store uploaded zip file and extract contents.
        
        Args:
            config_id: Configuration ID
            zip_file: Uploaded zip file
        
        Returns:
            Dict with zip_path, extracted_path, file_hash, file_size
        
        Raises:
            ValueError: If not a valid zip file
            IOError: If storage fails
        """
        config_dir = self._get_config_dir(config_id)
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Store zip file
        zip_path = config_dir / "original.zip"
        
        try:
            # Save uploaded file
            content = await zip_file.read()
            with open(zip_path, "wb") as f:
                f.write(content)
            
            # Verify it's a valid zip
            if not zipfile.is_zipfile(zip_path):
                zip_path.unlink()
                raise ValueError("Uploaded file is not a valid zip file")
            
            # Extract contents
            extracted_path = config_dir / "extracted"
            extracted_path.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extracted_path)
            
            # Calculate hash and size
            file_hash = self._calculate_file_hash(zip_path)
            file_size = zip_path.stat().st_size
            
            logger.info(f"Stored zip for config {config_id}: {file_size} bytes, hash={file_hash[:8]}...")
            
            return {
                "zip_path": str(zip_path),
                "extracted_path": str(extracted_path),
                "file_hash": file_hash,
                "file_size": file_size
            }
        
        except zipfile.BadZipFile:
            if zip_path.exists():
                zip_path.unlink()
            raise ValueError("Invalid or corrupted zip file")
        except Exception as e:
            logger.error(f"Failed to store zip for config {config_id}: {e}")
            raise IOError(f"Failed to store configuration file: {str(e)}")
    
    def store_dump(self, config_id: int, dump_content: bytes) -> str:
        """
        Store configuration dump file (streams and decompresses gzip content to disk).

        Uses chunked decompression to avoid loading entire dump into memory.

        Args:
            config_id: Configuration ID
            dump_content: Gzip-compressed dump file content (binary)

        Returns:
            Path to dump file

        Raises:
            IOError: If storage or decompression fails
        """
        config_dir = self._get_config_dir(config_id)
        dump_path = config_dir / "dump.conf"

        try:
            compressed_size = len(dump_content)

            # Stream decompress in chunks to avoid memory overhead
            with io.BytesIO(dump_content) as compressed_stream:
                with gzip.open(compressed_stream, 'rb') as gz_file:
                    with open(dump_path, "wb") as f:
                        # Copy in 1MB chunks
                        shutil.copyfileobj(gz_file, f, length=1024 * 1024)

            # Get final decompressed size
            decompressed_size = dump_path.stat().st_size
            compression_ratio = (1 - compressed_size / decompressed_size) * 100

            logger.info(
                f"Stored dump for config {config_id}: {dump_path} "
                f"({compressed_size} bytes compressed → {decompressed_size} bytes decompressed, "
                f"{compression_ratio:.1f}% compression)"
            )

            return str(dump_path)

        except gzip.BadGzipFile as e:
            logger.error(f"Invalid gzip data for config {config_id}: {e}")
            raise IOError(f"Failed to decompress dump file: invalid gzip format")

        except Exception as e:
            logger.error(f"Failed to store dump for config {config_id}: {e}")
            raise IOError(f"Failed to store dump file: {str(e)}")
    
    def get_dump_path(self, config_id: int) -> str:
        """
        Get path to dump file.
        
        Args:
            config_id: Configuration ID
        
        Returns:
            Path to dump file
        
        Raises:
            FileNotFoundError: If dump doesn't exist
        """
        config_dir = self._get_config_dir(config_id)
        dump_path = config_dir / "dump.conf"
        
        if not dump_path.exists():
            raise FileNotFoundError(f"Dump file not found for configuration {config_id}")
        
        return str(dump_path)
    
    def get_file_tree(self, config_id: int, relative_path: str = "") -> Dict[str, Any]:
        """
        Get file tree structure or file content.
        
        Args:
            config_id: Configuration ID
            relative_path: Path relative to extracted directory
        
        Returns:
            Dict with tree structure or file content
        
        Raises:
            ValueError: If path is invalid
            FileNotFoundError: If path doesn't exist
        """
        config_dir = self._get_config_dir(config_id)
        extracted_dir = config_dir / "extracted"
        
        if not extracted_dir.exists():
            raise FileNotFoundError(f"Extracted files not found for configuration {config_id}")
        
        # Resolve target path
        target_path = extracted_dir / relative_path.lstrip("/")
        
        # Security: prevent directory traversal
        try:
            target_path = target_path.resolve()
            extracted_dir = extracted_dir.resolve()
            if not str(target_path).startswith(str(extracted_dir)):
                raise ValueError("Invalid path: directory traversal detected")
        except Exception:
            raise ValueError("Invalid path")
        
        if not target_path.exists():
            raise FileNotFoundError(f"Path not found: {relative_path}")
        
        # If file, return content
        if target_path.is_file():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                return {
                    "is_file": True,
                    "path": relative_path,
                    "content": content,
                    "size": target_path.stat().st_size
                }
            except UnicodeDecodeError:
                # Binary file
                return {
                    "is_file": True,
                    "path": relative_path,
                    "content": "[Binary file - cannot display]",
                    "size": target_path.stat().st_size
                }
        
        # If directory, return tree
        children = []
        for item in sorted(target_path.iterdir()):
            children.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })
        
        return {
            "is_file": False,
            "path": relative_path,
            "children": children
        }
    
    def update_file_content(self, config_id: int, file_path: str, content: str) -> bool:
        """
        Update content of a configuration file.
        
        Args:
            config_id: Configuration ID
            file_path: Relative path to file
            content: New file content
        
        Returns:
            True on success
        
        Raises:
            ValueError: If path is invalid or not a file
            FileNotFoundError: If file doesn't exist
        """
        config_dir = self._get_config_dir(config_id)
        extracted_dir = config_dir / "extracted"
        
        target_path = extracted_dir / file_path.lstrip("/")
        
        # Security check
        try:
            target_path = target_path.resolve()
            extracted_dir = extracted_dir.resolve()
            if not str(target_path).startswith(str(extracted_dir)):
                raise ValueError("Invalid path: directory traversal detected")
        except Exception:
            raise ValueError("Invalid path")
        
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not target_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")
        
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            logger.info(f"Updated file {file_path} in config {config_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update file {file_path} in config {config_id}: {e}")
            raise IOError(f"Failed to update file: {str(e)}")
    
    def delete_config_files(self, config_id: int) -> bool:
        """
        Delete all files for a configuration.
        
        Args:
            config_id: Configuration ID
        
        Returns:
            True on success
        """
        config_dir = self._get_config_dir(config_id)
        
        if config_dir.exists():
            try:
                shutil.rmtree(config_dir)
                logger.info(f"Deleted files for config {config_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete files for config {config_id}: {e}")
                raise IOError(f"Failed to delete configuration files: {str(e)}")
        
        return True