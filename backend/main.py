from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from backend.agent import agent_app

app = FastAPI()

# Allow all origins (adjust in production if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root route for health check or browser preview
@app.get("/", response_class=PlainTextResponse)
def root():
    return "✅ TailorTalk backend is live."

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        data = await request.json()
        if "text" not in data:
            raise HTTPException(status_code=400, detail="Missing 'text' field in request body.")
        result = agent_app.invoke(data)
        return result
    except Exception as e:
        return {"error": str(e)}