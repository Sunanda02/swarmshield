from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="SwarmShield Mock Target")


class ChatRequest(BaseModel):
    input: str


@app.post("/chat")
def chat(request: ChatRequest):
    prompt = request.input

    return {
        "output": f"Mock AI received your prompt: {prompt}"
    }


@app.get("/health")
def health():
    return {"status": "ok", "app": "Mock Target"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)