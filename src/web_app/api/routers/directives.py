import pandas as pd
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

from ..db.connections import neo4j_driver, parsed_conn

router = APIRouter(prefix="/directives", tags=["Directive Operations"])


class IdRequest(BaseModel):
    id: str


class TagRequest(BaseModel):
    tag: str


@router.get("/remove_by/id")
async def get_remove_by_id(request: IdRequest = None):
    """
    Get directives that are removed by a specific ID.
    """
    id = request.id if request else None
    try:
        # Query to find directives that are removed by the given ID
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n:secruleremovebyid)-[:DoesRemove]->(i:Id {value: $id})
                RETURN n
                """,
                {"id": id}
            )
            records = [record["n"] for record in result]
            df = pd.DataFrame(records).fillna(-1)
            return {"results": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving directives: {str(e)}")


@router.get("/remove_by/tag")
async def get_remove_by_tag(request: TagRequest = None):
    """
    Get directives that are removed by a specific tag.
    """
    tag = request.tag if request else None
    try:
        # Query to find directives that are removed by the given tag
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n:secruleremovebytag)-[*..2]->(t:Tag {value: $tag})
                RETURN n
                """,
                {"tag": tag}
            )
            records = [record["n"] for record in result]
            df = pd.DataFrame(records).fillna(-1)
            return {"results": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving directives: {str(e)}")


@router.get("/id")
async def get_directives_by_id(request: IdRequest = None):
    """
    Get directives with a specific ID.
    """
    id = request.id if request else None
    try:
        # Query to find directives with the given ID
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n)-[:Has]->(i:Id {value: $id})
                RETURN n
                """,
                {"id": id}
            )
            records = [record["n"] for record in result]
            df = pd.DataFrame(records).fillna(-1)
            return {"results": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving directives: {str(e)}")


@router.get("/tag")
async def get_directives_by_tag(request: TagRequest = None):
    """
    Get directives with a specific tag.
    """
    tag = request.tag if request else None
    try:
        # Query to find directives with the given tag
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n)-[:Has]->(t:Tag {value: $tag})
                RETURN n
                """,
                {"tag": tag}
            )
            records = [record["n"] for record in result]
            df = pd.DataFrame(records).fillna(-1)
            return {"results": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving directives: {str(e)}")

@router.get("/removed/{nodeid}")
async def get_remover_directives(nodeid: int):
    """
    Get directives that removed a specific node.
    It does not matter if it removed by ID or by tag.
    """
    try:
        # Query to find directives that removed the given node ID
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n)-[:DoesRemove]->(crt)-[*..2]-(a {node_id: $nodeid})
                WHERE n.node_id > a.node_id
                RETURN LABELS(crt) as type, crt, n
                """,
                {"nodeid": nodeid}
            )
            records = []
            for record in result:
                records.append((record['type'][0], record['crt']["value"], record['n']))
            removers = pd.DataFrame(records, columns=['criterion_type', 'criterion_value', 'directive']).fillna(-1)
            return {"results": removers.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving directives: {str(e)}")


@router.get("/id/{nodeid}")
async def get_directives_by_nodeid(nodeid: int):
    """
    Get directives with a specific node ID.
    """
    try:
        # Query to find directives with the given node ID
        with neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (n {node_id: $nodeid})
                RETURN n
                """,
                {"nodeid": nodeid}
            )
            records = [record["n"] for record in result]
            df = pd.DataFrame(records).fillna(-1)
            return {"results": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving directives: {str(e)}")
