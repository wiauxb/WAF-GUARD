# The WAF-GUARD Parser

How the configuration parser works, and what is wrong with it.

This document describes the parser being ported from `old/services/analyzer/` into
`backend/src/services/parser/`. The port is **faithful** — same behaviour, same bugs —
so this document is what you read before deciding which defects to fix.

Every measurement below comes from the real configuration in
`backend/src/storage/configs/config_5/` (a 124 MB dump, 277,187 lines, 92,443 directives,
48,792 SecRules). Reproduction commands are included so you can re-check any figure.

---

## 1. What the parser does

```
config.zip ──▶ WAF container ──▶ dump.conf ──▶ PARSER ──┬──▶ Neo4j    (what directives mean)
              (httpd -DDUMP_CONFIG)                     └──▶ Postgres (where they came from)
```

The parser never reads your configuration files as its primary input. It reads the
**compiled dump** that Apache itself produces via `httpd -t -DDUMP_CONFIG`.

That matters, and it is the single best design decision in the old system. An Apache +
ModSecurity configuration is not a static document — it is a program. `Include` pulls in
files by glob, `<IfDefine>` and `<IfModule>` switch blocks on and off, and `<Macro>` /
`Use` expand parameterised templates, often nested many levels deep. Reading the `.conf`
files directly would mean reimplementing Apache's own evaluation semantics, and getting
it subtly wrong.

Instead the WAF container runs a real Apache, which resolves all of that and prints the
fully expanded configuration — every directive, in evaluation order, annotated with where
it came from. The parser's job is to read that expansion back and rebuild the link from
each flattened directive to its original source location.

The parser only writes. Everything that *reads* the result is `AnalysisService`.

---

## 2. The dump format

Apache emits three kinds of line.

**Directive lines** — the actual configuration, fully expanded:

```apache
DefineStr IncidentServerId  node1
SecRule REMOTE_ADDR "^(?:127.0.0.1)$" "phase:1,t:none,setvar:tx.c_=%{IP.blocked},..."
```

**File markers** (`# In file:`) — which source file the following directives came from:

```apache
# In file: /etc/httpd/conf/machine/node.conf
```

**Instruction numbers** (`#  N:`) — the line number within that source file:

```apache
#   1:
```

So the simplest case reads:

```apache
# In file: /etc/httpd/conf/machine/node.conf
#   1:
DefineStr IncidentServerId  node1
```

→ *this `DefineStr` is line 1 of `node.conf`*.

### Macro expansion chains

When a directive comes from inside a `<Macro>`, the file marker becomes a **nested
chain**, innermost first:

```
# In file: macro 'secrule' (defined on line 58 of ".../macros/aaa-security.conf")
           used on line 1 of "macro 'secrulegtbig_' (defined on line 165 of ".../rules.conf")
           used on line 1 of "macro 'secrulegtbig' (defined on line 175 of ".../rules.conf")
           used on line 5 of "macro 'secrequestbodylimit' (defined on line 84 of ".../aaa-security.conf")
           used on line 39 of "/etc/httpd/conf/common/security/config.conf""""
```

Read outward: the `secrule` macro was used by `secrulegtbig_`, which was used by
`secrulegtbig`, which was used by `secrequestbodylimit`, which was finally used at line 39
of `config.conf`. Reconstructing this chain is what makes "show me where this rule really
comes from" possible in the UI.

In `config_5` these chains reach **15 levels deep**:

```
depth: 0      1      2      3      4      5      6      7      8     9     10    11    12   13   14  15
       1,411  4,551  6,248  5,497  8,853  15,302 14,557 9,657  6,584 6,275 6,023 4,416 1,901 624  478 66
```

Only 1.5% of directives sit directly in a file. **98.5% come from inside at least one
macro.** Keep that number in mind for defect #2.

---

## 3. The scanner

