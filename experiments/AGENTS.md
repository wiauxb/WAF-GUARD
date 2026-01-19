# AGENTS.md

This repository hosts the ModSecurity WAF configuration tooling:
- The `container/` image bundles Apache + ModSecurity + the FastAPI management API.
- `config_generator.py` produces templated `config/` artifacts that `sender.py` packages and ships into the container.
- `templates/` stores stack/app blueprints and their `defaults.yaml` overrides, while `config/` is generated output and should never be committed.

*Keep this document handy when you automate work here; it spells out how to build, inspect, and extend the service.*

## Build & Run

1. `docker compose build modsecurity-waf`
   - Compiles ModSecurity, installs runtime Python dependencies, and packages the FastAPI API using the multi-stage `container/Dockerfile`.
2. `docker compose up --build`
   - Starts Apache/ModSecurity (ports `8080`/`8443`) and the management API (`9000`).
   - Watch the entrypoint logs for certificate creation, low-port warnings, and API startup notices.
3. `docker compose down`
   - Tears down containers and networks once testing finishes; add `--volumes` if you intentionally persist `/tmp/modsecurity` state.
4. `docker compose exec modsecurity-waf /app/venv/bin/python /app/api/main.py`
   - Runs the API inside the container so you can hit endpoints with `curl` (mirrors the entrypoint behavior without Apache).
5. `python -m uvicorn container.api.main:app --reload --host 0.0.0.0 --port 9000`
   - Runs the FastAPI app locally outside Docker; point `sender.py` at `http://localhost:9000` for quick iteration.
6. `python -m pip install --upgrade fastapi uvicorn python-multipart requests pyyaml`
   - Syncs your venv with the container’s dependencies. Keep the pinned versions aligned with `container/Dockerfile` if you change the stack.
7. `docker compose logs -f modsecurity-waf`
   - Follow this after starting the stack to confirm Apache/ModSecurity initialize cleanly and the API logs `startup complete`.
8. `docker compose exec modsecurity-waf /usr/local/apache2/bin/apachectl configtest`
   - Validate the generated Apache configuration before reloading the server.
9. `docker compose exec modsecurity-waf tail -n 50 /var/log/modsec_audit.log`
   - Quickly inspect ModSecurity audit entries when troubleshooting false positives.

## Fast Feedback (Single Test Focus)

1. There are no unified unit tests yet, but if you add any, execute a single test with:
   ```bash
   python -m pytest tests/<module>.py::TestClass::test_case
   ```
   - Use `::` syntax to pinpoint a class or function so CI stays fast.
   - Run it from the repo root so pytest can discover `templates/`, `config/`, and your helper modules.
2. When verifying `config_generator.py` manually:
   ```bash
   python config_generator.py
   ```
   - It walks through discovery, configuration, and generation phases, then dumps statistics or raises on missing inputs.
3. To exercise `sender.py` without Docker you can:
   ```bash
   export API_URL=http://localhost:9000
   python sender.py --url $API_URL --config config
   ```
   - The script already catches `requests.ConnectionError` and `Timeout`; wrap this call in a test to assert those messages if you introduce mocks later.
4. Inside the container, target a single test with:
   ```bash
   docker compose exec modsecurity-waf /app/venv/bin/python -m pytest tests/<module>.py::test_name
   ```
   - Use this when you want to exercise container-specific logic or dependencies.
5. When you change `templates/` or defaults, run `python config_generator.py` plus `docker compose exec modsecurity-waf /usr/local/apache2/bin/apachectl configtest` to ensure generated configs parse.

## Structure Checklist for Agents

- `container/`: Base image layers, runtime scripts (`bin/`), and Apache/ModSecurity tooling.
- `container/api/main.py`: FastAPI entrypoint. Async handlers live here and run in the `/app/venv` environment.
- `config_generator.py`: Main generator with `_copy_and_convert_directory` helpers for templating and substitution.
- `sender.py`: Zips `config/` and posts to the API; exercises HTTP error handling in `requests`.
- `templates/`: Source stacks/apps. Keep `defaults.yaml` alongside each stack; apps live under `templates/apps/<name>`.
- `config/`: Generated artifacts (ignored in git). Treat it as disposable output; delete and regenerate as needed.
- `docker-compose.yml`: Wire-up that exposes Apache/ModSecurity (8086) and the management API (9000) on the host.

## Coding & Style Guidelines

### Imports
- Always group imports in this order with a blank line between groups:
  1. Python standard library (`json`, `pathlib`, `tempfile`).
  2. Third-party (`fastapi`, `requests`, `yaml`).
  3. Local modules (none yet, but keep this pattern even when adding helpers).
- Use absolute imports (e.g., `from fastapi import HTTPException`). Do not rely on relative imports spanning directories.
- Each import line should import specific names only when it improves clarity; prefer `from pathlib import Path` over `import pathlib` unless you need the module itself.

### Formatting & Tooling
- Follow PEP 8 (4-space indent, 79-char line limit where practical, hanging indents for wrapped keyword args).
- Keep functions focused; split long helpers (like `_copy_and_convert_directory`) into smaller pieces before calling them.
- Prefer `pathlib.Path` instead of string paths when manipulating files; convert to `str()` only when interacting with APIs that demand it.
- Use `f`-strings for readability, especially when building exception messages, CLI output, or logging entries.
- Use `with` statements for temporary directories and tar/zip archives to ensure cleanup.

