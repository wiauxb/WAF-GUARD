from fastapi import FastAPI, WebSocket
from basicGraph import graph_runnable 
from basicGraph import invoke_basic_graph
from pydantic import BaseModel

app = FastAPI()



class ChatInput(BaseModel):
    messages: list[dict]
    # thread_id: str

@app.post("/chat")
def chat(input: ChatInput):
    # config = {"configurable": {"thread_id": input.thread_id}}
    print(input.messages, flush=True)
    response = invoke_basic_graph(input.messages)
    return response


# WebSocket endpoint for real-time streaming
@app.websocket("/ws")     
async def websocket_endpoint(websocket: WebSocket):
    print("WebSocket connection established")
    # config = {"configurable": {"thread_id": thread_id}}
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        async for event in graph_runnable.astream({"messages": [data]}, stream_mode="messages"):
            print(event)
            await websocket.send_text(event[0].content)