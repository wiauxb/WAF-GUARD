# Analyzer Service: Advanced Debugging Requirements Analysis

## Executive Summary

This document analyzes the `old/services/analyzer` service to identify what configuration information and interactions **should** be tracked for advanced debugging purposes, compared to what **is currently implemented**.

---

## Current Implementation Overview

### Databases Used
- **PostgreSQL**: Tracks macro definitions, calls, and symbol table (file locations)
- **Neo4j**: Stores directive relationships, variables, constants, and configuration structure

### Currently Tracked Elements

#### ✅ **Configuration Structure**
- VirtualHost blocks
- Location directives
- If block conditions and nesting levels
- File sources and line numbers
- Macro definitions and call chains

#### ✅ **Directive Metadata**
- Directive types (SecRule, DefineStr, RemoveById, RemoveByTag)
- Rule IDs
- Rule tags
- Processing phase (1-5)
- Rule messages

#### ✅ **Data References**
- Constants (user-defined variables: `${VAR}`)
- ModSecurity variables (`%{VAR}`)
- Collection references (`@{COLLECTION.VAR}`)
- 85+ ModSecurity collections tracked

#### ✅ **ModSecurity Actions**
- setenv variables (environment variables)
- setvar variables (transaction variables)
- Variable unsets

#### ✅ **Rule Removal Tracking**
- SecRuleRemoveById (specific IDs and ranges)
- SecRuleRemoveByTag (regex-based tag matching)

#### ✅ **Operators**
- 40+ ModSecurity operators recognized (@rx, @pm, @detectSQLi, etc.)

---

## Required for Advanced Debugging: Comprehensive List

### 1. **Rule Execution Flow** ⚠️ PARTIALLY TRACKED

#### Currently Missing:
- ❌ **Rule execution order** within same phase
- ❌ **Rule chaining** (`chain` action relationships)
- ❌ **Skip actions** (`skip`, `skipAfter` target tracking)
- ❌ **Conditional execution** (which rules affect others)
- ❌ **Phase transitions** (how data flows between phases)

#### Should Track:
```
Rule Execution Graph:
├── Execution order (line-based + phase-based)
├── Chain relationships (rule A → rule B → rule C)
├── Skip targets (rule 100 skips to rule 150)
├── SkipAfter targets (skip after marker "END_VALIDATION")
├── Phase dependency (phase 2 variables used in phase 4)
└── Conditional branches (If-block alternative execution paths)
```

---

### 2. **Variable Lifecycle Management** ⚠️ PARTIALLY TRACKED

#### Currently Missing:
- ❌ **Variable creation points** (setvar tracking incomplete)
- ❌ **Variable read locations** (where variables are used in conditions)
- ❌ **Variable scope** (TX vs ENV vs collection lifecycle)
- ❌ **Variable mutations** (incremental changes: `TX.score=+5`)
- ❌ **Variable lifetime** (phase-based expiration)
- ❌ **Collection expansions** (`ARGS:*` vs `ARGS:username`)

#### Should Track:
```
Variable Lifecycle:
├── Creation: Rule/directive that sets variable
├── Reads: All rules that inspect the variable
├── Mutations: Rules that modify existing value
├── Unsets: Rules that delete the variable
├── Scope: TX (transaction) vs ENV (environment) vs SESSION
├── Lifetime: Which phases the variable exists in
├── Type: String, numeric, collection member
└── Dependencies: Variables derived from other variables
```

---

### 3. **Rule Interaction and Conflicts** ❌ NOT TRACKED

#### Currently Missing:
- ❌ **Overlapping rules** (multiple rules matching same condition)
- ❌ **Contradictory rules** (rule A blocks, rule B allows)
- ❌ **Rule shadowing** (earlier rule prevents later rule execution)
- ❌ **Remove conflicts** (RemoveById removing rules that other rules depend on)
- ❌ **Tag removal impacts** (RemoveByTag removing unexpected rules)
- ❌ **Duplicate rule detection** (same ID used multiple times)

#### Should Track:
```
Rule Interactions:
├── Conflicts: Rules with opposing actions
├── Overlaps: Rules matching similar patterns
├── Dependencies: Rules requiring other rules to exist
├── Removals: Which rules remove which other rules
├── Shadowing: Unreachable rules due to earlier matches
├── Duplicates: Same rule ID defined multiple times
└── Tag groups: Rules sharing tags and their relationships
```

---

### 4. **Data Flow and Transformations** ⚠️ PARTIALLY TRACKED

