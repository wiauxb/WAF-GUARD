# api/dependencies.py
# from fastapi import Depends
# from sqlalchemy.orm import Session
# from langgraph.checkpoint.postgres import PostgresSaver
# from shared.database import get_postgres_db, get_langgraph_checkpointer
# from services.chatbot.service import ChatbotService

# def get_chatbot_service(
#     db: Session = Depends(get_postgres_db)
# ) -> ChatbotService:
#     """Dependency that provides ChatbotService with checkpointer"""
#     checkpointer = get_langgraph_checkpointer()
#     return ChatbotService(db, checkpointer)