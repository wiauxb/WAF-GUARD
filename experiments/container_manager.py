"""Lightweight testing-environment deployment manager."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union
from uuid import uuid4

import docker
import yaml
from docker.errors import DockerException
from docker.models.containers import Container

logger = logging.getLogger(__name__)

DEFAULT_IMAGE = "lwilliot/apache-modsecurity2:latest"
DEFAULT_LABEL_KEY = "managed_by"
DEFAULT_LABEL_VALUE = "testing-environment"


class ContainerManagerError(Exception):
    """Raised when the deployment manager encounters an operational error."""


@dataclass
class ServiceSpec:
    """Minimal service description derived from a subset of Compose."""

    name: str
    image: str
    command: Optional[Union[str, Sequence[str]]] = None
    ports: List[str] = field(default_factory=list)
    environment: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    extra_labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class DeploymentSpec:
    """High-level deployment describing a group of services."""

    name: str
    services: List[ServiceSpec] = field(default_factory=list)


@dataclass
class ContainerRecord:
    """Metadata captured for every managed container."""

    name: str
    container_id: str
    image: str
    created_at: datetime
    status: str
    ports: Dict[str, List[str]]
    labels: Dict[str, str]
    deployment: str
    service: str
    container: Container = field(repr=False)


def deployment_spec_from_mapping(data: Mapping[str, Any], *, default_name: Optional[str] = None) -> DeploymentSpec:
    """Normalize an in-memory representation into a DeploymentSpec."""
    if not isinstance(data, Mapping):
        raise ContainerManagerError("Deployment spec must be a mapping/dict")

    name = data.get("name") or default_name or "deployment"
    services_raw = data.get("services")
    if not isinstance(services_raw, Mapping):
        raise ContainerManagerError("'services' section missing or invalid in deployment spec")

    services: List[ServiceSpec] = []
    for service_name, service_data in services_raw.items():
        if not isinstance(service_data, Mapping):
            raise ContainerManagerError(f"Invalid definition for service '{service_name}'")
        image = service_data.get("image")
        if not image or not isinstance(image, str):
            raise ContainerManagerError(f"Service '{service_name}' must declare an image")

        spec = ServiceSpec(
            name=service_name,
            image=image,
            command=service_data.get("command"),
            ports=_coerce_list_of_strings(service_data.get("ports")),
            environment=_normalize_environment(service_data.get("environment")),
            depends_on=_coerce_list_of_strings(service_data.get("depends_on")),
            extra_labels=_normalize_labels(service_data.get("labels")),
        )
        services.append(spec)

    return DeploymentSpec(name=name, services=services)


def load_deployment_spec(path: str | Path) -> DeploymentSpec:
    """Load a deployment specification from a YAML file."""
    path_obj = Path(path)
    if not path_obj.exists():
        raise ContainerManagerError(f"Deployment file not found: {path}")

    data = yaml.safe_load(path_obj.read_text()) or {}
    return deployment_spec_from_mapping(data, default_name=path_obj.stem)


def _coerce_list_of_strings(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value if item is not None]
    raise ContainerManagerError("Expected a list of strings")


def _normalize_environment(value: Any) -> Dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(k): str(v) for k, v in value.items() if v is not None}
    if isinstance(value, Sequence):
        env: Dict[str, str] = {}
        for item in value:
            if not isinstance(item, str) or "=" not in item:
                raise ContainerManagerError("Environment entries must be strings like KEY=value")
            key, val = item.split("=", 1)
            env[key] = val
        return env
    raise ContainerManagerError("Invalid environment specification")


def _normalize_labels(value: Any) -> Dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return {str(k): str(v) for k, v in value.items() if v is not None}
    raise ContainerManagerError("Labels must be a mapping")


def _build_port_bindings(ports: Sequence[str]) -> Dict[str, Union[int, Tuple[str, int]]]:
    bindings: Dict[str, Union[int, Tuple[str, int]]] = {}
    for spec in ports:
        parts = spec.split(":")
        if len(parts) == 1:
            host_port = parts[0]
            container = parts[0]
            host_ip = None
        elif len(parts) == 2:
            host_port, container = parts
            host_ip = None
        elif len(parts) == 3:
            host_ip, host_port, container = parts
        else:
            raise ContainerManagerError(f"Unsupported port mapping: {spec}")

        container_port = container if "/" in container else f"{container}/tcp"
        try:
            host_port_int = int(host_port)
        except ValueError as exc:
            raise ContainerManagerError(f"Invalid host port '{host_port}' in '{spec}'") from exc

        binding: Union[int, Tuple[str, int]] = host_port_int
        if host_ip:
            binding = (host_ip, host_port_int)

        bindings[container_port] = binding
    return bindings


def _topological_order(services: Sequence[ServiceSpec]) -> List[ServiceSpec]:
    pending = {service.name: set(service.depends_on) for service in services}
    service_map = {service.name: service for service in services}
    ordered: List[ServiceSpec] = []

    while pending:
        ready = [name for name, deps in pending.items() if not deps]
        if not ready:
            raise ContainerManagerError("Circular dependency detected in deployment spec")
        for name in ready:
            ordered.append(service_map[name])
            pending.pop(name)
            for deps in pending.values():
                deps.discard(name)
    return ordered


def _record_to_dict(record: ContainerRecord) -> dict[str, Any]:
    return {
        "name": record.name,
        "service": record.service,
        "deployment": record.deployment,
        "image": record.image,
        "status": record.status,
        "ports": record.ports,
        "labels": record.labels,
        "created_at": record.created_at.isoformat(),
    }


class EnvironmentManager:
    """Manages Docker containers for testing deployments."""

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        *,
        pull_before_run: bool = True,
        label_key: str = DEFAULT_LABEL_KEY,
        label_value: str = DEFAULT_LABEL_VALUE,
    ) -> None:
        try:
            self.client = docker.from_env()
        except DockerException as exc:
            raise ContainerManagerError("Failed to connect to Docker daemon") from exc

        self.image = image
        self.pull_before_run = pull_before_run
        self.label_key = label_key
        self.label_value = label_value
        self._tracked: Dict[str, ContainerRecord] = {}
        self._deployments: Dict[str, List[str]] = {}

    def _ensure_image_for_service(self, image: str) -> None:
        if not self.pull_before_run:
            return
        try:
            self.client.images.pull(image)
        except DockerException as exc:
            raise ContainerManagerError(f"Failed to pull image {image}") from exc

    def _generate_name(self, base: str) -> str:
        normalized = base.rstrip("-")
        if normalized not in self._tracked:
            return normalized
        return f"{normalized}-{uuid4().hex[:8]}"

    def _build_labels(self, extra: Mapping[str, str]) -> Dict[str, str]:
        labels = {self.label_key: self.label_value}
        labels.update(extra)
        return labels

    def _track_container(self, record: ContainerRecord) -> None:
        self._tracked[record.name] = record
        deployment_list = self._deployments.setdefault(record.deployment, [])
        deployment_list.append(record.name)

    def _untrack_container(self, record: ContainerRecord) -> None:
        self._tracked.pop(record.name, None)
        names = self._deployments.get(record.deployment)
        if names and record.name in names:
            names.remove(record.name)
            if not names:
                self._deployments.pop(record.deployment, None)

    def _refresh_record(self, record: ContainerRecord) -> None:
        try:
            record.container.reload()
            record.status = record.container.status
            record.ports = self._normalize_ports(
                record.container.attrs.get("NetworkSettings", {}).get("Ports")
            )
        except DockerException:
            logger.exception("Failed to refresh metadata for container %s", record.name)

    @staticmethod
    def _normalize_ports(port_mapping: Optional[Mapping[str, Any]]) -> Dict[str, List[str]]:
        normalized: Dict[str, List[str]] = {}
        if not port_mapping:
            return normalized

        for container_port, bindings in port_mapping.items():
            if not bindings:
                normalized[container_port] = []
                continue
            normalized[container_port] = [f"{binding['HostIp']}:{binding['HostPort']}" for binding in bindings]
        return normalized

    def deploy(self, spec: DeploymentSpec) -> List[ContainerRecord]:
        """Deploy a spec by starting each service with dependency order."""
        ordered_services = _topological_order(spec.services)
        records: List[ContainerRecord] = []
        for service in ordered_services:
            record = self._run_service(spec.name, service)
            records.append(record)
        return records

    def _run_service(self, deployment: str, service: ServiceSpec) -> ContainerRecord:
        self._ensure_image_for_service(service.image)
        container_name = self._generate_name(f"{deployment}-{service.name}")
        labels = self._build_labels(service.extra_labels)
        ports = _build_port_bindings(service.ports) if service.ports else {}

        try:
            container = self.client.containers.run(
                service.image,
                name=container_name,
                ports=ports or None,
                environment=service.environment or None,
                command=service.command,
                labels=labels,
                detach=True,
            )
        except DockerException as exc:
            raise ContainerManagerError(f"Failed to start service '{service.name}'") from exc

        try:
            container.reload()
        except DockerException:
            pass

        record = ContainerRecord(
            name=container_name,
            container_id=container.id,
            image=service.image,
            created_at=datetime.now(timezone.utc),
            status=container.status,
            ports=self._normalize_ports(
                container.attrs.get("NetworkSettings", {}).get("Ports")
            ),
            labels=labels,
            deployment=deployment,
            service=service.name,
            container=container,
        )
        self._track_container(record)
        logger.info("Started container %s (%s)", record.name, service.name)
        return record

    def stop_container(self, name: str, *, remove: bool = True, timeout: int = 10) -> None:
        """Stop and remove a container by name if it is tracked."""
        record = self._tracked.get(name)
        if not record:
            raise ContainerManagerError(f"Container '{name}' is not tracked")

        try:
            record.container.stop(timeout=timeout)
        except DockerException:
            logger.exception("Failed to stop container %s", name)
        finally:
            if remove:
                try:
                    record.container.remove()
                except DockerException:
                    logger.exception("Failed to remove container %s", name)
            self._untrack_container(record)

    def stop_deployment(self, name: str) -> List[str]:
        """Stop every container belonging to a deployment."""
        stopped: List[str] = []
        for container_name in list(self._deployments.get(name, [])):
            try:
                self.stop_container(container_name)
                stopped.append(container_name)
            except ContainerManagerError:
                logger.exception("Failed to stop container %s from deployment %s", container_name, name)
        return stopped

    def list_containers(self) -> List[ContainerRecord]:
        """Return metadata for all containers started during this session."""
        for record in self._tracked.values():
            self._refresh_record(record)
        return list(self._tracked.values())

    def cleanup_all(self, *, tolerate_errors: bool = True) -> List[str]:
        """Stop and remove every tracked container."""
        stopped: List[str] = []
        for name in list(self._tracked.keys()):
            try:
                self.stop_container(name)
                stopped.append(name)
            except ContainerManagerError:
                if tolerate_errors:
                    logger.exception("Failed to cleanup container %s", name)
                else:
                    raise
        return stopped

    def destroy_previous_runs(self) -> List[str]:
        """Purge any containers left by older runs that share the manager label."""
        filters = {"label": f"{self.label_key}={self.label_value}"}
        removed: List[str] = []
        for container in self.client.containers.list(all=True, filters=filters):
            if container.name in self._tracked:
                continue
            try:
                container.stop()
            except DockerException:
                logger.debug("Could not stop container %s before removal", container.name)
            try:
                container.remove()
            except DockerException:
                logger.exception("Failed to remove orphaned container %s", container.name)
            else:
                removed.append(container.name)
        return removed

    @property
    def tracked_names(self) -> List[str]:
        """Return the list of container names managed in this session."""
        return list(self._tracked.keys())


def sample_deployment_spec() -> DeploymentSpec:
    return deployment_spec_from_mapping(
        {
            "name": "dvwa-stack",
            "services": {
                "db": {
                    "image": "docker.io/library/mariadb:10",
                    "environment": [
                        "MYSQL_ROOT_PASSWORD=dvwa",
                        "MYSQL_DATABASE=dvwa",
                        "MYSQL_USER=dvwa",
                        "MYSQL_PASSWORD=p@ssw0rd",
                    ],
                },
                "dvwa": {
                    "image": "ghcr.io/digininja/dvwa:latest",
                    "depends_on": ["db"],
                    "ports": ["127.0.0.1:4280:80"],
                    "environment": [
                        "DB_SERVER=db",
                    ],
                },
            },
        }
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    manager = EnvironmentManager()

    logging.info("Cleaning leftover containers...")
    removed = manager.destroy_previous_runs()
    if removed:
        logging.info("Removed orphaned containers: %s", removed)

    spec = sample_deployment_spec()

    try:
        logging.info("Deploying %s", spec.name)
        records = manager.deploy(spec)
        logging.info("Started %d containers", len(records))
        time.sleep(2)
        for record in records:
            logging.info(json.dumps(_record_to_dict(record), indent=2))
    finally:
        logging.info("Shutting down managed containers...")
        cleaned = manager.cleanup_all()
        if cleaned:
            logging.info("Stopped containers: %s", cleaned)
        else:
            logging.info("No containers were running")


if __name__ == "__main__":
    main()