#### Currently Missing:
- ❌ **Transformation functions** (`t:lowercase`, `t:base64Decode`, etc.)
- ❌ **Transformation chains** (multiple transformations applied)
- ❌ **Data sanitization** (which transformations affect which operators)
- ❌ **Input/output tracking** (original value → transformed value)
- ❌ **Transformation order** (order matters for correctness)

#### Should Track:
```
Data Flow:
├── Source: Collection.Variable being inspected
├── Transformations: List of t: functions applied in order
├── Operator: Inspection operator (@rx, @pm, etc.)
├── Pattern: What pattern is matched against
├── Result: Variable set based on match result
└── Side effects: Logging, blocking, variable setting
```

**Transformation Functions to Track** (20+ types):
- Normalization: `lowercase`, `uppercase`, `trim`, `compressWhitespace`
- Encoding: `base64Decode`, `urlDecode`, `hexDecode`, `htmlEntityDecode`
- Removal: `removeNulls`, `removeWhitespace`, `removeComments`
- Special: `normalizePath`, `normalizePathWin`, `sqlHexDecode`, `utf8toUnicode`

---

### 5. **Anomaly Scoring System** ❌ NOT TRACKED

#### Currently Missing:
- ❌ **Anomaly score accumulation** (`TX.anomaly_score=+5`)
- ❌ **Scoring rules** (which rules contribute to score)
- ❌ **Threshold rules** (rules that check score >= threshold)
- ❌ **Score reset points** (where scores are cleared)
- ❌ **Inbound vs Outbound scoring** (request vs response scoring)
- ❌ **Critical vs Warning levels** (severity-based scoring)

#### Should Track:
```
Anomaly Scoring:
├── Score variables: TX.inbound_anomaly_score, TX.outbound_anomaly_score
├── Contributors: Rules that increment score
├── Severity mapping: Critical=5, Error=4, Warning=3, Notice=2
├── Thresholds: Rules checking score >= X
├── Actions on threshold: What happens when exceeded
├── Score flow: Phase-by-phase accumulation
└── Reset points: Where scores are cleared
```

---

### 6. **Action Tracking and Side Effects** ⚠️ PARTIALLY TRACKED

#### Currently Missing:
- ❌ **Action combinations** (what actions can coexist)
- ❌ **Disruptive actions** (`block`, `deny`, `drop`, `redirect`)
- ❌ **Flow control** (`pass`, `allow`, `skip`, `skipAfter`)
- ❌ **Logging actions** (`log`, `nolog`, `auditlog`, `noauditlog`)
- ❌ **Execution actions** (`exec`, `prepend`, `append`)
- ❌ **Action precedence** (which action takes priority)
- ❌ **Action inheritance** (default actions in SecDefaultAction)

#### Should Track:
```
Actions:
├── Disruptive: block, deny, drop, allow, pass, redirect
├── Flow: skip, skipAfter, chain
├── Data: setvar, setenv, unsetvar
├── Logging: log, nolog, auditlog, noauditlog, severity
├── Metadata: id, tag, msg, logdata
├── Status: status (HTTP status code)
├── Execution: exec (external script execution)
└── Default: SecDefaultAction settings per phase
```

---

### 7. **Request/Response Matching** ⚠️ PARTIALLY TRACKED

