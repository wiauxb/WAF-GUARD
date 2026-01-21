"""
Configuration Generator Module

Generates a new configuration folder structure from templates.
Converts .template files to .conf files during the copy process.
Substitutes ${VARIABLE} placeholders with values from defaults.yaml.
"""

import json
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path
from string import Template
from typing import Optional

import yaml

CRS_DOWNLOAD_URL = "https://github.com/coreruleset/coreruleset/releases/download/v{version}/coreruleset-{version}-minimal.tar.gz"
CRS_RELEASES_API = "https://api.github.com/repos/coreruleset/coreruleset/releases"


def get_available_stacks(templates_dir: str = "templates") -> list[dict]:
    """
    Get list of available stacks from the templates directory.

    Args:
        templates_dir: Path to the templates directory

    Returns:
        list: List of dicts with stack info: {"name": str, "path": str}
    """
    templates_path = Path(templates_dir)
    stacks_path = templates_path / "stacks"

    if not stacks_path.exists():
        return []

    stacks = []
    for stack_dir in stacks_path.iterdir():
        if stack_dir.is_dir() and (stack_dir / "defaults.yaml").exists():
            stacks.append({
                "name": stack_dir.name,
                "path": str(stack_dir)
            })

    return sorted(stacks, key=lambda x: x["name"])


def get_available_apps(templates_dir: str = "templates") -> list[dict]:
    """
    Get list of available apps from the templates directory.

    Args:
        templates_dir: Path to the templates directory

    Returns:
        list: List of dicts with app info: {"name": str, "path": str}
    """
    templates_path = Path(templates_dir)
    apps_path = templates_path / "apps"

    if not apps_path.exists():
        return []

    apps = []
    for app_dir in apps_path.iterdir():
        if app_dir.is_dir():
            apps.append({
                "name": app_dir.name,
                "path": str(app_dir)
            })

    return sorted(apps, key=lambda x: x["name"])


