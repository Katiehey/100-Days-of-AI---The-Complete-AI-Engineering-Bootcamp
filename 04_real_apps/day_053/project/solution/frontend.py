import streamlit as st
import httpx


def check_health(client) -> bool:
    """Ping the backend's GET /health through an injected HTTP client.

    Returns True only if the request succeeds with 200 AND status == 'ok'.
    Any exception (backend down, connection refused) -> False, never raises.
    The `client` is duck-typed: an httpx.Client in production, a TestClient in
    tests — both expose .get / .post / .request.
    """
    try:
        resp = client.get('/health')
        return resp.status_code == 200 and resp.json().get('status') == 'ok'
    except Exception:
        return False


def post_chat(client, message: str, temperature: float = 0.7) -> dict:
    """POST /chat honouring the JSON contract {message, temperature}.

    Returns the parsed {reply, model} on 200. On a non-200 status returns
    {'error': ..., 'status': code}; on a connection failure returns
    {'error': ...}. The frontend never sees a raw exception.
    """
    try:
        resp = client.post('/chat', json={'message': message, 'temperature': temperature})
    except Exception as e:
        return {'error': f'request failed: {e}'}
    if resp.status_code != 200:
        return {'error': f'backend returned {resp.status_code}', 'status': resp.status_code}
    return resp.json()


def request_json(client, method: str, path: str, payload: dict = None) -> dict:
    """Call the backend and normalise EVERY outcome into one envelope:

        {'ok': bool, 'status': int | None, 'data': dict | None, 'error': str | None}

    - success (2xx):        ok=True,  status=code, data=json
    - error status (4xx/5xx): ok=False, status=code, error='HTTP <code>'
    - connection failure:   ok=False, status=None, error='connection error: ...'

    One shape for the whole frontend to branch on — no scattered try/except.
    """
    try:
        resp = client.request(method, path, json=payload)
    except Exception as e:
        return {'ok': False, 'status': None, 'data': None,
                'error': f'connection error: {e}'}
    ok = 200 <= resp.status_code < 300
    try:
        data = resp.json()
    except Exception:
        data = None
    return {
        'ok':     ok,
        'status': resp.status_code,
        'data':   data if ok else None,
        'error':  None if ok else f'HTTP {resp.status_code}',
    }


class AIAppClient:
    """The frontend's typed gateway to the AI backend.

    Wraps an injected HTTP client (httpx.Client in production, TestClient in
    tests) so the exact same code runs against a live server or in-process.
    Every method returns plain data the UI can render — no HTTP details leak out.
    """

    def __init__(self, client):
        self.client = client

    def health(self) -> bool:
        return check_health(self.client)

    def chat(self, message: str, temperature: float = 0.7) -> dict:
        return post_chat(self.client, message, temperature)

    def templates(self) -> list:
        env = request_json(self.client, 'GET', '/templates')
        return env['data']['templates'] if env['ok'] else []

    def render(self, name: str, topic: str, temperature: float = 0.7) -> dict:
        env = request_json(self.client, 'POST', f'/render/{name}',
                           {'message': topic, 'temperature': temperature})
        return env['data'] if env['ok'] else {'error': env['error']}


BACKEND_URL = 'http://localhost:8000'

st.set_page_config(page_title='Full-Stack AI Chat', page_icon='🔗')
st.title('🔗 Full-Stack AI Chat')


@st.cache_resource
def get_client():
    """One HTTP client + gateway per session (cached across reruns)."""
    return AIAppClient(httpx.Client(base_url=BACKEND_URL, timeout=60.0))


api = get_client()

# Health badge: does the backend answer?
if api.health():
    st.success('Backend online')
else:
    st.error('Backend offline \u2014 start it with:  uvicorn backend:app --reload')

if 'messages' not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m['role']):
        st.markdown(m['content'])

prompt = st.chat_input('Type a message...')
if prompt:
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.spinner('Calling backend...'):
        result = api.chat(prompt)
    reply = result.get('reply') or result.get('error') or '(no response)'
    st.session_state.messages.append({'role': 'assistant', 'content': reply})
    st.rerun()