#### Currently Missing:
- ❌ **Request phase flow** (phases 1→2 variable passing)
- ❌ **Response phase flow** (phases 3→4→5 variable passing)
- ❌ **Body inspection** (REQUEST_BODY, RESPONSE_BODY usage)
- ❌ **Header inspection** (REQUEST_HEADERS, RESPONSE_HEADERS)
- ❌ **Cookie handling** (REQUEST_COOKIES, RESPONSE_COOKIES)
- ❌ **File uploads** (FILES, MULTIPART_* collections)
- ❌ **XML/JSON parsing** (XML:/* and JSON:/* selectors)

#### Should Track:
```
Request/Response Flow:
├── Phase 1 (Request Headers): Which collections inspected
├── Phase 2 (Request Body): Body parsing and inspection
├── Phase 3 (Response Headers): Response header inspection
├── Phase 4 (Response Body): Response body inspection
├── Phase 5 (Logging): Logging and cleanup
├── Variables passed between phases
└── Collection usage per phase
```

---

### 8. **Performance and Optimization** ❌ NOT TRACKED

#### Currently Missing:
- ❌ **Rule complexity** (regex complexity, operator cost)
- ❌ **Collection size** (ARGS:* expands to how many items)
- ❌ **Operator performance** (expensive operators like @detectSQLi)
- ❌ **Transformation cost** (multiple transformations impact)
- ❌ **Rule execution count** (how many times rule could fire)
- ❌ **Performance variables** (PERF_* collections)
- ❌ **SecRuleEngine settings** (On, DetectionOnly, Off per location)

#### Should Track:
```
Performance:
├── Rule complexity score
├── Expensive operators used
├── Transformation chain length
├── Collection expansion size
├── Regex complexity (nested groups, backreferences)
├── PERF_RULES, PERF_PHASE, PERF_SREAD, PERF_SWRITE usage
└── SecRuleEngine directive per context
```

---

### 9. **Error Handling and Edge Cases** ❌ NOT TRACKED

#### Currently Missing:
- ❌ **SecRuleEngine directives** (On/Off/DetectionOnly per location)
- ❌ **SecRequestBodyAccess** (whether body inspection enabled)
- ❌ **SecResponseBodyAccess** (whether response body inspected)
- ❌ **Body limits** (SecRequestBodyLimit, SecResponseBodyLimit)
- ❌ **Error handling** (SecRuleEngine DetectionOnly mode)
- ❌ **Missing variables** (graceful handling vs errors)
- ❌ **Invalid regex patterns** (malformed rules)

#### Should Track:
```
Error Handling:
├── Engine mode: On, Off, DetectionOnly
├── Body access settings
├── Size limits
├── Timeout settings
├── Error actions (what happens on parsing errors)
├── Missing variable handling
└── Invalid pattern detection
```

---

### 10. **Macro Expansion and Context** ✅ WELL TRACKED

#### Currently Tracked:
- ✅ Macro definitions
- ✅ Macro call chains
- ✅ Macro nesting
- ✅ Source file tracking
- ✅ Line number mapping

#### Minor Enhancements:
- ⚠️ **Macro parameter passing** (if macros accept parameters)
- ⚠️ **Macro recursive calls** (macro calling itself)
- ⚠️ **Macro shadowing** (macro redefinition)

---

### 11. **Tag-Based Rule Grouping** ⚠️ PARTIALLY TRACKED

#### Currently Missing:
- ❌ **Tag hierarchy** (OWASP_CRS, OWASP_CRS/WEB_ATTACK, etc.)
- ❌ **Tag-based removal impact** (which rules affected by tag removal)
- ❌ **Tag-based searching** (find all rules with tag X)
- ❌ **Tag relationships** (rules sharing multiple tags)
- ❌ **Standard tag conventions** (OWASP CRS tag structure)

#### Should Track:
```
Tag System:
├── Tag hierarchy (parent/child relationships)
├── Tag groups (rules with same tag)
├── Removal impact (RemoveByTag affects which rules)
├── Tag search index
├── Multiple tag combinations
└── Standard tags: OWASP_CRS, ATTACK, AUTOMATION, etc.
```

---

### 12. **External Data Sources** ❌ NOT TRACKED

#### Currently Missing:
- ❌ **IP lists** (@ipMatch, @ipMatchFromFile)
- ❌ **Pattern files** (@pmFromFile)
- ❌ **Geographic data** (@geoLookup)
- ❌ **RBL checks** (@rbl)
- ❌ **External scripts** (exec action)
- ❌ **Include files** (file dependencies)
- ❌ **SecDataDir** (persistent storage location)

#### Should Track:
```
External Dependencies:
├── File references (@pmFromFile paths)
├── IP list files
├── Geographic database files
├── RBL servers
├── External scripts (exec)
├── Include file dependencies
└── Data directory configuration
```

---

### 13. **SecAction and Initialization** ⚠️ PARTIALLY TRACKED

#### Currently Missing:
- ❌ **SecAction rules** (initialization without matching)
- ❌ **Variable initialization** (default values set at start)
- ❌ **Collection initialization** (initcol action)
- ❌ **Persistent storage** (setsid, setuid for collections)
- ❌ **Expiration** (expirevar action)

#### Should Track:
```
Initialization:
├── SecAction rules (id, phase, actions)
├── initcol (collection initialization)
├── Default variable values
├── Persistent collections (IP, SESSION, USER, GLOBAL)
├── Collection expiration
└── Collection storage (setsid, setuid)
```

---

### 14. **CTL (Control) Actions** ❌ NOT TRACKED

#### Currently Missing:
- ❌ **Runtime configuration changes** (ctl actions)
- ❌ **auditEngine control** (ctl:auditEngine=On/Off)
- ❌ **requestBodyAccess control** (ctl:requestBodyAccess=On/Off)
- ❌ **ruleEngine control** (ctl:ruleEngine=On/Off/DetectionOnly)
- ❌ **ruleRemoveById** (runtime rule removal)
- ❌ **ruleRemoveByTag** (runtime tag-based removal)
- ❌ **ruleRemoveTargetById** (remove specific variables from rule)

#### Should Track:
```
CTL Actions:
├── auditEngine modifications
├── requestBodyAccess changes
├── responseBodyAccess changes
├── ruleEngine state changes
├── Runtime rule removals
├── Target variable exclusions
└── Rule-specific control changes
```

---

### 15. **Multipart and File Upload Handling** ❌ NOT TRACKED

#### Currently Missing:
- ❌ **MULTIPART_* collections** (MULTIPART_NAME, MULTIPART_FILENAME)
- ❌ **FILES collection** (uploaded file inspection)
- ❌ **FILES_NAMES** (uploaded file names)
- ❌ **FILES_SIZES** (uploaded file sizes)
- ❌ **FILES_TMPNAMES** (temporary file paths)
- ❌ **File inspection** (@inspectFile operator usage)

#### Should Track:
```
File Upload Handling:
├── MULTIPART_* variable usage
├── FILES collection inspection
├── File size limits
├── File type validation
├── @inspectFile operator usage
└── Temporary file handling
```

---

## Gap Analysis Summary

### Well Tracked (✅)
1. Configuration structure (VirtualHost, Location, If blocks)
2. Macro definitions and call chains
3. File sources and line numbers
4. Basic directive metadata (ID, tag, phase, message)
5. Constants and variables (basic references)
6. Rule removal directives (ById, ByTag)

### Partially Tracked (⚠️)
1. **Variable lifecycle** - Sets tracked, reads not tracked
2. **Actions** - Some tracked (setvar, setenv), many missing
3. **Data flow** - Collections tracked, transformations not tracked
4. **Rule execution** - Phase tracked, order and chains not tracked
5. **Tag system** - Tags stored, hierarchy not analyzed

### Not Tracked (❌)
1. **Rule interactions** - No conflict or dependency detection
2. **Anomaly scoring** - No score accumulation tracking
3. **Action side effects** - Limited action tracking
4. **Performance implications** - No complexity analysis
5. **Error handling** - No engine mode or error action tracking
6. **Transformations** - Not parsed or stored
7. **CTL actions** - Runtime control not tracked
8. **External dependencies** - File references not tracked
9. **Request/Response flow** - Phase transitions not tracked
10. **File uploads** - Multipart handling not tracked

---

## Priority Recommendations for Advanced Debugging

### High Priority (Critical for Debugging)

1. **Rule Execution Order and Chains**
   - Track `chain` action to link dependent rules
   - Calculate execution order (phase + line number)
   - Map `skip` and `skipAfter` targets

2. **Variable Lifecycle (Complete)**
   - Track where variables are READ (not just set)
   - Map variable flow through phases
   - Track variable scope (TX vs ENV)
   - Handle variable mutations (+= operations)

3. **Transformation Tracking**
   - Parse all `t:*` functions from rule arguments
   - Store transformation order (matters for correctness)
   - Link transformations to operators

4. **Rule Interactions and Conflicts**
   - Detect overlapping patterns
   - Identify conflicting actions (block vs allow)
   - Map removal impacts (what RemoveById affects)
   - Find unreachable rules (shadowing)

5. **Action Tracking (Complete)**
   - Parse all action types (disruptive, flow, logging)
   - Track action combinations
   - Identify default actions (SecDefaultAction)
   - Map action precedence

### Medium Priority (Enhanced Debugging)

6. **Anomaly Scoring**
   - Track TX.anomaly_score modifications
   - Map scoring rules and their contributions
   - Identify threshold checks
   - Track severity-to-score mappings

7. **CTL Actions**
   - Parse ctl: directives
   - Track runtime engine state changes
   - Map dynamic rule removals

8. **Tag Hierarchy and Relationships**
   - Parse tag structure (slash-separated hierarchy)
   - Build tag taxonomy
   - Map tag-based removal impacts

9. **Request/Response Phase Flow**
   - Track which collections are used per phase
   - Map variable passing between phases
   - Identify body inspection rules

### Low Priority (Optimization and Advanced)

10. **Performance Metrics**
    - Calculate regex complexity scores
    - Identify expensive operators
    - Track collection expansion sizes

11. **External Dependencies**
    - Parse file references (@pmFromFile, etc.)
    - Track Include directives
    - Map external script dependencies

12. **File Upload Handling**
    - Track MULTIPART_* and FILES usage
    - Map file inspection rules

---

## Recommended Database Schema Extensions

### Neo4j Schema Additions

```cypher
// New Node Types
(:Transformation {name: "lowercase", order: 1})
(:Action {type: "block", disruptive: true})
(:Phase {number: 2, name: "Request Body"})
(:Score {variable: "TX.anomaly_score", threshold: 5})
(:Ctl {action: "ruleEngine=DetectionOnly"})

// New Relationships
(:SecRule)-[:CHAINS_TO]->(:SecRule)
(:SecRule)-[:SKIPS_TO]->(:SecRule)
(:SecRule)-[:READS]->(:Variable)
(:SecRule)-[:WRITES]->(:Variable)
(:SecRule)-[:APPLIES_TRANSFORMATION {order: 1}]->(:Transformation)
(:SecRule)-[:PERFORMS]->(:Action)
(:SecRule)-[:CONTRIBUTES_TO]->(:Score)
(:SecRule)-[:CONFLICTS_WITH]->(:SecRule)
(:SecRule)-[:SHADOWS]->(:SecRule)
(:SecRule)-[:DEPENDS_ON]->(:SecRule)
(:Variable)-[:FLOWS_TO_PHASE]->(:Phase)
(:Tag)-[:CHILD_OF]->(:Tag)
```

### PostgreSQL Schema Additions

```sql
-- Rule execution order table
CREATE TABLE rule_execution_order (
    rule_id INTEGER PRIMARY KEY,
    execution_order INTEGER NOT NULL,
    phase INTEGER NOT NULL,
    can_be_skipped BOOLEAN DEFAULT FALSE
);

-- Variable lifecycle table
CREATE TABLE variable_lifecycle (
    id SERIAL PRIMARY KEY,
    variable_name TEXT NOT NULL,
    scope TEXT NOT NULL, -- TX, ENV, GLOBAL, SESSION, etc.
    created_by_rule INTEGER REFERENCES symboltable(id),
    read_by_rules INTEGER[], -- Array of rule IDs
    modified_by_rules INTEGER[], -- Array of rule IDs
    deleted_by_rule INTEGER REFERENCES symboltable(id),
    start_phase INTEGER,
    end_phase INTEGER
);

-- Rule interaction table
CREATE TABLE rule_interactions (
    id SERIAL PRIMARY KEY,
    rule_a INTEGER REFERENCES symboltable(id),
    rule_b INTEGER REFERENCES symboltable(id),
    interaction_type TEXT, -- conflict, shadow, dependency, overlap
    description TEXT
);

-- Transformation tracking
CREATE TABLE transformations (
    id SERIAL PRIMARY KEY,
    rule_id INTEGER REFERENCES symboltable(id),
    transformation_name TEXT NOT NULL,
    order_position INTEGER NOT NULL
);
```

---

## Implementation Effort Estimation

### Quick Wins (1-2 days)
- Parse transformation functions from SecRule arguments
- Track action types more comprehensively
- Build tag hierarchy from tag strings
- Identify chain actions and link rules

### Medium Effort (1 week)
- Implement variable read tracking (requires parsing operator arguments)
- Build rule execution order calculator
- Implement skip/skipAfter target resolution
- Parse and track CTL actions

### Large Effort (2-3 weeks)
- Complete variable lifecycle tracking across phases
- Implement rule conflict and interaction detection
- Build anomaly scoring system tracker
- Implement complete action side-effect tracking
- Add performance complexity analysis

### Major Refactoring (4+ weeks)
- Implement complete data flow analysis
- Build phase-based variable flow tracker
- Implement intelligent debugging query interface
- Create visualization tools for rule interactions

---

## Conclusion

The current analyzer implementation provides a **solid foundation** for configuration parsing and basic relationship tracking. However, for **advanced debugging**, significant gaps exist in:

1. **Dynamic behavior tracking** (rule execution, variable lifecycle)
2. **Rule interaction analysis** (conflicts, dependencies, shadowing)
3. **Data flow analysis** (transformations, phase transitions)
4. **Action side effects** (complete action tracking)
5. **Anomaly scoring** (score accumulation and thresholds)

**Recommendation**: Prioritize the "High Priority" items first, as they provide the most value for debugging complex ModSecurity configurations. The additions can be implemented incrementally without major refactoring of the existing system.

The dual-database approach (Neo4j + PostgreSQL) is well-suited for these enhancements:
- **Neo4j**: Ideal for relationship queries (rule chains, variable flow, conflicts)
- **PostgreSQL**: Good for transactional tracking (execution order, lifecycle events)

With these enhancements, the analyzer will become a **powerful debugging tool** capable of answering complex questions like:
- "Why isn't rule 12345 firing?"
- "Which rules set the anomaly score above threshold?"
- "What happens if I remove rule 98765?"
- "Which rules are never executed due to shadowing?"
- "How does variable TX.blocked flow through the phases?"
