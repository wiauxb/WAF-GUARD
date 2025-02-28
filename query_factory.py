

class QueryFactory:

    @classmethod
    def base_module(cls):
        return """
        UNWIND $batch AS properties
        CREATE (node:$(properties.type))
        SET node = properties
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

        FOREACH (variable IN properties.variables |
            MERGE (v:Variable {name: variable})
            MERGE (node)-[:Uses]->(v)
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

        WITH node, properties
        UNWIND range(0, properties.num_of_vars-1) as var_i
        WITH node, properties, properties.secrule_vars[var_i*2] as var, properties.secrule_vars[(var_i*2)+1] as subvar
        FOREACH (_ IN CASE WHEN subvar IS NOT NULL AND subvar <> "" THEN [1] ELSE [] END |
            MERGE (v:Variable {name: var})
            MERGE (sv:SubVariable {name: subvar})
            MERGE (sv)-[:IsSubVariableOf]->(v)
            MERGE (node)-[:Uses]->(sv)
        )
        FOREACH (_ IN CASE WHEN subvar IS NULL OR subvar = "" THEN [1] ELSE [] END |
            MERGE (v:Variable {name: var})
            MERGE (node)-[:Uses]->(v)
        )
        """