`parse_compiled_config` (`core/dump_parser.py`, was `old/.../analyzer.py`) is a single
line-by-line pass holding a small amount of state:

| State | Set by | Cleared by |
|-------|--------|-----------|
| `current_virtualhost` | `<VirtualHost …>` | `</VirtualHost>` |
| `current_location` | `<Location …>` | `</Location>` |
| `current_if_level` | `<If …>` (+1) | `</If>` (−1) |
| `current_if_conditions` | `<If …>` (push) | `</If>` (pop) |
| `current_context` | `# In file:` | never — overwritten |
| `current_node_id` | every directive (+1) | never |

For each line it tries, in order: VirtualHost open/close, Location open/close, `<If>`
open/close, file marker, instruction number, `SecRule`, then a generic directive.

When a directive line matches, it increments `node_id` and hands everything to
`DirectiveFactory.create`, which picks a subclass and returns a `Directive` object.

`node_id` is simply a counter. It is the join key between Neo4j and Postgres, and because
the dump is in evaluation order, **`node_id` ordering is execution ordering** — which is
what makes "these rules run in this sequence" answerable.

---

## 4. The context chain

Two classes model provenance (`core/context.py`):

- **`FileContext(line_num, file_path)`** — a real file and line.
- **`MacroContext(macro_name, definition, use)`** — a macro frame: where it is *defined*
  (a `FileContext`) and where it is *used* (the next link outward).

The regex parses the chain innermost-first into a flat list, then a fix-up loop walks it
**backwards** to relink each frame's `.use` pointer to the next frame outward, so the
result is a proper linked list terminating in a `FileContext`.

`FileContext.to_real_path()` translates a dump path into a path on our disk. The dump says
`/etc/httpd/conf/common/macros.conf` (where the file lived inside the WAF container); the
extracted copy is at `storage/configs/config_{id}/extracted/conf/common/macros.conf`. The
translation rewrites everything up to and including `conf/` with our local root.

> **Port change.** The old code read that root from a global `os.environ["CONFIG_ROOT"]`.
> The new backend can parse two configurations at once in one process, so a global would
> let one parse resolve another's files. `config_root` is now passed in explicitly and
> carried on `FileContext`. This is the only behavioural change made during the port.

This chain is what populates `symbol_table`, `macro_definitions` and `macro_calls`, and
what `AnalysisService.get_macro_call_trace` walks to answer "where does this rule come
from?".

---

## 5. Constant and variable recovery

The hardest part, and the cleverest. `core/const_recovery.py`.

**The problem.** Given `SecRule %{tx.blocked} …` inside a macro, the interesting question
is not "this rule uses `tx.blocked`" but "*which actual constant* was passed in, five
macro levels up?" Macros take positional parameters, so a constant named at the outermost
call site arrives at the directive under a completely different name.

**The approach** — a backward taint analysis over the macro chain:

1. Start at the directive's own source line. Every argument is "interesting".
2. Find `$param` / `@param` tokens in the interesting arguments. Skip ModSecurity
   operators (`@rx`, `@eq`, …) and Apache regex backreferences (`$0`–`$9`), which look
   identical but are not parameters.
3. Look up which **positions** those parameters occupy in the enclosing macro's
   signature. Those positions are now "tinted".
4. Step outward to the call site. Read the actual arguments at the tinted positions.
5. Extract `${…}`, `%{…}`, `~{…}` references from them — these are real constants.
6. Repeat until the chain terminates in a file.

Two helper functions implement this: `tint_macro_def` (steps 2–3) and `extract_constants`
(step 5). `Macro.parse_macro_def` reads the `<Macro name arg1 arg2>` line to get the
formal parameter list.

Finally `DirectiveFactory.create` sorts the results:

| Extracted `(collection, name)` | Classified as |
|---|---|
| collection is a known ModSecurity collection (`TX`, `ARGS`, `ENV`, …) | **variable** |
| collection is non-empty but unknown | **constant**, named `collection.name` |
| collection is empty | **constant**, named `name` |

