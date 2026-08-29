"""
The source tools must never reach outside the conversation's own configuration.

This is the whole security property of giving an agent filesystem access, and it is not
something to take on faith from a code reading: the tools take a model-supplied `path`, and
a model will eventually send `../`. Every escape route is tried here against real storage.
"""

import os
import sys
from pathlib import Path

import pytest
from langchain.tools import ToolRuntime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from shared.config import settings                                    # noqa: E402
from services.configmanager.storage import ConfigFileStorage          # noqa: E402
from services.chatbot.context import ChatContext                      # noqa: E402
from services.chatbot.tools.waf import grep_config, glob_config, read_config_file  # noqa: E402

BOUND = 5        # the conversation's configuration
OTHER = 3        # a different one that also exists on disk


def _runtime(cid):
    """
    The ToolRuntime the agent's ToolNode would inject.

    It is not injected on a direct `.invoke()`, so the test builds one; only `context` is
    read by these tools, but the dataclass requires the rest.
    """
    return ToolRuntime(
        context=ChatContext(configuration_id=cid, user_id=1),
        state=None, config=None, stream_writer=lambda *a, **k: None,
        tool_call_id="t", store=None,
    )


def _run(tool, cid=BOUND, **kwargs):
    """Call a tool the way the agent does, bound to one configuration."""
    return tool.func(runtime=_runtime(cid), **kwargs)


def _roots():
    st = ConfigFileStorage(settings.STORAGE_ROOT)
    return Path(st.get_extracted_path(BOUND)), Path(st.get_extracted_path(OTHER))


pytestmark = pytest.mark.skipif(
    not os.path.isdir(settings.STORAGE_ROOT), reason="storage not mounted"
)


# --- escaping the root -------------------------------------------------------------

ESCAPES = [
    "../../config_3/extracted",
    "/../../config_3/extracted",
    "../..",
    "/etc",
    "../../../../etc",
    "../../../../etc/passwd",
    "/app/storage/configs/config_3/extracted",
    "conf/../../../config_3",
    "//etc",
    "/conf/../../../../etc",
]


def _blocked(out) -> bool:
    """
    A refused call either errors or comes back empty.

    Asserting the offending path is absent from the output does NOT work: the error message
    quotes it back, so `"config_3" not in out` fails on a correctly blocked call. What
    matters is that no bytes from outside the root came back.
    """
    if isinstance(out, dict) and out.get("error"):
        return True
    return not (out.get("matches") or out.get("files") or out.get("lines"))


@pytest.mark.parametrize("path", ESCAPES)
def test_grep_cannot_escape_the_bound_configuration(path):
    out = _run(grep_config, pattern="root", path=path)
    assert _blocked(out), out
    assert "root:x:" not in str(out)                 # no /etc/passwd contents


@pytest.mark.parametrize("path", ESCAPES)
def test_glob_cannot_escape_the_bound_configuration(path):
    out = _run(glob_config, pattern="**/*", path=path)
    assert _blocked(out), out
    assert "passwd" not in str(out.get("files", []))


@pytest.mark.parametrize("path", ESCAPES + ["/etc/passwd", "/etc/hosts",
                                            "../../config_3/extracted/conf/httpd.conf"])
def test_read_cannot_escape_the_bound_configuration(path):
    out = _run(read_config_file, path=path)
    assert _blocked(out), out
    assert "root:x:" not in str(out)


# --- the positive case still works -------------------------------------------------

def test_grep_finds_a_known_line_case_insensitively():
    """`SecRuleRemoveById` must find `SecRuleRemoveByID` — Apache is case-insensitive."""
    out = str(_run(grep_config, pattern="SecRuleRemoveById 5000402"))
    assert "aaa-security.conf" in out


def test_read_returns_real_line_numbers():
    out = str(_run(read_config_file, path="/conf/common/apps/jira.conf", offset=30, limit=10))
    assert "jira.conf" in out and "'line': 30" in out.replace('"', "'")


# --- results never carry the real filesystem layout --------------------------------

def test_paths_returned_are_virtual():
    """The model must not learn where configurations live, or it can name another one."""
    out = str(_run(grep_config, pattern="SecRuleRemoveByID"))
    assert str(settings.STORAGE_ROOT) not in out
    assert "config_5" not in out


# --- the binding, not the caller, decides which files are visible ------------------

def test_same_call_reads_different_files_per_configuration():
    """
    Identical arguments, two bound configurations -> two roots.

    Config 3 and 5 happen to hold the same files, so compare the roots the tool resolves
    rather than the content.
    """
    from services.chatbot.tools.waf.source_tools import _root

    r5, r3 = _roots()
    assert _root(_runtime(BOUND)) == r5.resolve()
    assert _root(_runtime(OTHER)) == r3.resolve()
    assert _root(_runtime(BOUND)) != _root(_runtime(OTHER))
