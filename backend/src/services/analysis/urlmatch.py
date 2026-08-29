"""
Match a request path against a configuration's stored location containers.

Answers "which `<Location>` / `<LocationMatch>` blocks does this URL fall into" — the
question you have when a log line names a URL and you need the rules that applied to it.
On a full configuration that is 601 patterns, 545 of them regexes, so it is not a question
anyone answers by reading.

Pure functions, no I/O: the caller supplies the (value, kind, count) rows. That keeps the
Apache semantics below testable without a database.

TWO REASONS THIS CANNOT BE A CYPHER `=~`:

  - Flavour and anchoring. Apache uses PCRE and `<LocationMatch>` is an unanchored SEARCH;
    Cypher's `=~` is Java-flavoured and matches the WHOLE string. `(?i)/php/` would stop
    matching `/foo/php/bar`.
  - `<Location>` is not a regex at all. It is a path-component prefix, which cannot be
    expressed in Cypher against a stored value.

AND WHY `regex` RATHER THAN `re`: Apache/PCRE allows inline flags mid-pattern, as in
`/(?i)(?:TestSecAllow)?SOAP`. The standard library rejects that -- "global flags not at the
start of the expression" -- and fails on 56 of this configuration's 545 patterns. The
`regex` module accepts all 545 and agrees with `re` on every pattern both can compile.
It is pinned in requirements.txt for that reason; do not swap it back.
"""

import logging
from typing import Iterable, List, NamedTuple, Optional, Tuple
from urllib.parse import urlsplit

import regex

logger = logging.getLogger(__name__)

# Apache's shell wildcards for <Location>. Their presence switches the value from a path
# prefix to a full anchored match -- see _location_matches.
_WILDCARDS = set("*?")

# Regex-only metacharacters. A <Location> containing these was almost certainly meant to be
# a <LocationMatch>: Apache supports ? and * here and nothing else, so `(?:a|b)` is matched
# as those literal characters, not as an alternation.
_REGEX_ONLY_CHARS = set("()[]|^$\\+")

LOCATION = "Location"
LOCATION_MATCH = "LocationMatch"


class LocationPattern(NamedTuple):
    """One distinct location container, ready to test paths against."""
    value: str                       # raw, as stored -- what the filter needs back
    kind: str                        # Location | LocationMatch
    count: int                       # directives inside it
    warning: Optional[str] = None    # why it can never match, if so


def strip_quotes(value: str) -> str:
    """
    Drop the quotes the dump preserved around some values.

    17 LocationMatch and 3 Location values arrive as `"..."`. Same convention as the
    frontend's displayValue, kept in step deliberately.
    """
    if len(value) > 1 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def normalise(url: str) -> str:
    """
    Reduce whatever was pasted to the request path.

    Accepts a full URL (`https://host/jira/x?a=1#f`) or a bare path (`/jira/x`), and keeps
    only the path. The host is deliberately dropped: `VirtualHost` in this graph holds bind
    specs (`*:80`, `_default_:443`), not hostnames, so a log's host has nothing to match
    against. Query and fragment are dropped because Apache matches location containers on
    the path.
    """
    url = (url or "").strip()
    if not url:
        return ""
    # urlsplit only treats it as a URL when a scheme is present; a bare path stays a path.
    path = urlsplit(url).path if "://" in url else url.split("?")[0].split("#")[0]
    if not path:
        return "/"
    if not path.startswith("/"):
        # A pasted `host/path` with no scheme: keep everything from the first slash.
        path = "/" + path.split("/", 1)[1] if "/" in path else "/" + path
    return path


