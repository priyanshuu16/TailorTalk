from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from backend.agent import agent_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    result = agent_app.invoke(data)
    return result
