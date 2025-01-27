import re
import sys
from neo4j import GraphDatabase

from context import Context
from prototype import Directive

class Neo4jDB:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self.driver.verify_connectivity()
        except Exception as e:
            print(f"Error connecting to database: {e}")

    def close(self):
        self.driver.close()

    def query(self, query, **kwargs):
        with self.driver.session() as session:
            return session.run(query, **kwargs)
        
    def format_properties(self, properties):
        properties_list = []
        for k, v in properties.items():
            if v is None:
                continue
            if isinstance(v, str):
                v = v.replace("'", "\\'")
            if isinstance(v, str) or isinstance(v, Context):
                properties_list.append(f"{k}: '{v}'")
            else:
                properties_list.append(f"{k}: {v}")
            # if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
            #     properties_list.append(f"{k}: {v}")
            # else:
        return ", ".join(properties_list)
        
    def add_generic(self, directive:Directive):
        label = directive.type
        properties = directive.properties()
        query = ""
        if properties.get("phase") is not None:
            query += f"MERGE (p:Phase {{value: {properties['phase']}}})"
        if properties.get("id") is not None:
            query += f" MERGE (i:Id {{value: {properties['id']}}})"
        if properties.get("tags") is not None:
            for i, tag in enumerate(properties['tags']):
                query += f" MERGE (t{i}:Tag {{value: '{tag}'}})"
        if properties.get("Location") is not None:
            query += f" MERGE (l:Location {{value: '{properties['Location']}'}})"
        if properties.get("VirtualHost") is not None:
            query += f" MERGE (v:VirtualHost {{value: '{properties['VirtualHost']}'}})"
        if properties.get("conditions") is not None:
            for i, condition in enumerate(properties['conditions']):
                query += f" MERGE (c{i}:Predicate {{value: '{condition}'}})"
            
        query += f" MERGE (n:{label} {{{self.format_properties(properties)}}})"

        if properties.get("phase") is not None:
            query += " MERGE (n)-[:InPhase]->(p)"
        if properties.get("id") is not None:
            query += " MERGE (n)-[:Has]->(i)"
        if properties.get("tags") is not None:
            for i, _ in enumerate(properties['tags']):
                query += f" MERGE (n)-[:Has]->(t{i})"
        if properties.get("Location") is not None:
            query += " MERGE (n)-[:AtLocation]->(l)"
        if properties.get("VirtualHost") is not None:
            query += " MERGE (n)-[:InVirtualHost]->(v)"
        if properties.get("conditions") is not None:
            for i, _ in enumerate(properties['conditions']):
                query += f" MERGE (n)-[:Has]->(c{i})"
        if directive.constants:
            for i, constant in enumerate(directive.constants):
                query += f" MERGE (const_{i}:Constant {{name: '{constant}'}}) MERGE (n)-[:Uses]->(const_{i})"

        self.query(query)

    def add_definestr(self, directive:Directive):
        label = directive.type
        properties = directive.properties()
        match_definestr = re.match(r"^\s*(?P<name>.+?)(?:\s+(?P<value>.*))?$", directive.args)
        if not match_definestr:
            print(f"Error parsing {label} directive: {directive.args}", file=sys.stderr)
            query = f"CREATE (n:{label} {{{self.format_properties(properties)}}})"
        else:
            query = f"MERGE (c:Constant {{{self.format_properties(dict(name=match_definestr.group('name'), value=match_definestr.group('value')))}}}) CREATE (n:{label} {{{self.format_properties(properties)}}}) CREATE (n)-[:Define]->(c)"
        if directive.constants:
            for i, constant in enumerate(directive.constants):
                query += f" MERGE (c{i}:Constant {{name: '{constant}'}}) MERGE (n)-[:Uses]->(c{i})"
        self.query(query)

    def add_secruleremovebyid(self, directive:Directive, step=500, max_interval=50_000):
        label = directive.type
        properties = directive.properties()
        ids_strings = re.split(r"[ ,]", properties.get("args"))
        ids = []
        ranges = []
        query = ""
        for s in ids_strings:
            if s == "":
                continue
            s = re.sub(r"(^[\"\'])|([\"\']$)", "", s)
            if s.isdigit():
                ids.append(int(s))
            # elif "," in s:
            #     r = s.split(",")
            #     for l in r:
            #         l = l.strip()
            #         if not l.isdigit():
            #             print(f"Error parsing {label} directive: {s} is an invalid id", file=sys.stderr)
            #             continue
            #         ids.append(int(l))
            else:
                r = s.split("-")
                if len(r) != 2 or not r[0].isdigit() or not r[1].isdigit():
                    print(f"Error parsing {label} directive: {s} is an invalid range", file=sys.stderr)
                    continue
                ranges.append((int(r[0]), int(r[1])))
        # print(f"there are {len(ids)} ids")
        for l, id in enumerate(ids):
            query += f" MERGE (i{l}:Id {{value: {id}}})"
        query += f" CREATE (n:{label} {{{self.format_properties(properties)}}})"
        for l, _ in enumerate(ids):
            query += f" CREATE (n)-[:DoesRemove]->(i{l})"
        if directive.constants:
            for i, constant in enumerate(directive.constants):
                query += f" MERGE (c{i}:Constant {{name: '{constant}'}}) MERGE (n)-[:Uses]->(c{i})"
        self.query(query)
        query = ""
        for i, (begin, end) in enumerate(ranges):
            if (end-begin) > max_interval:
                print(f"\nError parsing {label} directive: range {begin}-{end} is too big, ignoring", file=sys.stderr)
                continue
            # print(f"\nAdding range {begin} to {end}")
            for j in range(begin, end+1, step):
                # print(f"\t -> Adding range {j} to {min(end, j+step)}")
                query = f"UNWIND range({j}, {min(end, j+step)}) as value MERGE (i_{j}:Id {{value: value}}) MERGE (n:{label} {{{self.format_properties(properties)}}}) MERGE (n)-[:DoesRemove]->(i_{j})"
                self.query(query)

    def add_secruleremovebytag(self, directive:Directive):
        label = directive.type
        properties = directive.properties()
        tags = re.split(r"[ ,]", properties.get("args"))
        query = ""
        for l, tag in enumerate(tags):
            tag = re.sub(r"(^[\"\'])|([\"\']$)", "", tag)
            query += f" MERGE (r{l}:Regex {{value: '{tag}'}})"
        query += f" CREATE (n:{label} {{{self.format_properties(properties)}}})"
        query += f" WITH n, {", ".join([f"r{i}" for i in range(len(tags))])} MATCH (t:Tag) WHERE 1=1"
        for l, _ in enumerate(tags):
            query += f" AND t.value =~ r{l}.value"
            query += f" MERGE (r{l})-[:Match]->(t) MERGE (n)-[:DoesRemove]->(r{l})"
        if directive.constants:
            for i, constant in enumerate(directive.constants):
                query += f" MERGE (c{i}:Constant {{name: '{constant}'}}) MERGE (n)-[:Uses]->(c{i})"
        self.query(query)

    def add(self, directive:Directive):
        if directive.type.lower() == "definestr":
            self.add_definestr(directive)
        elif directive.type.lower() == "setenv":
            self.add_definestr(directive)
        elif directive.type.lower() == "secruleremovebyid":
            self.add_secruleremovebyid(directive)
        elif directive.type.lower() == "secruleremovebytag":
            self.add_secruleremovebytag(directive)

        self.add_generic(directive)