
import sys
import time
from neo4j import GraphDatabase

from context import Context
from prototype import DefineStr, Directive, SecRuleRemoveById, SecRuleRemoveByTag
from query_factory import QueryFactory

BATCH_SIZE_GENERIC = 5000
BATCH_SIZE_SMALL = 1000

class Neo4jDB:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try:
            self.driver.verify_connectivity()
        except Exception as e:
            print(f"Error connecting to database: {e}")
        self.generic_batch = []
        self.definestr_batch = []
        self.removebyid_batch = []
        self.removebytag_batch = []

    def close(self):
        self.flush_all_batch()
        self.driver.close()

    def query(self, query, **kwargs):
        with self.driver.session() as session:
            return session.run(query, **kwargs)

    def add(self, directive:Directive):
        """Collects directives instead of executing immediately"""
        if isinstance(directive, DefineStr):
            self.definestr_batch.append(directive)
        elif isinstance(directive, SecRuleRemoveById):
            self.removebyid_batch.append(directive)
        elif isinstance(directive, SecRuleRemoveByTag):
            self.removebytag_batch.append(directive)
        else:
            self.generic_batch.append(directive)
        
        # Process in batches
        if len(self.definestr_batch) >= BATCH_SIZE_GENERIC:
            self.flush_batch(self.definestr_batch, "definestr")
        if len(self.removebyid_batch) >= BATCH_SIZE_SMALL:
            self.flush_batch(self.definestr_batch, "definestr")
            self.flush_batch(self.removebyid_batch, "removebyid")
        if len(self.removebytag_batch) >= BATCH_SIZE_GENERIC:
            self.flush_batch(self.definestr_batch, "definestr")
            self.flush_batch(self.removebytag_batch, "removebytag")
        if len(self.generic_batch) >= BATCH_SIZE_GENERIC:
            self.flush_batch(self.definestr_batch, "definestr")
            self.flush_batch(self.generic_batch, "generic")

    def flush_all_batch(self):
        if self.definestr_batch:
            print(f"Flushing {len(self.definestr_batch)} DefineStr directives to database")
            self.flush_batch(self.definestr_batch, "definestr")
        if self.removebyid_batch:
            print(f"Flushing {len(self.removebyid_batch)} SecRuleRemoveById directives to database")
            self.flush_batch(self.removebyid_batch, "removebyid")
        if self.removebytag_batch:
            print(f"Flushing {len(self.removebytag_batch)} SecRuleRemoveByTag directives to database")
            self.flush_batch(self.removebytag_batch, "removebytag")
        if self.generic_batch:
            print(f"Flushing {len(self.generic_batch)} generic directives to database")

    def flush_batch(self, batch, type:str):
        """Executes a batch insert using UNWIND"""
        if not batch:
            return
        
        batch_prop = [d.properties() for d in batch]  # Convert to list of dictionaries
        batch.clear() # Reset batch list

        query = QueryFactory.base_module()
        
        if type == "definestr":
            query += QueryFactory.definestr_module()
        elif type == "removebyid":
            query += QueryFactory.removebyid_module()
        elif type == "removebytag":
            query += QueryFactory.removebytag_module()
        else:
            query += QueryFactory.generic_module()

        # Run batch query
        self.query(query, batch=batch_prop)