### Type & Static Hints
- Add explicit return types to all top-level functions (`-> dict`, `-> int`, `-> None`, etc.).
- Use `Optional[...]` and `list[...]` from `typing` or native generics (`list[str]`) to document expected shapes.
- Annotate all parameters—especially dictionary inputs used for templating—so future static analysis (mypy/pylint) can infer structure.
- Document dictionary returns with key-level descriptions where keys carry statistical data.

### Naming & Semantics
- Keep function names descriptive and snake_case (e.g., `download_crs_rules`, `get_available_stacks`).
- Use clear variable names for directories (`stack_path`, `mods_dest`). Avoid single letters unless they are obvious loop variables (e.g., `for f in files`).
- Constants should be uppercase (`CRS_DOWNLOAD_URL`, `APACHECTL`). Group them near the top of each module.
- When building statistics dicts, choose keys that reflect the data (`files_copied`, `variables_substituted`), and document what they track.
- When naming CLI options/builder params, keep the option string and variable name aligned (e.g., `--config` / `config_dir`).

### Docstrings & Comments
- Every public/top-level function gets a triple-quoted docstring describing:
  1. What it does.
  2. Arguments (names + short description).
  3. Return value type.
  4. Exceptions raised (if not obvious).
- Inline comments should explain *why* something happens, not *what* (`# Remove template extension before writing` is fine). Avoid redundant comments.
- Block diagrams or CLI instructions can live inside `if __name__ == "__main__"` sections, as `config_generator.py` already demonstrates.
- Keep module-level docstrings concise but descriptive about the generator’s or API’s responsibilities.

### Error Handling
- Raise `FileNotFoundError`, `FileExistsError`, or `HTTPException` as appropriate; avoid catching plain `Exception` unless you wrap/re-raise it with context.
- When raising for HTTP responses, include descriptive `detail` text for downstream callers (FastAPI surfaces it). Prefer `HTTPException(status_code=400, detail="...")` for client errors.
- Wrap external calls (`requests.post`, `urllib.request.urlopen`) in try/except blocks that translate failures into repository-specific messages.
- Validate preconditions early (templates directory exists, config path exists) and raise before making changes.
- When touching the filesystem, ensure parent directories exist (`mkdir(parents=True, exist_ok=True)`) before writing files.

### Files & Templates
- Convert `.template` files to `.conf` by stripping `.template` and appending `.conf` unless the target name already ends with `.conf`.
- Prefer `safe_substitute` for `string.Template` to leave unmatched placeholders untouched but log the substitution count when necessary.
- Track substitution statistics (e.g., increment `variables_substituted` when processed content differs from source).
- Always read/write text files with `encoding="utf-8"` to avoid locale issues.
- Keep templates focused: each stack’s `apache/` subdirectory should map directly to the generated `config/apache/` tree.

### HTTP & API Integrations
- Bundle API requests in helper functions (`send_config`) rather than performing logic inline in scripts.
- Always handle non-200 responses by parsing JSON when possible and falling back to raw text.
- Keep API endpoints minimal: `POST /config` should validate `.zip` uploads, extract to a temp directory, and copy *only* files.
- When copying configs, mirror directory structures via `rglob` and `relative_to` so path traversal bugs are impossible.

### Git & Contributions
- Generated `config/`, downloaded CRS rules, and built containers should remain out of commits; add `.gitignore` entries if new artifacts appear.
- Keep `templates/` as the single source of truth; avoid duplicating values between stacks/apps.
- If you bump versions (e.g., CRS, ModSecurity, base image), ensure `container/Dockerfile`, bin scripts, and AGENTS instructions stay in sync.
- Don't edit files inside `config/`; regenerate via `python config_generator.py` or `sender.py`.

## Configuration Workflows

- Templates live under `templates/stacks/<stack>` and `templates/apps/<app>` with their own `defaults.yaml`.
- Run `python config_generator.py` to regenerate `config/` and inspect the `stats` output for directory/file counts.
- Use `generate_config(overwrite=True, apps=[...], crs_version="<semver>")` programmatically when scripting new deployments.
- If adding an app, add its manifest under `templates/apps/<name>` and ensure `defaults.yaml` is evergreen.
- Maintain `custom/crs` + `custom/apps` folders to store user overrides, and always create placeholder `before/after` files when generating configs.

## Operational Reminders for Agents

- When you need to inspect runtime config, copy files from `config/` into the container via `docker compose cp` rather than editing inside the running image.
- The FastAPI endpoint expects a ZIP file named `config.zip`. `sender.py` already constructs it correctly; reuse that logic in tests.
- For manual certificate regeneration, rerun `/usr/local/bin/generate-certificate` inside the container before starting Apache if you need fresh certs.
- If you automate deployments, stop the container before overwriting `/etc/modsecurity.d/` to avoid race conditions with Apache.
- When configuring Apache, run `docker compose exec modsecurity-waf /usr/local/apache2/bin/apachectl -t` after copying new files from `config/apache`.
- Track `MODSEC_RULE_ENGINE` and `BLOCKING_PARANOIA` values carefully when toggling detection/blocking modes.
- Use `container/bin/healthcheck` as a reference implementation for service probes; mirror its logic when adding new monitoring scripts.

<i>This AGENTS.md is intentionally verbose to help future agents understand the mechanical, stylistic, and operational quirks of this repository.</i>