This is also the single most expensive part of the parser — see defect #8.

---

## 6. Directive subtypes

`DirectiveFactory` picks a class by directive name. All of them parse `id:`, `tag:`,
`phase:` and `msg:` from the argument text; the subclasses add more.

| Class | Matches | Additionally extracts |
|-------|---------|----------------------|
| `Directive` | anything else | — |
| `SecRule` | `SecRule` | target variables, operator, actions, and all `setvar:` / `setenv:` assignments including unsets |
| `DefineStr` | `DefineStr`, `SetEnv` | constant name and value |
| `SecRuleRemoveById` | `SecRuleRemoveById` | individual IDs and ID ranges (ranges wider than 2500 are skipped) |
| `SecRuleRemoveByTag` | `SecRuleRemoveByTag` | tag patterns (regexes) |

---

## 7. What lands where

**PostgreSQL — provenance.** `symbol_table` (file path + line number per node),
`macro_definitions` (name → defining symbol), `macro_calls` (call sites). This answers
"where in my files did this come from" and "what produced this line".

**Neo4j — semantics.** One node per directive, labelled with the lowercased directive name
(`secrule`, `definestr`, …), plus shared value nodes (`:Constant`, `:Tag`, `:Id`,
`:Location`, `:VirtualHost`, `:Phase`, `:Variable`, `:Collection`, `:Regex`) connected by
`Uses`, `Sets`, `Define`, `DoesRemove`, `Has`, `AtLocation`, `InVirtualHost` and friends.
This answers "which rules apply here", "what removed this rule", "what uses this constant".

The full graph model — labels, properties, relationships, indexes — is documented in
[DOC.md → Neo4j Graph Schema](DOC.md).

> **Port change.** The old analyzer wiped both databases before every run
> (`DROP SCHEMA public CASCADE` plus a full Neo4j `DETACH DELETE`), so it only ever held
> one configuration. Every node now carries `configuration_id`, included in every `MERGE`
> key, and clearing is scoped to a single configuration.

### Measured end to end

A full run of `config_5` through the ported service:

| | |
|---|---|
| directives parsed | 92,443 |
| Neo4j nodes | 96,939 |
| `symbol_table` rows | 650,279 — of which 92,443 carry a node_id, 557,836 are macro frames |
| `macro_definitions` | 876 |
| `macro_calls` | 556,960 |
| **wall time** | **15.5 min** — 56 s parsing, ~14.5 min writing |
| peak RSS | ~865 MB |

> ⚠️ **The write phase dominates, and that is worth a follow-up.** ~1.2M rows are inserted
> one at a time, each with its own `flush()` to obtain the id that the next row's foreign
> key needs. The old code had the same per-row shape (psycopg2 `PREPARE` + one `EXECUTE`
> per row), so this is not a regression introduced by the port — but nothing forces it to
> stay that way. Batching the symbol inserts with `RETURNING` would cut the round trips by
> orders of magnitude. Independent of defects #7 and #8, which concern the parse phase.

---

## 8. Defects

Ordered by measured impact. Numbers refer to `config_5`.

Line references point at the original code in `old/`; the ported copies under
`backend/src/services/parser/core/` are identical.

---

### 🔴 #1 — `<LocationMatch>` is ignored entirely (80.2% of directives)

**The code.** The scanner has exactly one pattern for location containers:

```python
location_pattern = re.compile(r'[ \t]*<Location\s+(.*?)>')   # gérer locationMatch & directory
```

The trailing comment is the original author's own note: *handle LocationMatch & directory*.
It was never done. `<LocationMatch …>` does not match this pattern — after `<Location`
comes `Match`, not whitespace — so the block is invisible to the parser. The same is true
of `<Directory>`, `<DirectoryMatch>` and `<Proxy>`.

