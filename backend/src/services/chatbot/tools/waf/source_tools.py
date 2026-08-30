"""
Read-only access to the ORIGINAL configuration files, as extracted from the WAF container.

The analysis tools query the compiled dump; these read the source it was compiled from.
That is the difference between "what is Apache running" and "what do I edit to change it",
and only the second can be acted on by a human.

# Isolation

Every tool resolves its root from `ChatContext.configuration_id` **at call time**, so the
files reachable in a turn are exactly the files of the configuration the conversation is
bound to. This is deliberately the same binding the analysis tools use rather than a second
mechanism: langchain's FilesystemFileSearchMiddleware takes its `root_path` as a constructor
argument, which would mean the isolation invariant had two sources of truth — the graph
build and the invocation context — and could silently drift apart. One source, checked on
every call.

Containment uses `Path.resolve().is_relative_to(root)`, which resolves symlinks and cannot
be fooled by a shared prefix (`config_5` vs `config_55`) the way `str.startswith` can — see
`AnalysisService._resolve`, which predates this and uses the weaker form on parser-supplied
paths.

Paths crossing the tool boundary are VIRTUAL: rooted at the configuration, so
`/conf/common/macros/aaa-security.conf`, never `/app/storage/configs/config_5/...`. The
model is therefore unable to express another configuration's path, let alone read one.

# No writing

Read, search, list. Nothing here creates or modifies a file: the agent recommends an edit in
the chat and a human applies it. An LLM with write access to a customer's WAF configuration
is not a trade worth making for the convenience.
"""

import fnmatch
import logging
import os
import re
from pathlib import Path
from typing import Optional

from langchain.tools import ToolRuntime, tool

from shared.config import settings
from services.configmanager.storage import ConfigFileStorage
from ...context import ChatContext, ConfigurationUnavailable

logger = logging.getLogger(__name__)

# These bound what one call can put back into the context window. A WAF config is small
# (~200 files, ~1 MB) so the caps are about the model's budget, not the filesystem's.
# Sized against the TOKENS-PER-MINUTE budget, not the context window: an agent resends the
# whole conversation at every step, so each of these payloads is billed once per remaining
# step. See context.DEFAULT_LIMIT for the measurement.
MAX_MATCHES = 30
MAX_READ_LINES = 120
MAX_LINE_CHARS = 220
MAX_FILE_BYTES = 2_000_000


def _root(runtime: ToolRuntime[ChatContext]) -> Path:
    """The extracted source tree of the configuration this conversation is bound to."""
    cid = runtime.context.configuration_id
    try:
        return Path(ConfigFileStorage(settings.STORAGE_ROOT).get_extracted_path(cid)).resolve()
    except FileNotFoundError:
        raise ConfigurationUnavailable(
            f"The original files for configuration {cid} are not available on disk, so I "
            f"cannot read its source. The compiled configuration is still queryable."
        )


def _resolve(root: Path, virtual: str) -> Path:
    """
    Map a path onto the real tree, refusing anything that escapes the root.

    Accepts BOTH forms the agent will hold, because it gets them from different tools and
    cannot be expected to convert between them:
      - virtual, rooted at the configuration:  /conf/common/apps/jira.conf
      - as recorded in the dump and returned by get_provenance, i.e. the path inside the
        WAF container:                         /etc/httpd/conf/common/apps/jira.conf

    Anything containing "/conf/" is re-rooted from that segment, which is the same mapping
    the parser and AnalysisService use. Without this the agent loops: provenance hands it a
    dump path, the read fails, and it starts guessing filenames.
    """
    cleaned = virtual.replace("\\", "/")
    # Refuse traversal BEFORE the /conf/ mapping below. Without this, a path like
    # "../../config_9/extracted/conf/httpd.conf" contains "/conf/", gets re-rooted, and
    # quietly returns the BOUND configuration's httpd.conf instead. Not a leak, but
    # answering a different question than the one asked is its own kind of wrong.
    if ".." in cleaned.split("/"):
        raise ConfigurationUnavailable(
            f"Path {virtual!r} is not allowed. Give a path inside this configuration, with "
            f"no '..' segments."
        )
    if "/conf/" in cleaned:
        candidate = (root / "conf" / cleaned.split("/conf/", 1)[1]).resolve()
    else:
        candidate = (root / cleaned.lstrip("/")).resolve()
    if not (candidate == root or candidate.is_relative_to(root)):
        raise ConfigurationUnavailable(
            f"Path {virtual!r} is outside this configuration. You can only read the files "
            f"of the configuration this conversation is bound to."
        )
    return candidate


def _virtual(root: Path, real: Path) -> str:
    return "/" + str(real.relative_to(root))


def _guarded(fn):
    """Failures become a sentence the agent can relay, never an exception ending the turn."""
    try:
        return fn()
    except ConfigurationUnavailable as e:
        return {"error": str(e)}
    except Exception as e:                       # noqa: BLE001
        logger.exception("Chatbot source tool failed")
        return {"error": f"That failed: {type(e).__name__}: {e}"}


