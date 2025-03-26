# 📖 Graph Documentation - [Project Name]

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
Briefly describe the purpose of this graph and its role in the chatbot.

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

| Catégorie | Description |
|-----------|------------|
| `Cat1`    | Description Cat 1 |
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
  "type": "List"
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

---

## 7️⃣ Query Examples
Some basic Cypher queries.

**Question 1**
```cypher
MATCH ...
```

---

## 8️⃣ Update History
| Version | Date       | Changes |
|---------|-----------|-------------|
| 1.0     | YYYY-MM-DD | Initial structure |

---

## 9️⃣ Conclusion
Summarize key points and provide any future considerations.