def get_available_crs_versions(limit: int = 10) -> list[dict]:
    """
    Fetch available CRS versions from GitHub releases API.

    Args:
        limit: Maximum number of versions to return

    Returns:
        list: List of dicts with version info: {"version": str, "name": str, "published_at": str}
    """
    try:
        req = urllib.request.Request(
            CRS_RELEASES_API,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            releases = json.loads(response.read().decode("utf-8"))

        versions = []
        for release in releases[:limit]:
            tag = release.get("tag_name", "")
            # Remove 'v' prefix if present
            version = tag.lstrip("v")
            versions.append({
                "version": version,
                "tag": tag,
                "name": release.get("name", ""),
                "published_at": release.get("published_at", "")
            })

        return versions
    except Exception:
        return []


def get_stack_defaults(stack: str, templates_dir: str = "templates") -> dict:
    """
    Get default configuration values for a specific stack.

    Args:
        stack: Name of the stack
        templates_dir: Path to the templates directory

    Returns:
        dict: Dictionary of default variable names to values
    """
    templates_path = Path(templates_dir)
    defaults_file = templates_path / "stacks" / stack / "defaults.yaml"
    return load_defaults(defaults_file)


def load_defaults(file_path: Path) -> dict:
    """
    Load variables from a YAML defaults file.

    Args:
        file_path: Path to the defaults.yaml file

    Returns:
        dict: Dictionary of variable names to values
    """
    if not file_path.exists():
        return {}

    with open(file_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data if data else {}


def download_crs_rules(version: str, dest_dir: Path) -> int:
    """
    Download and extract CRS rules from GitHub.

    Args:
        version: CRS version to download (e.g., "4.0.0")
        dest_dir: Destination directory for the rules

    Returns:
        int: Number of rule files extracted
    """
    url = CRS_DOWNLOAD_URL.format(version=version)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        tarball_path = tmp_path / f"coreruleset-{version}-minimal.tar.gz"

        # Download the tarball
        urllib.request.urlretrieve(url, tarball_path)

        # Extract the tarball
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(tmp_path)

        # Find the rules directory (inside coreruleset-{version}/rules/)
        extracted_dir = tmp_path / f"coreruleset-{version}"
        rules_src = extracted_dir / "rules"

        # Copy rules to destination
        rule_count = 0
        if rules_src.exists():
            for rule_file in rules_src.iterdir():
                if rule_file.is_file():
                    shutil.copy2(rule_file, dest_dir / rule_file.name)
                    rule_count += 1

        return rule_count


def substitute_variables(content: str, variables: dict) -> str:
    """
    Substitute ${VARIABLE} placeholders with values from variables dict.
    Uses string.Template for safe substitution (unmatched variables are kept as-is).

    Args:
        content: Template content with ${VARIABLE} placeholders
        variables: Dictionary of variable names to values

    Returns:
        str: Content with variables substituted
    """
    template = Template(content)
    return template.safe_substitute(variables)


def generate_config(
    templates_dir: str = "templates",
    output_dir: str = "config",
    stack: str = "apache-modsecurity2",
    overwrite: bool = False,
    variables: Optional[dict] = None,
    apps: Optional[list] = None,
    crs_version: Optional[str] = None
) -> dict:
    """
    Generate a new configuration folder structure from templates.

    Creates the following structure:
        config/
        ├── apache/
        │   ├── httpd.conf
        │   └── extra/
        │       └── *.conf files
        └── modsecurity/
            ├── modsecurity.conf
            ├── crs-setup.conf
            ├── unicode.mapping
            ├── apps/
            ├── crs_rules/
            └── custom/
                ├── crs/
                └── apps/

    Args:
        templates_dir: Path to the templates directory
        output_dir: Path to the output config directory
        stack: The stack template to use (default: apache-modsecurity2)
        overwrite: If True, remove existing config directory before generating
        variables: Optional dict of variables to override defaults
        apps: Optional list of app names to include (empty list = no apps, None = no apps)
        crs_version: Optional CRS version to download (e.g., "4.0.0")

    Returns:
        dict: Summary of the generation process with counts and paths

    Raises:
        FileExistsError: If output directory exists and overwrite is False
        FileNotFoundError: If templates directory doesn't exist
    """
    templates_path = Path(templates_dir)
    output_path = Path(output_dir)
    stack_path = templates_path / "stacks" / stack
    apps_path = templates_path / "apps"

    # Validate templates directory exists
    if not templates_path.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_path}")

    if not stack_path.exists():
        raise FileNotFoundError(f"Stack template not found: {stack_path}")

    # Load default variables and merge with overrides
    defaults_file = stack_path / "defaults.yaml"
    template_vars = load_defaults(defaults_file)
    if variables:
        template_vars.update(variables)

    # Handle existing output directory
    if output_path.exists():
        if not overwrite:
            raise FileExistsError(
                f"Output directory already exists: {output_path}. "
                "Use overwrite=True to replace it."
            )
        shutil.rmtree(output_path)

    # Track statistics
    stats = {
        "files_copied": 0,
        "files_converted": 0,
        "variables_substituted": 0,
        "directories_created": 0,
        "apache_files": [],
        "modsecurity_files": []
    }

    # Create output directory structure
    output_path.mkdir(parents=True, exist_ok=True)
    stats["directories_created"] += 1

    # Process Apache configuration
    apache_src = stack_path / "apache"
    apache_dest = output_path / "apache"
    if apache_src.exists():
        _copy_and_convert_directory(apache_src, apache_dest, template_vars, stats, "apache_files")

    # Process ModSecurity configuration
    modsec_src = stack_path / "modsecurity"
    modsec_dest = output_path / "modsecurity"
    if modsec_src.exists():
        _copy_and_convert_directory(modsec_src, modsec_dest, template_vars, stats, "modsecurity_files")

    # Create additional ModSecurity subdirectories
    modsec_subdirs = [
        "apps",
        "crs_rules",
        "custom/crs",
        "custom/apps"
    ]
    for subdir in modsec_subdirs:
        subdir_path = modsec_dest / subdir
        if not subdir_path.exists():
            subdir_path.mkdir(parents=True, exist_ok=True)
            stats["directories_created"] += 1

    # Download CRS rules if version specified
    if crs_version:
        crs_rules_dir = modsec_dest / "crs_rules"
        stats["crs_rules_count"] = download_crs_rules(crs_version, crs_rules_dir)

    # Create default empty CRS customization files
    crs_custom_files = ["before-crs.conf", "after-crs.conf"]
    for filename in crs_custom_files:
        file_path = modsec_dest / "custom" / "crs" / filename
        file_path.touch()

    # Copy app configurations to modsecurity/apps (only if apps list provided)
    if apps_path.exists() and apps:
        _copy_apps_directory(apps_path, modsec_dest / "apps", stats, apps)

        # Create empty custom files for each app
        for app_name in apps:
            app_custom_dir = modsec_dest / "custom" / "apps" / app_name
            app_custom_dir.mkdir(parents=True, exist_ok=True)
            stats["directories_created"] += 1
            (app_custom_dir / f"{app_name}-before.conf").touch()
            (app_custom_dir / f"{app_name}-after.conf").touch()

    return stats


def _copy_and_convert_directory(
    src: Path,
    dest: Path,
    variables: dict,
    stats: dict,
    files_key: str
) -> None:
    """
    Recursively copy a directory, converting .template files to .conf files
    and substituting variables.

    Args:
        src: Source directory path
        dest: Destination directory path
        variables: Dictionary of template variables
        stats: Statistics dictionary to update
        files_key: Key in stats dict to append file paths to
    """
    dest.mkdir(parents=True, exist_ok=True)
    stats["directories_created"] += 1

    for item in src.iterdir():
        if item.is_dir():
            _copy_and_convert_directory(item, dest / item.name, variables, stats, files_key)
        elif item.is_file():
            # Determine output filename
            if item.suffix == ".template":
                new_name = item.stem  # Remove .template extension
                if not new_name.endswith(".conf"):
                    new_name += ".conf"
                dest_file = dest / new_name
                stats["files_converted"] += 1
            else:
                dest_file = dest / item.name

            # Read, substitute variables, and write
            content = item.read_text(encoding="utf-8")
            processed_content = substitute_variables(content, variables)

            if content != processed_content:
                stats["variables_substituted"] += 1

            dest_file.write_text(processed_content, encoding="utf-8")
            stats["files_copied"] += 1
            stats[files_key].append(str(dest_file))


def _copy_apps_directory(src: Path, dest: Path, stats: dict, apps: list) -> None:
    """
    Copy application-specific configurations to the apps directory.

    Args:
        src: Source apps directory path
        dest: Destination apps directory path
        stats: Statistics dictionary to update
        apps: List of app names to include
    """
    for app_dir in src.iterdir():
        if app_dir.is_dir() and app_dir.name in apps:
            app_dest = dest / app_dir.name
            app_dest.mkdir(parents=True, exist_ok=True)
            stats["directories_created"] += 1

            for item in app_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, app_dest / item.name)
                    stats["files_copied"] += 1
                    stats["modsecurity_files"].append(str(app_dest / item.name))


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 1: Discovery")
    print("=" * 60)

    # Get available stacks
    print("\n[Available Stacks]")
    stacks = get_available_stacks()
    for stack in stacks:
        print(f"  - {stack['name']}")

    # Get available apps
    print("\n[Available Apps]")
    apps = get_available_apps()
    for app in apps:
        print(f"  - {app['name']}")

    # Get available CRS versions
    print("\n[Available CRS Versions (top 5)]")
    crs_versions = get_available_crs_versions(limit=5)
    for v in crs_versions:
        print(f"  - {v['version']} (released: {v['published_at'][:10]})")

    print("\n" + "=" * 60)
    print("PHASE 2: Configuration")
    print("=" * 60)

    # Get stack defaults
    selected_stack = "apache-modsecurity2"
    print(f"\n[Default values for '{selected_stack}']")
    defaults = get_stack_defaults(selected_stack)
    print(f"  Total variables: {len(defaults)}")
    print("\n  Sample values:")
    sample_keys = ["PORT", "BACKEND", "SERVER_NAME", "MODSEC_RULE_ENGINE", "BLOCKING_PARANOIA"]
    for key in sample_keys:
        if key in defaults:
            print(f"    {key}: {defaults[key]}")

    print("\n" + "=" * 60)
    print("PHASE 3: Generation")
    print("=" * 60)

    try:
        # Generate config with custom overrides
        result = generate_config(
            overwrite=True,
            apps=["wordpress"],
            crs_version=crs_versions[0]["version"] if crs_versions else None,
            variables={"PORT": 80, "MODSEC_RULE_ENGINE": "On", "BACKEND": "http://dvwa:80"}
        )
        print("\n[Generation Result]")
        print(f"  Directories created: {result['directories_created']}")
        print(f"  Files copied: {result['files_copied']}")
        print(f"  Templates converted: {result['files_converted']}")
        print(f"  Variables substituted: {result['variables_substituted']}")
        if "crs_rules_count" in result:
            print(f"  CRS rules downloaded: {result['crs_rules_count']}")

        print("\n[Apache files]")
        for f in result["apache_files"]:
            print(f"  - {f}")

        print("\n[ModSecurity files]")
        for f in result["modsecurity_files"]:
            print(f"  - {f}")

    except Exception as e:
        print(f"Error: {e}")
