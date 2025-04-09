from fastapi import FastAPI, WebSocket
from basicGraph import graph_runnable 
from basicGraph import invoke_basic_graph
from basicGraph import stream_basic_graph
from uiGraph import invoke_graph
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from langchain_core.messages.base import message_to_dict
import time
import json
import asyncio
from functools import partial

app = FastAPI()



class ChatInput(BaseModel):
    messages: list[dict]
    # thread_id: str

@app.post("/chat/basic_graph")
def chat(input: ChatInput):
    # config = {"configurable": {"thread_id": input.thread_id}}
    print("Basic graph endpoint", flush=True)
    response = invoke_basic_graph(input.messages)
    return response

@app.post("/chat/ui_graph")
def chat_ui(input: ChatInput):
    # config = {"configurable": {"thread_id": input.thread_id}}
    print("Ui graph endpoint", flush=True)
    response = invoke_graph(input.messages)
    return response

@app.post("/chat_stream")
async def chat_stream(input: ChatInput):
    # config = {"configurable": {"thread_id": input.thread_id}}
    print(input, flush=True)
    def event_generator():
        for event in graph_runnable.stream({"messages":"write a 500 words essay about AI"},stream_mode="messages"):
            print(event, flush=True)
            message=message_to_dict(event[0])
            payload=json.dumps(message)
            yield payload
    
    return StreamingResponse(event_generator(), media_type="application/json")


# WebSocket endpoint for real-time streaming
@app.websocket("/ws")     
async def websocket_endpoint(websocket: WebSocket):
    print("WebSocket connection established", flush=True)
    try:
        # config = {"configurable": {"thread_id": thread_id}}
        await websocket.accept()
        while True:
            data = await websocket.receive_text()
            async for event in graph_runnable.astream({"messages":"how many hosts are in the config?"},stream_mode="messages"):
                print(event, flush=True)
                await websocket.send_text(event[0].content)
                
#             response="""Artificial Intelligence (AI) has emerged as one of the most transformative technologies of the 21st century. It encompasses a broad range of technologies that enable machines to mimic human intelligence, including learning, reasoning, problem-solving, and understanding language. AI's profound impact is evident across various sectors, including healthcare, finance, transportation, and entertainment, reshaping how we live, work, and interact with the world.

#         At the core of AI is machine learning, a subset focusing on the development of algorithms that allow computers to learn from and make predictions based on data. Through machine learning, systems can improve their performance on tasks over time without being explicitly programmed. This ability to learn and adapt makes AI a versatile tool in tackling complex challenges. For instance, in healthcare, AI systems can analyze vast datasets to identify patterns and make diagnoses with increasing accuracy. This capability not only augments the expertise of medical professionals but also speeds up the diagnostic process, potentially saving lives.
# """
#             for word in response.split(" "):
#                 await websocket.send_text(word)
#                 await asyncio.sleep(0.1)
#                 print(word, flush=True)
    except Exception as e:
        print(f"Error: {e}", flush=True)
        await websocket.close()
