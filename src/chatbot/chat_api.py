from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from langchain_core.messages.base import message_to_dict
import time
import json
import asyncio
from functools import partial
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from typing import Annotated
import bcrypt
from langchain_core.messages import messages_to_dict


from uiGraphCP import invoke_graph
from Graph.uiGraph import UIGraph
from db.connection import get_pool
from db.users import register_user, get_user_by_username
from db.threads import get_threads_db, create_thread, delete_thread, get_thread_messages

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str

class ChatInput(BaseModel):
    messages: list[dict]
    config:dict



app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
uiGraph= UIGraph(get_pool(),checkpointer=True)  # Assuming checkpointer is not needed for this example




@app.post("/chat/ui_graph")
def chat_ui(input: ChatInput):
    print("Ui graph endpoint", flush=True)
    print("Input messages:", input.messages, flush=True)
    print("Input config:", input.config, flush=True)
    response=uiGraph.invoke(input.messages,configuration=input.config)
    print("Response from UI graph:", response, flush=True)
    return response



def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def authenticate_user(username: str, password: str):
    user = get_user_by_username(username)
    print(f"Authenticating user: {user}", flush=True)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user_by_username(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user



@app.post("/chat/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    print("Login endpoint called", flush=True)
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.post("/chat/register", response_model=Token)
async def register(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    if get_user_by_username(form_data.username):
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_pw = get_password_hash(form_data.password)
    # fake_users_db[form_data.username] = {"username": form_data.username, "hashed_password": hashed_pw}
    # fake_threads_db[form_data.username] = []  # init empty thread list
    id= register_user(form_data.username, hashed_pw)
    print(f"User registered with ID: {id}", flush=True)

    token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


@app.get("/chat/threads")
async def get_threads(user: Annotated[str, Depends(get_current_user)]):
    return get_threads_db(user["users_id"])

@app.post("/chat/threads")
async def create_new_thread(user: Annotated[str, Depends(get_current_user)]):
    print(f"Creating new thread for user: {user}", flush=True)
    thread_id = create_thread(user["users_id"])
    return thread_id

@app.get("/chat/threads/{thread_id}")
async def fetch_thread_messages(thread_id: str, user: Annotated[str, Depends(get_current_user)]):
    print(f"Fetching messages for thread ID: {thread_id} for user: {user}", flush=True)
    messages = get_thread_messages(thread_id)
    return messages_to_dict(messages)






# @app.post("/chat/basic_graph")
# def chat(input: ChatInput):
#     # config = {"configurable": {"thread_id": input.thread_id}}
#     print("Basic graph endpoint", flush=True)
#     response = invoke_basic_graph(input.messages)
#     return response

# @app.post("/chat_stream")
# async def chat_stream(input: ChatInput):
#     # config = {"configurable": {"thread_id": input.thread_id}}
#     print(input, flush=True)
#     def event_generator():
#         for event in graph_runnable.stream({"messages":"write a 500 words essay about AI"},stream_mode="messages"):
#             print(event, flush=True)
#             message=message_to_dict(event[0])
#             payload=json.dumps(message)
#             yield payload
    
#     return StreamingResponse(event_generator(), media_type="application/json")


# # WebSocket endpoint for real-time streaming
# @app.websocket("/ws")     
# async def websocket_endpoint(websocket: WebSocket):
#     print("WebSocket connection established", flush=True)
#     try:
#         # config = {"configurable": {"thread_id": thread_id}}
#         await websocket.accept()
#         while True:
#             data = await websocket.receive_text()
#             async for event in graph_runnable.astream({"messages":"how many hosts are in the config?"},stream_mode="messages"):
#                 print(event, flush=True)
#                 await websocket.send_text(event[0].content)
                
# #             response="""Artificial Intelligence (AI) has emerged as one of the most transformative technologies of the 21st century. It encompasses a broad range of technologies that enable machines to mimic human intelligence, including learning, reasoning, problem-solving, and understanding language. AI's profound impact is evident across various sectors, including healthcare, finance, transportation, and entertainment, reshaping how we live, work, and interact with the world.

# #         At the core of AI is machine learning, a subset focusing on the development of algorithms that allow computers to learn from and make predictions based on data. Through machine learning, systems can improve their performance on tasks over time without being explicitly programmed. This ability to learn and adapt makes AI a versatile tool in tackling complex challenges. For instance, in healthcare, AI systems can analyze vast datasets to identify patterns and make diagnoses with increasing accuracy. This capability not only augments the expertise of medical professionals but also speeds up the diagnostic process, potentially saving lives.
# # """
# #             for word in response.split(" "):
# #                 await websocket.send_text(word)
# #                 await asyncio.sleep(0.1)
# #                 print(word, flush=True)
#     except Exception as e:
#         print(f"Error: {e}", flush=True)
#         await websocket.close()