**Why it is wrong.** Directives inside an untracked container keep whatever
`current_location` was already set, which is almost always the empty string. They are
recorded as applying to *no location at all*.

**Measured impact.**

| | count | share |
|---|---:|---:|
| directives inside `<LocationMatch>` — recorded as `location=""` | **74,131** | **80.2%** |
| …of which are SecRules | **40,290** | |
| directives inside `<Location>` — correct | 9,720 | 10.5% |
| directives genuinely outside any location | 8,592 | 9.3% |

`config_5` contains 1,468 `<LocationMatch>` blocks against 217 `<Location>` — plus 14
`<Directory>`, 28 `<DirectoryMatch>` and 7 `<Proxy>`.

**What it means for you.** A real block from your dump:

```apache
<LocationMatch "^/SecError/>
  AddType "application/problem+json" "json"
  RewriteOptions InheritBefore
  RewriteRule "[.](?:json)$" - [E=fix-type:application/problem+json,NE,DPI]
</LocationMatch>
```

All three directives are stored with no location. Ask *"what applies to `/SecError/`?"* and
you get nothing back. Ask *"what applies globally?"* and you get these three plus 74,128
others that do not.

This is the input to `filter_directives_by_request` — the flagship analysis query, and the
chatbot's `filter_rule` tool. Built on today's data, it is right about 20% of the
configuration.

**Fixing it is not a one-liner**, because the two container types are semantically
different: `<Location />` is a literal path, `<LocationMatch ^/api>` is a regex. Matching a
request against them requires knowing which is which, so the container kind has to be
stored, not just its value.

```bash
# reproduce
grep -c '<LocationMatch' backend/src/storage/configs/config_5/dump.conf   # 1468
grep -c '<Location '     backend/src/storage/configs/config_5/dump.conf   # 217
```

---

### ✅ #2 — Macro context truncated on 98.5% of directives — RESOLVED by removal

**The code.** `context.py:54`:

```python
def __str__(self):
    return f"line {self.line_num} of " if self.line_num else "" + f"[{self.macro_name}](...)..."
```

**Why it is wrong.** Python parses this as `A if cond else ("" + B)`, not
`(A if cond else "") + B`. When `line_num` is set — which the scanner does for essentially
every directive — the whole macro description is discarded and only the prefix is returned.

Worse, the corruption **cascades**: the intact branch renders the next frame with
`{self.use}`, which is another `MacroContext` with the same bug.

**Measured impact.** 91,032 of 92,443 directives (98.5%) — every directive at macro depth
≥ 1. The `Context` string is stored as a property on each Neo4j node and surfaced in the UI.

**What it means for you.** For the deep chain shown in §2, this is what gets stored:

```
'line 7 of '
```

This is what the chain actually contains:

```
line 7 of [secrule](/etc/httpd/conf/common/macros/aaa-security.conf:58) used on line 1 of
  [secrulegtbig_](/etc/httpd/conf/common/macros/rules.conf:165) used on line 1 of
  [secrulegtbig](/etc/httpd/conf/common/macros/rules.conf:175) used on line 5 of
  [secrequestbodylimit](/etc/httpd/conf/common/macros/aaa-security.conf:84) used on line 39 of
  /etc/httpd/conf/common/security/config.conf:39
```

Every file, every line, every macro name — thrown away and replaced with `line 7 of `.

**Resolution (2026-08-25): the field was removed rather than repaired.**

The underlying data was never lost — `symbol_table` and `macro_calls` record the chain
correctly, which is why `get_macro_call_trace` can rebuild it. The `Context` property was
only ever a denormalised copy of that, and a broken one. Since
`GET /nodes/{id}/metadata` serves the same provenance accurately for 100% of directives,
the property earned nothing:

- `core/directives.py` no longer writes `Context` in `node_properties()`
- `analysis/queries.py` no longer projects it, and `DirectiveResponse` has no `context`
- Verified write-only beforehand: nothing matched, filtered or joined on it

