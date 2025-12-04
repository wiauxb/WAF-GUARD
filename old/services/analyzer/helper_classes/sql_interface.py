import psycopg2
import os

from .context import *
from .directives import Directive


class PostgresDB:
    def __init__(self, uri, user, password, database):
        environment = os.getenv("ENVIRONMENT", "dev")

        if environment == "prod":
            self.connection = psycopg2.connect(
                host=uri,
                user=user,
                password=password,
                database=database,
                sslmode='require'
            )
        else:
            self.connection = psycopg2.connect(
                host=uri,
                user=user,
                password=password,
                database=database
            )
        self.prepare_statements()

    def init_tables(self):
        self.execute("CREATE TABLE IF NOT EXISTS symboltable (id serial PRIMARY KEY, file_path text NOT NULL, line_number integer NOT NULL, node_id integer);")
        self.execute("CREATE TABLE IF NOT EXISTS macrodef (name text PRIMARY KEY, ruleid integer references symboltable(id));")
        self.execute("CREATE TABLE IF NOT EXISTS macrocall (id serial PRIMARY KEY, nodeid integer NOT NULL, macro_name text references macrodef(name), ruleid integer references symboltable(id));")

    def prepare_statements(self):
        with self.connection.cursor() as cursor:
            cursor.execute("PREPARE insert_symboltable AS INSERT INTO symboltable (file_path, line_number, node_id) VALUES ($1, $2, $3) RETURNING id;")
            cursor.execute("PREPARE insert_macrodef AS INSERT INTO macrodef (name, ruleid) VALUES ($1, $2);")
            cursor.execute("PREPARE insert_macrocall AS INSERT INTO macrocall (nodeid, macro_name, ruleid) VALUES ($1, $2, $3) RETURNING id;")
            cursor.execute("PREPARE select_macrodef AS SELECT * FROM macrodef WHERE name = $1;")

    def execute(self, query, vars_list=None):
        with self.connection.cursor() as cursor:
            cursor.execute(query, vars_list)
            if cursor.description:  # Check if the query returns rows
                return cursor.fetchall()
            else:
                self.commit()
                return None

    def execute_prepared(self, statement_name, vars_list=None):
        with self.connection.cursor() as cursor:
            cursor.execute(f"EXECUTE {statement_name} ({','.join(['%s'] * len(vars_list))});" if vars_list else f"EXECUTE {statement_name};", vars_list)
            if cursor.description:  # Check if the query returns rows
                return cursor.fetchall()
            else:
                self.commit()
                return None

    def commit(self):
        self.connection.commit()

    def close(self):
        self.commit()
        self.connection.close()

    def add_rule(self, ctx: Context, node_id: int = None):
        if isinstance(ctx, FileContext):
            file_path = ctx.file_path
            line_number = ctx.line_num
        elif isinstance(ctx, MacroContext):
            file_path = ctx.definition.file_path
            line_number = ctx.definition.line_num + ctx.line_num
        else:
            raise Exception(f"Invalid context type {type(ctx)}")
        return self.execute_prepared("insert_symboltable", (file_path, line_number, node_id))[0][0]

    def add_macrodef(self, name: str, rule_id: int):
        self.execute_prepared("insert_macrodef", (name, rule_id))
        return name

    def add_macrocall(self, node_id: int, macro_id: int, rule_id: int):
        return self.execute_prepared("insert_macrocall", (node_id, macro_id, rule_id))[0][0]

    def add_sql(self, directive: Directive):
        ptr_ctx = directive.Context
        first_step = True
        while ptr_ctx is not None:
            if isinstance(ptr_ctx, FileContext):
                if first_step:
                    self.add_rule(ptr_ctx, directive.node_id)
                    first_step = False
                ptr_ctx = None
            elif isinstance(ptr_ctx, MacroContext):
                def_id = self.execute_prepared("select_macrodef", (ptr_ctx.macro_name,))
                if not def_id:
                    def_id = self.add_rule(ptr_ctx.definition)
                    self.add_macrodef(ptr_ctx.macro_name, def_id)
                if first_step:
                    self.add_rule(ptr_ctx, directive.node_id)
                    first_step = False
                use_id = self.add_rule(ptr_ctx.use)
                self.add_macrocall(directive.node_id, ptr_ctx.macro_name, use_id)
                ptr_ctx = ptr_ctx.use
                
        
        

if __name__ == "__main__":
    db = PostgresDB("localhost", "user", "password", "cwaf")
    # print(db.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);"))
    # print(db.execute("INSERT INTO test (num, data) VALUES (100, 'abc');"))
    # print(db.execute("SELECT * FROM test;"))
    # --------------------------------------------
    # print(db.execute("DROP TABLE macrodef CASCADE;"))
    db.close()