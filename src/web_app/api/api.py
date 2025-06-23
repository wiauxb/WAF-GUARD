import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from dotenv import load_dotenv

# Import routers
from .routers import cypher, configs, nodes, storage, database, directives

# Load environment variables
load_dotenv()


# Initialize FastAPI app
app = FastAPI()

# Include all routers
app.include_router(cypher.router)
app.include_router(nodes.router)
app.include_router(configs.router)
app.include_router(storage.router)
app.include_router(database.router)
app.include_router(directives.router)

@app.get("/health")
async def health():
    return {"status": "ok"}