No re-parse is required — existing graphs keep a vestigial property nothing reads, and it
disappears on the next parse.

`MacroContext.__str__` still carries the precedence bug, but it now only reaches parser
stderr messages (`directives.py` prints `from {context}` on malformed rules), not stored
data. A related nit if it is ever fixed: the correct rendering prints
`used on line 1 of line 1 of`, because the frame prints `self.use.line_num` and then
`str(self.use)`, which repeats it.

---

### 🟠 #3 — `SecRuleRemoveById` with only ranges produces no edges

**The code.** `query_factory.py:62-72`:

```cypher
UNWIND properties.ids_to_remove as id      -- if this list is empty…
MERGE (i:Id {value: id})
MERGE (node)-[:DoesRemove]->(i)

WITH node, properties                       -- …zero rows reach here
UNWIND range(0, properties.num_of_ranges-1) as range_i
...
```

**Why it is wrong.** `UNWIND []` produces zero rows, and in Cypher every subsequent clause
operates per-row. With no rows, the ranges block never executes.

**What it means for you.** `SecRuleRemoveById 900000-900100` — a range with no bare IDs —
creates the directive node but **no `DoesRemove` relationships at all**. "What removed rule
900050?" returns nothing, even though something did.

The fix is to run the two blocks as independent statements, or to expand ranges into
`ids_to_remove` in Python before the query ever runs.

---

### 🟠 #4 — Tag-removal edges are computed too early

**The code.** `neo4j_interface.py:80-88` flushes batches in this order:

```
definestr → removebyid → removebytag → secrule → generic
```

but `removebytag_module` resolves its patterns against tags already in the graph:

```cypher
MATCH (t:Tag) WHERE t.value =~ regex
MERGE (r)-[:Match]->(t)
```

**Why it is wrong.** `:Tag` nodes are created by the `secrule` and `generic` batches — the
two flushed *after* `removebytag`. Any tag that has not been written yet is invisible, so
the `Match` edge is never created. This applies to intermediate flushes and to the final
one, where up to 10,000 pending directives' worth of tags are still unwritten.

**What it means for you.** `SecRuleRemoveByTag` silently under-reports. A rule may be
disabled by a tag pattern and still appear active in the analysis.

The clean fix is to stop doing this at write time: write all directives first, then
resolve `:Regex → :Match → :Tag` in a single post-pass. That also removes a full `:Tag`
scan per removebytag directive.

---

### 🟡 #5 — `msg:` regex uses a character class instead of an alternation

**The code.** `directives.py:50`:

```python
msg_pattern  = re.compile(r'msg\s*:\s*(?P<msg>.*?)[,$]')      # [,$] = "," or a literal "$"
tags_pattern = re.compile(r'tag\s*:\s*(?P<tag>.*?)(?:,|$)')   # correct, two lines above
```

`[,$]` is a character class matching a comma or a literal dollar sign. It does **not** mean
end-of-string. The adjacent `tags_pattern` gets it right, which makes this a clear slip.

**Measured impact.** 131 SecRules lose their `msg` — those where `msg:` is the final action
with no trailing comma.

```bash
# 47,912 SecRules contain msg: — old regex captures 47,781, correct regex captures 47,912
```

Low blast radius, and a one-character fix.

---

### 🟡 #6 — `parse_args_setvar` reads the wrong dictionary

**The code.** `directives.py:243`:

```python
collected_vars_unset[None] = collected_vars_no_value.get(None, set()).union([var])
#                            ^^^^^^^^^^^^^^^^^^^^^^^ should be collected_vars_unset
```

Line 245, the dotted-variable branch immediately below, uses the correct dictionary.

**Why it is wrong.** Unset variables without a `.` prefix get merged with the *no-value*
set, and each iteration overwrites the previous one rather than accumulating. Both the
unset list and the no-value list end up wrong.

---