def _walk(base: Path, root: Path):
    """Every readable file under `base`, skipping anything that leaves the root."""
    for dirpath, _dirnames, filenames in os.walk(base):
        for name in filenames:
            p = Path(dirpath) / name
            try:
                rp = p.resolve()
            except OSError:
                continue
            # Re-checked per result: a symlink inside the tree could still point out of it.
            if not rp.is_relative_to(root):
                continue
            if rp.is_file() and rp.stat().st_size <= MAX_FILE_BYTES:
                yield rp


@tool
def grep_config(
    runtime: ToolRuntime[ChatContext],
    pattern: str,
    path: str = "/",
    include: Optional[str] = None,
    case_sensitive: bool = False,
) -> dict:
    """
    Search the ORIGINAL configuration files for a regex, returning matching lines.

    Case-INSENSITIVE by default, because Apache directive names are case-insensitive and the
    files do not agree with themselves: `SecRuleRemoveByID` and `SecRuleRemoveById` both
    occur. Only pass case_sensitive=True when the case genuinely matters.

    IMPORTANT — a miss is not proof of absence. These are the files BEFORE macro expansion,
    so text that exists in the compiled configuration often appears nowhere here: the block
    the dump calls `<Location /jira/secure/>` is written `<Location $frontPath/>` in the
    source. If you do not find something you know exists, it is macro-generated; use
    get_provenance to find the file, do not report it as missing.

    `path` narrows to a subtree, `include` is a filename glob such as "*.conf". Paths may be
    given either as returned here (/conf/...) or as get_provenance reports them
    (/etc/httpd/conf/...); both resolve to the same file.
    """
    def run():
        root = _root(runtime)
        base = _resolve(root, path)
        try:
            rx = re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regular expression {pattern!r}: {e}"}

        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = _walk(base, root)
        else:
            return {"error": f"No such path in this configuration: {path!r}"}

        matches, total = [], 0
        for f in files:
            if include and not fnmatch.fnmatch(f.name, include):
                continue
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    for n, line in enumerate(fh, start=1):
                        if rx.search(line):
                            total += 1
                            if len(matches) < MAX_MATCHES:
                                matches.append({
                                    "file": _virtual(root, f),
                                    "line": n,
                                    "text": line.rstrip("\n")[:MAX_LINE_CHARS],
                                })
            except OSError:
                continue

        return {
            "pattern": pattern,
            "case_sensitive": case_sensitive,
            "total_matches": total,
            "shown": len(matches),
            "matches": matches,
            "note": (
                "No match. Remember these are pre-expansion source files: anything built by "
                "a macro will not appear literally. Try get_provenance instead of concluding "
                "it is absent." if total == 0 else None
            ),
        }
    return _guarded(run)


@tool
def glob_config(runtime: ToolRuntime[ChatContext], pattern: str = "**/*.conf", path: str = "/") -> dict:
    """
    List files in the ORIGINAL configuration tree matching a glob (e.g. "**/*.conf").

    Use this to see how the configuration is laid out before searching it — which files
    exist, how they are grouped. Paths returned are rooted at the configuration.
    """
    def run():
        root = _root(runtime)
        base = _resolve(root, path)
        if not base.is_dir():
            return {"error": f"Not a directory in this configuration: {path!r}"}
        found = sorted(
            _virtual(root, p) for p in _walk(base, root)
            if fnmatch.fnmatch(_virtual(root, p), pattern if pattern.startswith("/") else "/" + pattern)
            or fnmatch.fnmatch(p.name, pattern)
        )
        return {
            "pattern": pattern,
            "total": len(found),
            "files": found[:MAX_MATCHES],
            "truncated": len(found) > MAX_MATCHES,
        }
    return _guarded(run)


@tool
def read_config_file(
    runtime: ToolRuntime[ChatContext],
    path: str,
    offset: int = 1,
    limit: int = 60,
) -> dict:
    """
    Read a slice of one ORIGINAL configuration file, with line numbers.

    Use it after grep_config or get_provenance to see the context around a hit — the whole
    <Macro> body it sits in, or what a <Location> block already contains before you suggest
    adding a line to it. `offset` is a 1-based line number; `limit` caps the lines returned.

    The line numbers here are REAL, read from the file. Prefer them to the line recorded in
    a provenance chain, which is approximate for macro-expanded directives.

    `path` accepts either the /conf/... form returned by these tools or the
    /etc/httpd/conf/... form that get_provenance reports; both find the same file.
    """
    def run():
        root = _root(runtime)
        target = _resolve(root, path)
        if not target.is_file():
            return {"error": f"No such file in this configuration: {path!r}. "
                             f"Use glob_config to see what exists."}
        if target.stat().st_size > MAX_FILE_BYTES:
            return {"error": f"{path!r} is too large to read."}

        n_lines = max(1, min(int(limit or 1), MAX_READ_LINES))
        start = max(1, int(offset or 1))
        out, total = [], 0
        with open(target, "r", encoding="utf-8", errors="replace") as fh:
            for n, line in enumerate(fh, start=1):
                total += 1
                if start <= n < start + n_lines:
                    out.append({"line": n, "text": line.rstrip("\n")[:MAX_LINE_CHARS]})
        return {
            "file": _virtual(root, target),
            "total_lines": total,
            "from_line": start,
            "lines": out,
            "truncated": total > start + n_lines - 1,
        }
    return _guarded(run)


SOURCE_TOOLS = [grep_config, glob_config, read_config_file]
