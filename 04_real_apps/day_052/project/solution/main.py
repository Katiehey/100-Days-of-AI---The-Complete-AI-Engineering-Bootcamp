import warnings
warnings.filterwarnings('ignore')
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import ollama


class ChatRequest(BaseModel):
    """Request body for the chat endpoints."""
    message: str = Field(min_length=1, description='User message for the model')
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Response body returned by the chat endpoints."""
    reply: str
    model: str


class HealthResponse(BaseModel):
    """Response body for the health check."""
    status: str
    model: str


PROMPT_TEMPLATES = {
    'summary':  'Summarize the following topic in two sentences: {topic}',
    'explain':  'Explain {topic} to a complete beginner.',
    'critique': 'List three criticisms of {topic}.',
}


def run_model(model: str, prompt: str, temperature: float = 0.7) -> str:
    """Call Ollama once and return the reply text. Raises on model error."""
    resp = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': temperature},
    )
    return resp['message']['content'].strip()


def build_api(model: str = 'llama3.2') -> FastAPI:
    """Assemble the complete AI API: health, templates, chat, and templated chat."""
    app = FastAPI(title='AI API', version='1.0.0')

    @app.get('/health', response_model=HealthResponse)
    def health():
        return HealthResponse(status='ok', model=model)

    @app.get('/templates')
    def list_templates():
        return {'templates': list(PROMPT_TEMPLATES.keys())}

    @app.post('/chat', response_model=ChatResponse)
    def chat(req: ChatRequest):
        try:
            return ChatResponse(reply=run_model(model, req.message, req.temperature),
                                model=model)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')

    @app.post('/render/{name}', response_model=ChatResponse)
    def render_chat(name: str, req: ChatRequest):
        if name not in PROMPT_TEMPLATES:
            raise HTTPException(status_code=404, detail=f'template {name!r} not found')
        prompt = PROMPT_TEMPLATES[name].format(topic=req.message)
        try:
            return ChatResponse(reply=run_model(model, prompt, req.temperature),
                                model=model)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f'Model unavailable: {e}')

    return app


app = build_api()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
