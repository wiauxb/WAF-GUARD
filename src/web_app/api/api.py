import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from .routers import cypher, configs, nodes, storage, database, directives

# Load environment variables


# Initialize FastAPI app
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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