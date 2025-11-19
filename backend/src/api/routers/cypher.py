import pandas as pd
from fastapi import APIRouter
from pyvis.network import Network

from ..db.connections import neo4j_driver
from ..models.models import CypherQuery

router = APIRouter(prefix="/cypher", tags=["Cypher Queries"])


@router.post("/run")
async def run_cypher(query: CypherQuery):
    with neo4j_driver.session() as session:
        result = session.run(query.query)
        graph = result.graph()
        net = Network()
        for node in graph.nodes:
            net.add_node(node.element_id, label=list(node.labels)[0],
                         title="\n".join(
                             [f"{k}: {v if len(str(v)) < 50 else f'{str(v)[:47]}...'}" for k, v in node.items()]))
        for rel in graph.relationships:
            net.add_edge(rel.nodes[0].element_id, rel.nodes[1].element_id, label=rel.type)
    net.set_options("""
const options = {
  "edges": {
    "arrows": {
      "to": {
        "enabled": true
      }
    }
  },
  "physics": {
    "barnesHut": {
      "gravitationalConstant": -9950
    },
    "minVelocity": 0.75
  }
}
                    """)
    # net.show_buttons()
    net.show("tmp.html", notebook=False)
    with open("tmp.html", "r") as f:
        res = f.read()
    return {"html": res}


@router.post("/to_json")
async def run_cypher_to_json(query: CypherQuery):
    with neo4j_driver.session() as session:
        result = session.run(query.query)
        res_col = result.keys()[0]
        records = [record[res_col] for record in result]
        df = pd.DataFrame(records).fillna(-1)
    return {"df": df.to_dict(orient="records")}
