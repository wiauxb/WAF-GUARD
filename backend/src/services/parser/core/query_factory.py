

class QueryFactory:

    @classmethod
    def base_module(cls):
        return """
        UNWIND $batch AS properties
        CREATE (node:$(properties.type))
        SET node = properties.node_props
        WITH node, properties
        
        FOREACH (_ IN CASE WHEN properties.Location IS NOT NULL THEN [1] ELSE [] END |
            MERGE (l:Location {value: properties.Location, configuration_id: $cid})
            MERGE (node)-[:AtLocation]->(l)
        )

        FOREACH (_ IN CASE WHEN properties.VirtualHost IS NOT NULL THEN [1] ELSE [] END |
            MERGE (v:VirtualHost {value: properties.VirtualHost, configuration_id: $cid})
            MERGE (node)-[:InVirtualHost]->(v)
        )

        FOREACH (condition IN properties.conditions |
            MERGE (c:Predicate {value: condition, configuration_id: $cid})
            MERGE (node)-[:Has]->(c)
        )

        FOREACH (constant IN properties.constants |
            MERGE (co:Constant {name: constant, configuration_id: $cid})
            MERGE (node)-[:Uses]->(co)
        )

        FOREACH (var_i IN range(0,properties.num_of_variables-1) |
            FOREACH (_ IN CASE WHEN properties.variables[(var_i*2)+1] <> "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.variables[var_i*2], configuration_id: $cid})
                MERGE (sv:Variable {name: properties.variables[(var_i*2)+1], configuration_id: $cid})
                MERGE (sv)-[:IsVariableOf]->(v)
                MERGE (node)-[:Uses]->(sv)
            )
            FOREACH (_ IN CASE WHEN properties.variables[(var_i*2)+1] = "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.variables[var_i*2], configuration_id: $cid})
                MERGE (node)-[:Uses]->(v)
            )
        )
        """

    @classmethod
    def definestr_module(cls):
        return """
        FOREACH (_ IN CASE WHEN properties.cst_value IS NOT NULL THEN [1] ELSE [] END |
            MERGE (cst:Constant {name: properties.cst_name, value: properties.cst_value, configuration_id: $cid})
            MERGE (node)-[:Define]->(cst)
        )
        FOREACH (_ IN CASE WHEN properties.cst_value IS NULL THEN [1] ELSE [] END |
            MERGE (cst2:Constant {name: properties.cst_name, configuration_id: $cid})
            MERGE (node)-[:Define]->(cst2)
        )
        """

    @classmethod
    def removebyid_module(cls):
        return """
        WITH node, properties
        UNWIND properties.ids_to_remove as id
        MERGE (i:Id {value: id, configuration_id: $cid})
        MERGE (node)-[:DoesRemove]->(i)
            
        WITH node, properties
        UNWIND range(0, properties.num_of_ranges-1) as range_i
        UNWIND range(properties.ranges_to_remove[range_i*2], properties.ranges_to_remove[(range_i*2)+1]) as value
        MERGE (i_r:Id {value: value, configuration_id: $cid})
        MERGE (node)-[:DoesRemove]->(i_r)
        """

    @classmethod
    def removebytag_module(cls):
        return """
        WITH node, properties
        UNWIND properties.tags_to_remove as regex
        MERGE (r:Regex {value: regex, configuration_id: $cid})
        MERGE (node)-[:DoesRemove]->(r)
        WITH node, properties, r, regex
        MATCH (t:Tag {configuration_id: $cid}) WHERE t.value =~ regex
        MERGE (r)-[:Match]->(t)
        """

    @classmethod
    def generic_module(cls):
        return """
        FOREACH (_ IN CASE WHEN properties.phase IS NOT NULL THEN [1] ELSE [] END |
            MERGE (p:Phase {value: properties.phase, configuration_id: $cid})
            MERGE (node)-[:InPhase]->(p)
        )

        FOREACH (_ IN CASE WHEN properties.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (i:Id {value: properties.id, configuration_id: $cid})
            MERGE (node)-[:Has]->(i)
        )

        FOREACH (tag IN properties.tags |
            MERGE (t:Tag {value: tag, configuration_id: $cid})
            MERGE (node)-[:Has]->(t)
        )
        """

    @classmethod
    def secrule_module(cls):
        return """
        FOREACH (_ IN CASE WHEN properties.phase IS NOT NULL THEN [1] ELSE [] END |
            MERGE (p:Phase {value: properties.phase, configuration_id: $cid})
            MERGE (node)-[:InPhase]->(p)
        )

        FOREACH (_ IN CASE WHEN properties.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (i:Id {value: properties.id, configuration_id: $cid})
            MERGE (node)-[:Has]->(i)
        )

        FOREACH (tag IN properties.tags |
            MERGE (t:Tag {value: tag, configuration_id: $cid})
            MERGE (node)-[:Has]->(t)
        )

        FOREACH (var_i IN range(0,properties.setenv_num_vars-1) |
            MERGE (env:Collection {name: "ENV", configuration_id: $cid})
            MERGE (sv2:Variable {name: properties.setenv_vars[var_i*2], value: properties.setenv_vars[(var_i*2)+1], configuration_id: $cid})
            MERGE (sv2)-[:IsVariableOf]->(env)
            MERGE (node)-[:Sets]->(sv2)
        )

        FOREACH (vnv IN properties.setenv_vars_no_value |
            MERGE (v2:Variable {name: vnv, configuration_id: $cid})
            MERGE (node)-[:Sets]->(v2)
        )

        FOREACH (unset_var IN properties.setenv_unset |
            MERGE (uv:Variable {name: unset_var, configuration_id: $cid})
            MERGE (node)-[:Unsets]->(uv)
        )

        FOREACH (var_i IN range(0,properties.setvar_num_vars-1) |
            FOREACH (_ IN CASE WHEN properties.setvar_vars[var_i*3] IS NOT NULL THEN [1] ELSE [] END |
                MERGE (env:Collection {name: properties.setvar_vars[var_i*3], configuration_id: $cid})
                MERGE (sv2:Variable {name: properties.setvar_vars[(var_i*3)+1], value: properties.setvar_vars[(var_i*3)+2], configuration_id: $cid})
                MERGE (sv2)-[:IsVariableOf]->(env)
                MERGE (node)-[:Sets]->(sv2)
            )
            FOREACH (_ IN CASE WHEN properties.setvar_vars[var_i*3] IS NULL THEN [1] ELSE [] END |
                MERGE (v2:Variable {name: properties.setvar_vars[(var_i*3)+1], value: properties.setvar_vars[(var_i*3)+2], configuration_id: $cid})
                MERGE (node)-[:Sets]->(v2)
            )
        )

        FOREACH (vnv_i IN range(0,properties.setvar_num_vars_no_value-1) |
            FOREACH (_ IN CASE WHEN properties.setvar_vars_no_value[vnv_i*2] IS NOT NULL THEN [1] ELSE [] END |
                MERGE (env2:Collection {name: properties.setvar_vars_no_value[vnv_i*2], configuration_id: $cid})
                MERGE (v2:Variable {name: properties.setvar_vars_no_value[(vnv_i*2)+1], configuration_id: $cid})
                MERGE (v2)-[:IsVariableOf]->(env2)
                MERGE (node)-[:Sets]->(v2)
            )
            FOREACH (_ IN CASE WHEN properties.setvar_vars_no_value[vnv_i*2] IS NULL THEN [1] ELSE [] END |
                MERGE (v2:Variable {name: properties.setvar_vars_no_value[(vnv_i*2)+1], configuration_id: $cid})
                MERGE (node)-[:Sets]->(v2)
            )
        )

        FOREACH (unset_i IN range(0,properties.setvar_num_unset-1) |
            FOREACH (_ IN CASE WHEN properties.setvar_unset[unset_i*2] IS NOT NULL THEN [1] ELSE [] END |
                MERGE (env3:Collection {name: properties.setvar_unset[unset_i*2], configuration_id: $cid})
                MERGE (uv:Variable {name: properties.setvar_unset[(unset_i*2)+1], configuration_id: $cid})
                MERGE (uv)-[:IsVariableOf]->(env3)
                MERGE (node)-[:Unsets]->(uv)
            )
            FOREACH (_ IN CASE WHEN properties.setvar_unset[unset_i*2] IS NULL THEN [1] ELSE [] END |
                MERGE (uv:Variable {name: properties.setvar_unset[(unset_i*2)+1], configuration_id: $cid})
                MERGE (node)-[:Unsets]->(uv)
            )
        )

        FOREACH (var_i IN range(0,properties.num_of_vars-1) |
            FOREACH (_ IN CASE WHEN properties.secrule_vars[(var_i*2)+1] <> "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.secrule_vars[var_i*2], configuration_id: $cid})
                MERGE (sv:Variable {name: properties.secrule_vars[(var_i*2)+1], configuration_id: $cid})
                MERGE (sv)-[:IsVariableOf]->(v)
                MERGE (node)-[:Uses]->(sv)
            )
            FOREACH (_ IN CASE WHEN properties.secrule_vars[(var_i*2)+1] = "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.secrule_vars[var_i*2], configuration_id: $cid})
                MERGE (node)-[:Uses]->(v)
            )
        )
        """

    @classmethod
    def create_indexes(cls):
        return """
                    CREATE FULLTEXT INDEX cstIndex IF NOT EXISTS
                    FOR (n:Constant|Variable|Collection)
                    ON EACH [n.name]
                """

    # Every value node is now MERGEd with configuration_id in its key, and every
    # analysis query filters on it, so each label needs an index on that property.
    # Without these, a scoped MERGE degrades to a full label scan.
    SCOPED_LABELS = [
        "Location", "VirtualHost", "Predicate", "Constant",
        "Collection", "Variable", "Id", "Tag", "Phase", "Regex",
    ]

    @classmethod
    def create_scope_indexes(cls):
        """One CREATE INDEX statement per scoped label (Neo4j runs these one at a time)."""
        return [
            f"CREATE INDEX cfg_{label.lower()} IF NOT EXISTS "
            f"FOR (n:{label}) ON (n.configuration_id)"
            for label in cls.SCOPED_LABELS
        ]