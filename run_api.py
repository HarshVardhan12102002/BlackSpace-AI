import json
import os
from typing import List

from io import BytesIO

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query, UploadFile, File, Body, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime
from supabase import create_client

import PyPDF2

from server.api import BlackSpaceAPI

# Load environment variables
load_dotenv()

# Access environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CORS_ORIGINS = ["http://localhost:3000", "https://blackspace-ai.vercel.app"]
CORS_METHODS = ["GET", "POST"]

# Initialize FastAPI app
app = FastAPI()

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=CORS_METHODS,
    allow_headers=["*"],
)

from fastapi import Header, HTTPException, Depends

class AuthenticatedResponse(BaseModel):
    message: str

def get_user_from_key(authorization: str) -> None:
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized")

    response = supabase_client.table("users").select("*").eq("key", authorization).execute()

    return response.data[0]


@app.get("/")
async def say_hello():
    return {"message": "Hello World"}


class MessageList(BaseModel):
    session_id: str
    human_say: str


@app.post("/chat/{chat_id}")
async def chat_with_sales_agent(chat_id, session_id: str = Body(None), human_say: str = Body(...), stream: bool = Query(False), file: UploadFile = File(None)):
    sales_api = None
    user = get_user_from_key(chat_id)

    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    print(user["id"])

    if session_id is None:
      new_session_payload = {
        "user_id": user["id"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
        }
      
      new_session = supabase_client.table("sessions").insert(new_session_payload).execute()
      session_id = new_session.data[0]["id"]


    conversations = supabase_client.table("conversations").select("*").eq("session_id", session_id).limit(20).execute()

    conversations_history = []

    for conversation in conversations.data:
        conversations_history.append(conversation["text"])

    sales_api = BlackSpaceAPI(
            config_path=user["config"],
            verbose=True,
            product_catalog=user["products"],
            model_name=os.getenv("GPT_MODEL", "gpt-3.5-turbo-0613"),
            use_tools=os.getenv("USE_TOOLS_IN_API", "True").lower()
            in ["true", "1", "t"],
            conversation_history=conversations_history
        )

    extracted_text = ""

    if file and file.filename.endswith(".pdf"):
        file_content = await file.read()
        pdf_reader = PyPDF2.PdfFileReader(BytesIO(file_content))
        num_pages = pdf_reader.numPages

        for page_num in range(num_pages):
            page = pdf_reader.getPage(page_num)
            extracted_text += page.extractText()


    human_input = "User: " + human_say  + extracted_text + " <END_OF_TURN>"

    new_user_conversation = {
        "session_id": session_id,
        "text": human_input,
        "type": "human",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    supabase_client.table("conversations").insert(new_user_conversation).execute()

    if stream:
        async def stream_response():
            stream_gen = sales_api.do_stream(conversations_history, human_say + extracted_text)
            async for message in stream_gen:
                data = {"token": message}
                yield json.dumps(data).encode("utf-8") + b"\n"

        return StreamingResponse(stream_response())
    else:
        response = await sales_api.do(human_say + extracted_text)

        new_ai_conversation_payload = {
        "session_id": session_id,
        "text": response["reply"],
        "type": "ai",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
        }

        supabase_client.table("conversations").insert(new_ai_conversation_payload).execute()

        response["session_id"] = session_id

        return response

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase_client = create_client(supabase_url, supabase_key)

class ConversationCreate(BaseModel):
    session_id: int
    text: str
    type: str

class UserCreate(BaseModel):
    name: str
    config: dict
    products: str

class SessionCreate(BaseModel):
    user_id: int

# Conversation API Endpoints
@app.post("/conversations/", status_code=status.HTTP_201_CREATED)
def create_conversation(conversation_data: ConversationCreate):
    data = {
        "session_id": conversation_data.session_id,
        "text": conversation_data.text,
        "type": conversation_data.type,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    try:
        response = supabase_client.table("conversations").insert(data).execute()
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/conversations/{session_id}/")
def read_conversation(session_id: int):
    try:
        response = supabase_client.table("conversations").select("*").eq("session_id", session_id).execute()
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# User API Endpoints
@app.post("/users/", status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate):
    data = {
        "name": user_data.name,
        "config": user_data.config,
        "products": user_data.products,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    try:
        response = supabase_client.table("users").insert(data).execute()
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/users/{user_id}/")
def read_user(user_id: int):
    try:
        response = supabase_client.table("users").select("*").eq("id", user_id).execute()
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Session API Endpoints
@app.post("/sessions/", status_code=status.HTTP_201_CREATED)
def create_session(session_data: SessionCreate):
    data = {
        "user_id": session_data.user_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    try:
        response = supabase_client.table("sessions").insert(data).execute()
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.get("/sessions/{session_id}/")
def read_session(session_id: int):
    try:
        response = supabase_client.table("sessions").select("*").eq("id", session_id).execute()
        return response
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Main entry point
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
