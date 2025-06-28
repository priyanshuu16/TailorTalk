from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.agent import agent_app, State

app = FastAPI()

# ✅ CORS setup — allow all origins (change for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ✅ Replace with frontend URL in production
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

        # ✅ Validate incoming data using State schema
        state_input = State(**data)

        # ✅ IMPORTANT: Convert to dict before passing to LangGraph
        result = agent_app.invoke(state_input.dict())

        # ✅ Return response as JSON
        return result if isinstance(result, dict) else result.dict()

    except Exception as e:
        return {"error": str(e)}