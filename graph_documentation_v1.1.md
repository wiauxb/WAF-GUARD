# 📖 Graph Documentation - [WAFSSISTANT]

## 📜 Table of Contents
1. [Introduction](#introduction)
2. [Graph Overview](#graph-overview)
3. [Node Classification](#node-classification)
4. [Node Details](#node-details)
5. [Relationships](#relationships)
6. [Simplified Graph Schema](#simplified-graph-schema)
7. [Query Examples](#query-examples)
8. [Update History](#update-history)
9. [Conclusion](#conclusion)

---

## 1️⃣ Introduction
This document describes the structure of the graph used in the chatbot, explaining its main components and their interactions.

---

## 2️⃣ Graph Overview
- **Graph Name:** `[Graph Name]`
- **Version:** `[Current Version]`
- **Description:**
  > Provide a high-level explanation of what this graph represents.
- **Use Case:**
  > Explain how the chatbot interacts with this graph.

---

## 3️⃣ Node Classification
The graph contains **XXXX node types**, grouped into **XX categories**.

[comment]: # (A single node can belong to multiple categories. {In that case would'n it be better to just add a 'Categories' parameter to each node and have the bot make a search based on the categories})

| Catégorie | Description |
|-----------|------------|
| `Mod Security Calls???`    | Description Cat 1 |
| `Cat2`    | Description Cat 2 |
| `Cat3`    | Description Cat 3 |
| `Cat4`    | Description Cat 4 |
| `Cat5`    | Description Cat 5 |
| `Cat6`    | Description Cat 6 |
---

## 4️⃣ Node Details
Each node type has specific attributes.

[comment]: # (Maybe here we can give these attributes by categories; the main attributes that are common to every node types in a category.)

### Example : `SecRule` Node
Represents a reference to a SecRule call
```json
{
  "property": "String",
  "type": "String"
}
```

### Example : `Regex` Node
Not really a node but more of a choice of construction...
```json
{
  "property": "String",
  "type": "List of Integers"
}
```

---

## 5️⃣ Relationships
Relationships between nodes define interactions.

| Relationship  | From Node | To Node | Description |
|--------------|----------|---------|-------------|
| `AtLocation`  | secdebuglog     | Location | This secdebuglog call was made at this location. |
| `InVirtualHost`   | secdebuglog     | VirtualHost  | This  secdebuglog call is in this virtual host.|
| `Uses` | secdebuglog    | Constant| This secdebulog uses this constant. |

[comment]: # (If relationships contain attributes, mention them as well. Didn't see any relations with attributes in this graph but maybe I missed it.)

---

## 6️⃣ Simplified Graph Schema
Provide a simplified visual representation of the graph schema.

[comment]: # (I'm still somewhat skeptical about this part.)

---

## 7️⃣ Query Examples
Some basic Cypher queries.

**What are the rules that block all cookies by default and where it is used?**
```cypher
CALL {
MATCH (n1)-[*..2]->(v1 WHERE v1.name =~"REQUEST_COOKIE.*") RETURN n1 as rule, v1 as var
UNION
MATCH (n2)-[:Uses]->(v2:SubVariable WHERE v2.name =~ "(?i).*cookie.*")-[:IsSubVariableOf]->(v2_var:Variable WHEREv2_var.name = "REQUEST_HEADERS") RETURN n2 as rule, v2 as var
}
WITH rule
WHERE rule.args CONTAINS "deny"
RETURN rule
```

**What are the rules that allow cookies and where are they used?**
```cypher

```

**Filter by security tag.**
```cypher
WITH rule
WHERE rule.args CONTAINS "deny" and "SHORT" IN rule.tags
RETURN rule
```

**Filter by phase.**
```cypher
WITH rule
WHERE rule.args CONTAINS "deny" and rule.phase = 3
RETURN rule
```

**Give me the rules that we apply to the args or body or header  depending for a specific location (example /auth/).**
```cypher
MATCH (v:Variable WHERE v.name = "REQUEST_BODY")<-[*..2]-(n)-[:AtLocation]->(l:Location WHERE l.value =~ "/wp.*") RETURN n
```

**Is there any rules regarding JSON in the location /realms/?**
```cypher
MATCH (n)-[:AtLocation]->(l:Location WHERE l.value =~ "(.*/)?realms.*") WHERE TOLOWER(n.args) CONTAINS "json" RETURN n
```

**What is the regex autorized for the argument username in the location for keycloak?**
```cypher

```

**Is this username allowed for the keycloak environment :Olivié?**
```cypher

```

**What are the rules disabled for keycloak?**
```cypher
MATCH (n) WHERE TOLOWER(n.Context) CONTAINS "keycloak" and ((n)-[*]-(:secruleremovebyid) or (n)-[*]-(:secruleremovebytag)) RETURN n
```

**Is there any rules for specific locations used in the jira environment?**
```cypher
MATCH (n)-[:AtLocation]->(l:Location WHERE l.value =~ "/jira/.+") RETURN n
```

---

## 8️⃣ Update History
| Version | Date       | Changes |
|---------|-----------|-------------|
| 1.0     | YYYY-MM-DD | Initial structure |

---

## 9️⃣ Conclusion
This documentation will be maintained and updated with each major graph change to ensure consistency with chatbot behavior.
For any improvements, contact the technical team.



