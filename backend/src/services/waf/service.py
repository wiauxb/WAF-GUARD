import requests
from pathlib import Path
import logging
import gzip

logger = logging.getLogger(__name__)

class WAFService:
    """Integration with WAF container for dump generation"""
    
    def generate_dump(self, config_zip_path: str, waf_url: str, timeout: int = 120) -> bytes:
        """
        Send configuration to WAF and get compiled dump (gzip compressed).

        Args:
            config_zip_path: Filesystem path to configuration zip
            waf_url: URL of WAF service
            timeout: Request timeout in seconds

        Returns:
            Gzip-compressed Apache dump content (binary)

        Raises:
            FileNotFoundError: If zip file not found
            RuntimeError: If WAF service fails
        """
        zip_path = Path(config_zip_path)

        if not zip_path.exists():
            raise FileNotFoundError(f"Configuration zip not found: {config_zip_path}")

        try:
            # Read zip file
            with open(zip_path, "rb") as f:
                files = {"file": (zip_path.name, f, "application/zip")}

                # Send to WAF service
                response = requests.post(
                    f"{waf_url}/get_dump",
                    files=files,
                    timeout=timeout
                )

            # Check response
            if response.status_code != 200:
                logger.error(f"WAF service error: {response.status_code} - {response.text}")
                raise RuntimeError(f"WAF service returned error: {response.text}")

            # Return compressed binary content
            compressed_dump = response.content
            logger.info(f"Received compressed dump: {len(compressed_dump)} bytes (gzip)")

            return compressed_dump

        except requests.ConnectionError:
            logger.error(f"Cannot connect to WAF service at {waf_url}")
            raise RuntimeError(f"Cannot connect to WAF service at {waf_url}")

        except requests.Timeout:
            logger.error(f"WAF service timeout after {timeout} seconds")
            raise RuntimeError(f"WAF service timeout after {timeout} seconds")

        except Exception as e:
            logger.error(f"WAF service error: {e}")
            raise RuntimeError(f"Failed to generate dump: {str(e)}")