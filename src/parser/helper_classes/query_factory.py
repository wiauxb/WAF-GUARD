

class QueryFactory:

    @classmethod
    def base_module(cls):
        return """
        UNWIND $batch AS properties
        CREATE (node:$(properties.type))
        SET node = properties.node_props
        WITH node, properties
        
        FOREACH (_ IN CASE WHEN properties.Location IS NOT NULL THEN [1] ELSE [] END |
            MERGE (l:Location {value: properties.Location})
            MERGE (node)-[:AtLocation]->(l)
        )

        FOREACH (_ IN CASE WHEN properties.VirtualHost IS NOT NULL THEN [1] ELSE [] END |
            MERGE (v:VirtualHost {value: properties.VirtualHost})
            MERGE (node)-[:InVirtualHost]->(v)
        )

        FOREACH (condition IN properties.conditions |
            MERGE (c:Predicate {value: condition})
            MERGE (node)-[:Has]->(c)
        )

        FOREACH (constant IN properties.constants |
            MERGE (co:Constant {name: constant})
            MERGE (node)-[:Uses]->(co)
        )

        FOREACH (var_i IN range(0,properties.num_of_variables-1) |
            FOREACH (_ IN CASE WHEN properties.variables[(var_i*2)+1] <> "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.variables[var_i*2]})
                MERGE (sv:Variable {name: properties.variables[(var_i*2)+1]})
                MERGE (sv)-[:IsVariableOf]->(v)
                MERGE (node)-[:Uses]->(sv)
            )
            FOREACH (_ IN CASE WHEN properties.variables[(var_i*2)+1] = "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.variables[var_i*2]})
                MERGE (node)-[:Uses]->(v)
            )
        )
        """

    @classmethod
    def definestr_module(cls):
        return """
        FOREACH (_ IN CASE WHEN properties.cst_value IS NOT NULL THEN [1] ELSE [] END |
            MERGE (cst:Constant {name: properties.cst_name, value: properties.cst_value})
            MERGE (node)-[:Define]->(cst)
        )
        FOREACH (_ IN CASE WHEN properties.cst_value IS NULL THEN [1] ELSE [] END |
            MERGE (cst2:Constant {name: properties.cst_name})
            MERGE (node)-[:Define]->(cst2)
        )
        """

    @classmethod
    def removebyid_module(cls):
        return """
        WITH node, properties
        UNWIND properties.ids_to_remove as id
        MERGE (i:Id {value: id})
        MERGE (node)-[:DoesRemove]->(i)
            
        WITH node, properties
        UNWIND range(0, properties.num_of_ranges-1) as range_i
        UNWIND range(properties.ranges_to_remove[range_i*2], properties.ranges_to_remove[(range_i*2)+1]) as value
        MERGE (i_r:Id {value: value})
        MERGE (node)-[:DoesRemove]->(i_r)
        """

    @classmethod
    def removebytag_module(cls):
        return """
        WITH node, properties
        UNWIND properties.tags_to_remove as regex
        MERGE (r:Regex {value: regex})
        MERGE (node)-[:DoesRemove]->(r)
        WITH node, properties, r, regex
        MATCH (t:Tag) WHERE t.value =~ regex
        MERGE (r)-[:Match]->(t)
        """

    @classmethod
    def generic_module(cls):
        return """
        FOREACH (_ IN CASE WHEN properties.phase IS NOT NULL THEN [1] ELSE [] END |
            MERGE (p:Phase {value: properties.phase})
            MERGE (node)-[:InPhase]->(p)
        )

        FOREACH (_ IN CASE WHEN properties.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (i:Id {value: properties.id})
            MERGE (node)-[:Has]->(i)
        )

        FOREACH (tag IN properties.tags |
            MERGE (t:Tag {value: tag})
            MERGE (node)-[:Has]->(t)
        )
        """

    @classmethod
    def secrule_module(cls):
        return """
        FOREACH (_ IN CASE WHEN properties.phase IS NOT NULL THEN [1] ELSE [] END |
            MERGE (p:Phase {value: properties.phase})
            MERGE (node)-[:InPhase]->(p)
        )

        FOREACH (_ IN CASE WHEN properties.id IS NOT NULL THEN [1] ELSE [] END |
            MERGE (i:Id {value: properties.id})
            MERGE (node)-[:Has]->(i)
        )

        FOREACH (tag IN properties.tags |
            MERGE (t:Tag {value: tag})
            MERGE (node)-[:Has]->(t)
        )

        FOREACH (var_i IN range(0,properties.setenv_num_vars-1) |
            MERGE (env:Collection {name: "ENV"})
            MERGE (sv2:Variable {name: properties.setenv_vars[var_i*2], value: properties.setenv_vars[(var_i*2)+1]})
            MERGE (sv2)-[:IsVariableOf]->(env)
            MERGE (node)-[:Sets]->(sv2)
        )

        FOREACH (vnv IN properties.setenv_vars_no_value |
            MERGE (v2:Variable {name: vnv})
            MERGE (node)-[:Sets]->(v2)
        )

        FOREACH (unset_var IN properties.setenv_unset |
            MERGE (uv:Variable {name: unset_var})
            MERGE (node)-[:Unsets]->(uv)
        )

        FOREACH (var_i IN range(0,properties.setvar_num_vars-1) |
            MERGE (env:Collection {name: properties.setvar_vars[var_i*3]})
            MERGE (sv2:Variable {name: properties.setvar_vars[(var_i*3)+1], value: properties.setvar_vars[(var_i*3)+2]})
            MERGE (sv2)-[:IsVariableOf]->(env)
            MERGE (node)-[:Sets]->(sv2)
        )

        FOREACH (vnv_i IN range(0,properties.setvar_num_vars_no_value-1) |
            MERGE (env2:Collection {name: properties.setvar_vars_no_value[vnv_i*2]})
            MERGE (v2:Variable {name: properties.setvar_vars_no_value[(vnv_i*2)+1]})
            MERGE (v2)-[:IsVariableOf]->(env2)
            MERGE (node)-[:Sets]->(v2)
        )

        FOREACH (unset_i IN range(0,properties.setvar_num_unset-1) |
            MERGE (env3:Collection {name: properties.setvar_unset[unset_i*2]})
            MERGE (uv:Variable {name: properties.setvar_unset[(unset_i*2)+1]})
            MERGE (uv)-[:IsVariableOf]->(env3)
            MERGE (node)-[:Unsets]->(uv)
        )
        """
    """

        FOREACH (var_i IN range(0,properties.num_of_vars-1) |
            FOREACH (_ IN CASE WHEN properties.secrule_vars[(var_i*2)+1] <> "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.secrule_vars[var_i*2]})
                MERGE (sv:Variable {name: properties.secrule_vars[(var_i*2)+1]})
                MERGE (sv)-[:IsVariableOf]->(v)
                MERGE (node)-[:Uses]->(sv)
            )
            FOREACH (_ IN CASE WHEN properties.secrule_vars[(var_i*2)+1] = "" THEN [1] ELSE [] END |
                MERGE (v:Collection {name: properties.secrule_vars[var_i*2]})
                MERGE (node)-[:Uses]->(v)
            )
        )
        """