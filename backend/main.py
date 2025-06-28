from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.agent import agent_app, State

app = FastAPI()

# Allow all origins for development; restrict in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()

        if "text" not in data:
            raise HTTPException(status_code=400, detail="Missing 'text' in request.")

        # ✅ Initialize State object from incoming data
        state_input = State(**data)

        # ✅ Pass as dictionary to LangGraph (required)
        result = agent_app.invoke(state_input.dict())

        # ✅ Return response as JSON
        return result if isinstance(result, dict) else result.dict()

    except Exception as e:
        return {"error": str(e)}
