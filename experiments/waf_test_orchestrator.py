"""WAF Test Orchestrator - Manages containers for WAF testing environments."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

import docker
from pydantic import BaseModel, Field
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container

logger = logging.getLogger(__name__)

DEFAULT_LABEL_KEY = "managed_by"
DEFAULT_LABEL_VALUE = "waf-test-orchestrator"
DEFAULT_NETWORK_PREFIX = "waf-test-network"


class WafTestOrchestratorError(Exception):
    """Raised when the orchestrator encounters an error."""


class NetworkInfo(BaseModel):
    """Information about a managed network."""

    id: str
    name: str
    driver: str = "bridge"
    created_at: datetime


class ContainerInfo(BaseModel):
    """Information about a managed container."""

    id: str
    name: str
    image: str
    status: str
    created_at: datetime
    ports: Dict[str, Optional[str]] = Field(default_factory=dict)
    network: Optional[str] = None


class WafTestOrchestrator:
    """Manages Docker containers for WAF testing.

    This orchestrator tracks only the containers it has started,
    allowing safe listing and stopping operations without affecting
    other containers on the system.
    """

    def __init__(
        self,
        label_key: str = DEFAULT_LABEL_KEY,
        label_value: str = DEFAULT_LABEL_VALUE,
        network_prefix: str = DEFAULT_NETWORK_PREFIX,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            label_key: Label key used to identify managed containers.
            label_value: Label value used to identify managed containers.
            network_prefix: Prefix for the default network name.
        """
        try:
            self._client = docker.from_env()
        except DockerException as exc:
            raise WafTestOrchestratorError("Failed to connect to Docker daemon") from exc

        self._label_key = label_key
        self._label_value = label_value
        self._managed_ids: set[str] = set()
        self._managed_networks: Dict[str, str] = {}  # name -> id

        self._default_network = self._create_network(
            f"{network_prefix}-{uuid4().hex[:8]}"
        )

    def _generate_container_name(self, prefix: str = "waf-test") -> str:
        """Generate a unique container name."""
        return f"{prefix}-{uuid4().hex[:8]}"

    def _get_container_ports(self, container: Container) -> Dict[str, Optional[str]]:
        """Extract port mappings from a container."""
        ports: Dict[str, Optional[str]] = {}
        try:
            container.reload()
            port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})
            for container_port, bindings in (port_bindings or {}).items():
                if bindings:
                    host_binding = bindings[0]
                    ports[container_port] = f"{host_binding['HostIp']}:{host_binding['HostPort']}"
                else:
                    ports[container_port] = None
        except DockerException:
            logger.warning("Could not retrieve port info for container %s", container.id[:12])
        return ports

    def get_used_ports(self) -> List[int]:
        """Get all host ports currently in use by any Docker container.

        This includes ports from ALL containers on the system, not just
        those managed by this orchestrator. Useful for avoiding port conflicts.

        Returns:
            List of host port numbers currently in use.
        """
        used_ports: set[int] = set()
        try:
            for container in self._client.containers.list(all=False):  # only running
                try:
                    container.reload()
                    port_bindings = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                    for bindings in (port_bindings or {}).values():
                        if bindings:
                            for binding in bindings:
                                try:
                                    used_ports.add(int(binding["HostPort"]))
                                except (KeyError, ValueError, TypeError):
                                    pass
                except DockerException:
                    continue
        except DockerException as exc:
            logger.warning("Could not list containers for port check: %s", exc)
        return sorted(used_ports)

    def find_available_port(self, start: int = 8000, end: int = 9000) -> Optional[int]:
        """Find an available host port in the given range.

        Args:
            start: Start of port range (inclusive).
            end: End of port range (inclusive).

        Returns:
            An available port number, or None if no port is available.
        """
        used = set(self.get_used_ports())
        for port in range(start, end + 1):
            if port not in used:
                return port
        return None

    def _create_network(self, name: str, driver: str = "bridge") -> NetworkInfo:
        """Create a Docker network and track it."""
        labels = {self._label_key: self._label_value}
        try:
            network = self._client.networks.create(
                name=name,
                driver=driver,
                labels=labels,
            )
            self._managed_networks[name] = network.id
            logger.info("Created network %s (%s)", name, network.id[:12])
            return NetworkInfo(
                id=network.id,
                name=name,
                driver=driver,
                created_at=datetime.now(timezone.utc),
            )
        except DockerException as exc:
            raise WafTestOrchestratorError(f"Failed to create network {name}") from exc

    def create_network(self, name: Optional[str] = None, driver: str = "bridge") -> NetworkInfo:
        """Create a new network for grouping containers.

        Args:
            name: Network name. If not provided, a unique name is generated.
            driver: Network driver (default: "bridge").

        Returns:
            NetworkInfo with details about the created network.
        """
        network_name = name or f"waf-net-{uuid4().hex[:8]}"
        return self._create_network(network_name, driver)

    def list_networks(self) -> List[NetworkInfo]:
        """List all networks managed by this orchestrator."""
        networks: List[NetworkInfo] = []
        for name, network_id in list(self._managed_networks.items()):
            try:
                network = self._client.networks.get(network_id)
                networks.append(NetworkInfo(
                    id=network.id,
                    name=name,
                    driver=network.attrs.get("Driver", "bridge"),
                    created_at=datetime.now(timezone.utc),
                ))
            except NotFound:
                logger.warning("Network %s no longer exists", name)
                self._managed_networks.pop(name, None)
            except DockerException as exc:
                logger.warning("Could not inspect network %s: %s", name, exc)
        return networks

    def remove_network(self, name: str) -> bool:
        """Remove a managed network.

        Args:
            name: The network name to remove.

        Returns:
            True if removed successfully, False otherwise.
        """
        if name == self._default_network.name:
            raise WafTestOrchestratorError("Cannot remove the default session network")

        network_id = self._managed_networks.get(name)
        if not network_id:
            raise WafTestOrchestratorError(f"Network {name} is not managed by this orchestrator")

        try:
            network = self._client.networks.get(network_id)
            network.remove()
            self._managed_networks.pop(name, None)
            logger.info("Removed network %s", name)
            return True
        except DockerException as exc:
            logger.error("Failed to remove network %s: %s", name, exc)
            return False

    @property
    def default_network(self) -> NetworkInfo:
        """Return the default session network."""
        return self._default_network

    def start(
        self,
        image: str,
        *,
        name: Optional[str] = None,
        ports: Optional[Dict[str, int]] = None,
        environment: Optional[Dict[str, str]] = None,
        command: Optional[str] = None,
        network: Optional[str] = None,
        pull: bool = True,
    ) -> ContainerInfo:
        """Start a new container from a Docker Hub image.

        Args:
            image: Docker image name (e.g., "nginx:latest", "httpd:2.4").
            name: Optional container name. If not provided, a unique name is generated.
            ports: Port mappings as {container_port: host_port} (e.g., {"80/tcp": 8080}).
            environment: Environment variables as {key: value}.
            command: Optional command to run in the container.
            network: Network name to connect the container to. Uses default session network if not specified.
            pull: Whether to pull the image before starting (default: True).

        Returns:
            ContainerInfo with details about the started container.

        Raises:
            WafTestOrchestratorError: If the container fails to start.
        """
        if pull:
            try:
                logger.info("Pulling image %s...", image)
                self._client.images.pull(image)
            except ImageNotFound:
                raise WafTestOrchestratorError(f"Image not found: {image}")
            except DockerException as exc:
                raise WafTestOrchestratorError(f"Failed to pull image {image}") from exc

        container_name = name or self._generate_container_name()
        labels = {self._label_key: self._label_value}

        port_bindings = None
        if ports:
            port_bindings = {k: v for k, v in ports.items()}

        network_name = network or self._default_network.name
        if network and network not in self._managed_networks:
            raise WafTestOrchestratorError(
                f"Network {network} is not managed by this orchestrator. "
                "Use create_network() first or use the default network."
            )

        try:
            container: Container = self._client.containers.run(
                image,
                name=container_name,
                ports=port_bindings,
                environment=environment,
                command=command,
                labels=labels,
                network=network_name,
                detach=True,
            )
        except DockerException as exc:
            raise WafTestOrchestratorError(f"Failed to start container: {exc}") from exc

        self._managed_ids.add(container.id)

        container.reload()
        info = ContainerInfo(
            id=container.id,
            name=container.name,
            image=image,
            status=container.status,
            created_at=datetime.now(timezone.utc),
            ports=self._get_container_ports(container),
            network=network_name,
        )

        logger.info("Started container %s (%s) from image %s on network %s", info.name, info.id[:12], image, network_name)
        return info

    def list(self, *, refresh: bool = True) -> List[ContainerInfo]:
        """List all containers managed by this orchestrator instance.

        Args:
            refresh: Whether to refresh container status from Docker (default: True).

        Returns:
            List of ContainerInfo for all managed containers.
        """
        containers: List[ContainerInfo] = []

        for container_id in list(self._managed_ids):
            try:
                container = self._client.containers.get(container_id)
                if refresh:
                    container.reload()

                networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
                network_name = list(networks.keys())[0] if networks else None

                info = ContainerInfo(
                    id=container.id,
                    name=container.name,
                    image=container.image.tags[0] if container.image.tags else str(container.image.id[:12]),
                    status=container.status,
                    created_at=datetime.now(timezone.utc),
                    ports=self._get_container_ports(container),
                    network=network_name,
                )
                containers.append(info)
            except NotFound:
                logger.warning("Container %s no longer exists, removing from tracking", container_id[:12])
                self._managed_ids.discard(container_id)
            except DockerException as exc:
                logger.warning("Could not inspect container %s: %s", container_id[:12], exc)

        return containers

    def stop(
        self,
        container_id: str,
        *,
        remove: bool = True,
        timeout: int = 10,
    ) -> bool:
        """Stop a container managed by this orchestrator.

        Args:
            container_id: The container ID or name to stop.
            remove: Whether to remove the container after stopping (default: True).
            timeout: Timeout in seconds to wait for the container to stop.

        Returns:
            True if the container was stopped successfully, False otherwise.

        Raises:
            WafTestOrchestratorError: If the container is not managed by this orchestrator.
        """
        resolved_id = self._resolve_container_id(container_id)
        if resolved_id not in self._managed_ids:
            raise WafTestOrchestratorError(
                f"Container {container_id} is not managed by this orchestrator"
            )

        try:
            container = self._client.containers.get(resolved_id)
            container.stop(timeout=timeout)
            logger.info("Stopped container %s", container.name)

            if remove:
                container.remove()
                logger.info("Removed container %s", container.name)

            self._managed_ids.discard(resolved_id)
            return True

        except NotFound:
            logger.warning("Container %s not found", container_id)
            self._managed_ids.discard(resolved_id)
            return False
        except DockerException as exc:
            logger.error("Failed to stop container %s: %s", container_id, exc)
            return False

    def stop_all(self, *, remove: bool = True, timeout: int = 10) -> List[str]:
        """Stop all containers managed by this orchestrator.

        Args:
            remove: Whether to remove containers after stopping (default: True).
            timeout: Timeout in seconds to wait for each container to stop.

        Returns:
            List of container IDs that were successfully stopped.
        """
        stopped: List[str] = []
        for container_id in list(self._managed_ids):
            try:
                if self.stop(container_id, remove=remove, timeout=timeout):
                    stopped.append(container_id)
            except WafTestOrchestratorError:
                pass
        return stopped

    def _resolve_container_id(self, container_id_or_name: str) -> str:
        """Resolve a container ID or name to the full container ID."""
        if container_id_or_name in self._managed_ids:
            return container_id_or_name

        for managed_id in self._managed_ids:
            if managed_id.startswith(container_id_or_name):
                return managed_id

        try:
            container = self._client.containers.get(container_id_or_name)
            return container.id
        except (NotFound, DockerException):
            return container_id_or_name

    @property
    def managed_count(self) -> int:
        """Return the number of containers currently managed."""
        return len(self._managed_ids)

    def cleanup(self) -> None:
        """Stop all containers and remove all networks managed by this orchestrator."""
        self.stop_all()
        self._cleanup_networks()

    def _cleanup_networks(self) -> None:
        """Remove all managed networks."""
        for name, network_id in list(self._managed_networks.items()):
            try:
                network = self._client.networks.get(network_id)
                network.remove()
                logger.info("Removed network %s", name)
            except NotFound:
                pass
            except DockerException as exc:
                logger.warning("Could not remove network %s: %s", name, exc)
            finally:
                self._managed_networks.pop(name, None)

    def __enter__(self) -> "WafTestOrchestrator":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    with WafTestOrchestrator() as orchestrator:
        print(f"Default network: {orchestrator.default_network.name}")

        container = orchestrator.start("nginx:alpine")
        print(f"\nStarted: {container.model_dump()}")

        print("\nManaged containers:")
        for c in orchestrator.list():
            print(c.model_dump())


        print("used ports:", orchestrator.get_used_ports())
        print("\nManaged networks:")
        for n in orchestrator.list_networks():
            print(n.model_dump())