### 🟡 #7 — Macro lookups re-read files 1.2 million times

**The code.** `macro.py:9` and `macro.py:20` — both `parse_macro_def` and
`find_line_inside_macro` open the file and `readlines()` it on every call. There is no cache.

`recover_used_constants` calls them roughly twice per macro frame, for every directive.

**Measured impact.**

| | |
|---|---|
| `open()` + `readlines()` calls for one parse | **1,206,363** |
| distinct files involved | **191** (1.8 MB total) |
| measured cost, warm page cache | **~19.5 s of pure I/O** |
| same workload with a cache | 191 reads |

Roughly a 6,300× reduction in file operations for a dictionary keyed on path. On cold cache
or network storage the current cost is considerably worse. This is very likely the main
reason the old README warns that analysis "will take a long time" with the page "freezing
saying *running* for ages".

---

### 🟡 #8 — Everything is held in memory at once

**The code.** `analyzer.py:25` does `lines = file.readlines()` on the dump, and
`parse_compiled_config` returns a list of every `Directive` before a single database write.
Each `Directive.__init__` also does `deepcopy` of its context chain.

**Measured impact.** A full parse of `config_5` was run end to end:

| | |
|---|---|
| **peak RSS for one parse** | **873 MB** |
| wall time | 56 s (before any database write) |
| `readlines()` on `dump.conf` alone | 153 MB, versus 9 MB streaming |
| directive argument text alone | 61 MB (92,443 directives, avg 694 B, max 10 KB) |
| context deepcopies | ~1.5M objects (chains up to 15 deep) |

**873 MB, for one configuration.** The old analyzer was a standalone container where that
was survivable. It now runs inside the API process, alongside the SQLAlchemy pool, the
Neo4j driver and LangGraph — and two concurrent parses would mean ~1.7 GB.

The dump is streamable in one pass — the parser never looks backwards — so this is
mechanical to fix. Making `parse_compiled_config` a generator that yields directives in
batches would let writes start immediately and cap memory regardless of config size.

Relevant because this now runs **inside the API process**, not a standalone container.

---

### ⚪ #9 — A single malformed directive aborts the whole parse

`SecRule.__init__` raises on an argument count it does not expect, and
`Macro.parse_macro_def` raises if a macro definition line does not match. Neither is caught;
both propagate out of `parse_compiled_config` and kill the run.

**Measured impact: zero occurrences on `config_5`.** All 48,792 SecRules parse cleanly, and
all 878 distinct macro definition sites resolve and match their expected name. This is a
latent risk, not a current failure — but one bad rule in a future configuration discards
all 92,442 good ones with no partial result and no indication of which line was at fault.

```bash
# reproduce: parse every SecRule argument list, and every macro definition site
# → 0 raises out of 48,792 rules and 878 macro sites
```

---

### ⚪ #10 — Latent robustness issues

Neither of these fires on `config_5`. Recorded so they are not mistaken for live bugs.

- **`MacroContext.__init__` never calls `super().__init__()`** (`context.py:48`), so
  `line_num` does not exist until something assigns it. The fix-up loop always does, which
  is why `__str__` reads it without an `AttributeError` today.
- **`<VirtualHost>` resets `<If>` state** (`analyzer.py:41-42`), carrying the author's own
  `#FIXME: why do I reset the if level here?`. It fires once on `config_5`, silently
  dropping one open `<If>` condition. If a `</If>` ever arrives with no matching `<If>`,
  `conditions.pop()` raises `IndexError` and the parse dies. It never happens on this
  config — verified across all 379 `<If>` / 378 `</If>` occurrences.

---

### ⚪ #11 — Parser output is not reproducible across runs

**The code.** `recover_used_constants` returns a `set`, and `DirectiveFactory.create`
iterates it to build the `variables` list:

```python
for collection, const in names:          # names is a set
    if collection in modsec.COLLECTIONS:
        variables.extend((collection, const))
```