def _location_matches(pattern: str, path: str) -> bool:
    """
    Apache `<Location>` semantics. Verified against a real Apache 2.4.62, not just the docs.

    Two modes, and which one applies depends on whether the value contains a wildcard:

      NO WILDCARD -- a path-component PREFIX.
          `/wp` covers `/wp`, `/wp/`, `/wp/a/b/c`; NOT `/wpfoo`. The boundary is a path
          separator, not a character offset.

      `*` or `?` PRESENT -- a FULL match, anchored at both ends, where neither wildcard
      crosses a `/`:
          `/star*` covers `/star` (`*` matches zero characters) and `/starABC`;
          NOT `/starABC/deeper` (no prefix behaviour once wildcards are in play) and
          NOT `/xstarABC` (anchored at the start).
          `/q?c` covers `/qxc`; NOT `/q/c` and NOT `/qxxc` (`?` is exactly one character).

    A value not starting with `/` can never match: an origin request's URL-path always
    begins with one, and a proxy request's is `scheme://host/path`, which begins with the
    scheme.
    """
    if not pattern.startswith("/"):
        return False

    if _WILDCARDS & set(pattern):
        # Translate the shell wildcards to an anchored regex. [^/] rather than . is the
        # whole point: Apache's docs say neither wildcard matches a / in the URL-path, and
        # the live server agrees.
        built = "".join(
            "[^/]*" if ch == "*" else "[^/]" if ch == "?" else regex.escape(ch)
            for ch in pattern
        )
        return regex.fullmatch(built, path) is not None

    base = pattern.rstrip("/")
    if base == "":                        # `<Location />`
        return True
    return path == base or path.startswith(base + "/")


def prepare(rows: Iterable[Tuple[str, str, int]]) -> List[LocationPattern]:
    """
    Turn (value, kind, count) rows into patterns, flagging the ones that cannot match.

    A `<LocationMatch>` whose regex will not compile is flagged rather than dropped: a
    silently missing pattern is indistinguishable from one that genuinely did not match.
    """
    out: List[LocationPattern] = []
    for value, kind, count in rows:
        pattern = strip_quotes(value)
        warning = None

        if kind == LOCATION_MATCH:
            try:
                regex.compile(pattern)
            except regex.error as e:
                warning = f"not a valid pattern: {e}"
        else:
            # Two distinct problems, stated at their real strength. Both confirmed against
            # a live Apache 2.4.62 rather than inferred.
            if not pattern.startswith("/"):
                # Definite. A URL-path always begins with '/', and a proxy request's URL
                # begins with its scheme, so nothing can ever match this.
                warning = ("does not start with '/', so no request path can match it — "
                           "a leading '/' is probably missing")
            elif _REGEX_ONLY_CHARS & set(pattern):
                # NOT "never": Apache reads ? and * here as shell wildcards, so a value like
                # /auth/(?:health|metrics|welcome) does match the literal path
                # /auth/(X:health|metrics|welcome) -- just nothing anyone would request.
                # Deliberately not overstated; the config author meant <LocationMatch>.
                warning = ("looks like a regex, but <Location> only supports the wildcards "
                           "? and * (neither crosses '/') — it matches those characters "
                           "literally, so no realistic URL hits it. Probably meant to be "
                           "<LocationMatch>")

        out.append(LocationPattern(value=value, kind=kind, count=count, warning=warning))
    return out


def match(path: str, patterns: Iterable[LocationPattern]) -> List[LocationPattern]:
    """
    Every pattern whose container covers `path`, commonest first.

    A warning does NOT exclude a pattern. Warnings are advice about a container that looks
    misconfigured; whether it matches is still decided by Apache's rules. Skipping them
    would make this disagree with the server for a value like
    `/auth/(?:health|metrics|welcome)`, which really does match the literal path
    `/auth/(X:health|metrics|welcome)`. Only a pattern that cannot be EVALUATED is skipped.
    """
    if not path:
        return []

    hits: List[LocationPattern] = []
    for p in patterns:
        body = strip_quotes(p.value)
        try:
            if p.kind == LOCATION_MATCH:
                # search(), not match(): Apache's LocationMatch is unanchored.
                found = regex.search(body, path) is not None
            else:
                found = _location_matches(body, path)
        except regex.error:
            # The only reason to drop a pattern: it cannot be evaluated at all. prepare()
            # has already flagged it, so the caller still sees it in the warnings.
            logger.warning("Skipping uncompilable location pattern %r", p.value)
            continue
        if found:
            hits.append(p)

    hits.sort(key=lambda p: (-p.count, p.value))
    return hits
