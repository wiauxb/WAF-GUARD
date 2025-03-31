# 📖 Graph Documentation - [WAFSSISTANT]

## 📜 Table of Contents
1. [Introduction](#introduction)
2. [Graph Overview](#graph-overview)
3. [Node Classification](#node-classification)
4. [Node Details](#node-details)
5. [Relationships](#relationships)
6. [Query Examples](#query-examples)
7. [Update History](#update-history)
8. [Conclusion](#conclusion)


---

## 1️⃣ Introduction
This document describes the structure of the graph used in the WAFSSISTANT chatbot, explaining its main components and their interactions.

---

## 2️⃣ Graph Overview
- **Graph Name:** `[Graph Name]`
- **Version:** `1.1`
- **Description:**
  > Provide a high-level explanation of what this graph represents.
- **Use Case:**
  > Explain how the chatbot interacts with this graph.

---

## 3️⃣ Node Classification
The graph contains **XXXX node types**, grouped into **XX categories**.

[comment]: # (A single node can belong to multiple categories. {In that case wouldn't it be better to just add a 'Categories' parameter to each node and have the bot make a search based on the categories})

| Catégorie | Description |
|-----------|------------|
| `Mod Security Rule Node`    | Description Cat 1 |
| `Apache Mod Node`    | Description Cat 2 |
| `Design Node`    | Description Cat 3 |
| `Cat4`    | Description Cat 4 |
| `Cat5`    | Description Cat 5 |
| `Cat6`    | Description Cat 6 |
---

## 4️⃣ Node Details
Each node type has specific attributes.

### Example : `Collection` Node
Description

#### Use Case 1
**Description**
```cypher
MATCH ...
```

#### Use Case 2
**Description**
```cypher
MATCH ...
```

### Example : `Regex` Node
Description

#### Use Case 1
**Description**
```cypher
MATCH ...
```

#### Use Case 2
**Description**
```cypher
MATCH ...
```

---

## 5️⃣ Relationships
Relationships between nodes define interactions.

| Relationship  | From Node | To Node | Description |
|--------------|----------|---------|-------------|
| `AtLocation`  | All Rules Nodes     | Location | Node is defined at Location. |
| `InVirtualHost`   | All Rules Nodes      | VirtualHost  | Node is used in Virtual Host. |

---

## 6️⃣ Query Examples
Refer to the `queries_dataset` file for example of basic questions and queries that fetch their answers.

---

## 7️⃣ Update History
| Version | Date       | Changes |
|---------|-----------|-------------|
| 1.0     | 2025-04-01 | Initial structure |

---

## 8️⃣ Conclusion
This documentation will be maintained and updated with each major graph change to ensure consistency with chatbot behavior.
For any improvements, contact the technical team.