**Why it is wrong.** Python randomises string hashing per process, so set iteration order
differs between runs. Parsing the same file twice produces the same variables in a
different order.

**Measured impact.** 561 of 92,443 directives (0.6%) — those with two or more recovered
variables — emit their `variables` list in a different order on each run. Discovered while
diffing the ported parser against the original: the two agreed on every directive but
disagreed on ordering, until both were pinned to `PYTHONHASHSEED=0`, after which all 92,443
matched exactly across all 15 compared fields.

**What it means for you.** No incorrect data — `(collection, name)` pairs stay adjacent, so
the Cypher that indexes them in pairs still builds the right relationships. But reparsing a
configuration produces a diff even when nothing changed, which makes "did this config
actually change?" harder to answer and makes regression-testing the parser awkward.
Sorting the set before iterating fixes it in one line.

---

### ⚪ #12 — Cosmetic

- **`num_of_variables` counts flat entries, not pairs** (`directives.py:35` vs
  `query_factory.py:33`). The Cypher iterates twice as many times as needed; out-of-range
  indices return `null`, both `CASE` branches evaluate to `[]`, and nothing happens. Wasted
  work, no wrong data. Note `SecRule`'s own `num_of_vars` is counted correctly — only the
  base module disagrees.
- **`# In file:` is matched at column 0** while `#  N:` allows leading whitespace
  (`analyzer.py:20` vs `analyzer.py:22`). Not a bug here: all 85,472 file markers are at column 0. Worth
  knowing if a future Apache version indents them.
- **`</Location>` does not `continue`** like every other container branch. Harmless, since
  `</Location>` cannot match the generic directive pattern.
- **`Directive.processs_args`** is spelled with three s's.

---

## 9. Summary

| # | Defect | Severity | Measured blast radius | Recommendation |
|---|--------|----------|----------------------|----------------|
| 1 | `<LocationMatch>` / `<Directory>` / `<Proxy>` untracked | 🔴 Critical | 74,131 directives (80.2%), 40,290 SecRules | **Fix first.** Blocks meaningful request filtering |
| 2 | Macro `Context` string truncated | ✅ Resolved | was 91,032 directives (98.5%) | **Done** — field removed; provenance served by `/nodes/{id}/metadata` |
| 3 | `RemoveById` ranges produce no edges | 🟠 High | All range-only removals | Fix with #4 |
| 4 | Tag-removal edges resolved too early | 🟠 High | Up to 10,000 directives per run | Fix with #3, as a post-pass |
| 5 | `msg:` regex character class | 🟡 Medium | 131 SecRules | Cheap, fix opportunistically |
| 6 | `parse_args_setvar` wrong dict | 🟡 Medium | Undotted unset variables | Cheap, fix opportunistically |
| 7 | Uncached macro file reads | 🟡 Perf | 1,206,363 reads → 191 | High value, low risk |
| 8 | Whole dump and all directives in memory | 🟡 Perf | **873 MB peak RSS per parse** | Matters now that this runs in-process |
| 9 | One bad directive aborts everything | ⚪ Latent | 0 today | Worth doing before real-world configs |
| 10 | `super().__init__()`, `<If>` reset | ⚪ Latent | 0 today | Defensive only |
| 11 | Output not reproducible across runs | ⚪ Low | 561 directives (0.6%) | One-line fix: sort the set |
| 12 | Counting, spelling, `continue` | ⚪ Cosmetic | None | Whenever touching the code |

**#2 is resolved.** **#1 is now the top of the list** — the difference between an analysis
layer that describes your configuration and one that describes 20% of it. The
`location` column in the directives UI is already built and waiting for it. #3 and #4 are a natural second tranche since both live in the
removal path. #7 and #8 are pure wins with no semantic risk.

None of these are fixed by the port. They are reproduced exactly, so that fixing them is a
separate, reviewable change with a known before-and-after.
