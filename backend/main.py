from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.agent import agent_app, State  # Import State model

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        if "text" not in data:
            raise HTTPException(status_code=400, detail="Missing 'text' field in request body.")

        result: State = agent_app.invoke(data)
        return result.dict()  # ✅ Convert Pydantic State model to dict
    except Exception as e:
        return {"error": str(e)}