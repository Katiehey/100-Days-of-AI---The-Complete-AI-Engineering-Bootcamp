import warnings
warnings.filterwarnings('ignore')
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import ollama


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, description='User message for the model')
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    reply: str
    model: str


class HealthResponse(BaseModel):
    status: str
    model: str


PROMPT_TEMPLATES = {
    'summary':  'Summarize the following topic in two sentences: {topic}',
    'explain':  'Explain {topic} to a complete beginner.',
    'critique': 'List three criticisms of {topic}.',
}


def run_model(model: str, prompt: str, temperature: float = 0.7) -> str:
    resp = ollama.chat(
        model=model,
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': temperature},
    )
    return resp['message']['content'].strip()


def build_api(model: str = 'llama3.2') -> FastAPI:
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


def add_cors(app: FastAPI, origins: list) -> FastAPI:
    """Enable CORS so a browser front-end on a DIFFERENT origin can call this API.

    A browser enforces the same-origin policy: JavaScript on http://localhost:8501
    may not call http://localhost:8000 unless the server opts in with CORS
    headers. CORSMiddleware adds the `access-control-allow-origin` header (and
    answers preflight OPTIONS requests) for the origins you allow.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    return app


app = build_api()
add_cors(app, ['http://localhost:8501'])


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
