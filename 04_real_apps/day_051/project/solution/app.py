import streamlit as st
import ollama


def init_session(state: dict) -> dict:
    """
    Idempotently initialise a Streamlit-style session_state dict.

    Streamlit reruns the WHOLE script top-to-bottom on every interaction, so
    initialisation must never overwrite existing data. Only set a key if absent.

    Ensures keys:
        'messages'  -> list of {'role', 'content'} dicts (starts empty)
        'settings'  -> {'model', 'temperature', 'system_prompt'}
    Returns the same dict, mutated in place.
    """
    if 'messages' not in state:
        state['messages'] = []
    if 'settings' not in state:
        state['settings'] = {
            'model': 'llama3.2',
            'temperature': 0.7,
            'system_prompt': 'You are a helpful assistant.',
        }
    return state


def add_message(state: dict, role: str, content: str) -> dict:
    """Append a {'role', 'content'} message to state['messages']; return it."""
    if role not in ('user', 'assistant', 'system'):
        raise ValueError(f'invalid role: {role!r}')
    msg = {'role': role, 'content': content}
    state['messages'].append(msg)
    return msg


def reset_messages(state: dict) -> None:
    """Clear the conversation but keep settings (a 'Clear chat' button)."""
    state['messages'] = []


def validate_user_input(text: str, max_chars: int = 2000) -> tuple[bool, str]:
    """
    Validate raw text from an st.chat_input / st.text_area widget before it is
    sent to the model.

    Returns (is_valid, result):
      - empty/whitespace : (False, 'Please enter a message.')
      - too long         : (False, 'Message too long (max N chars).')
      - valid            : (True, cleaned_text)   # stripped
    """
    cleaned = text.strip()
    if not cleaned:
        return (False, 'Please enter a message.')
    if len(cleaned) > max_chars:
        return (False, f'Message too long (max {max_chars} chars).')
    return (True, cleaned)


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a widget value into [lo, hi]. st.slider bounds live input, but a
    value restored from session_state or a URL param may be out of range."""
    return max(lo, min(hi, value))


def build_settings(model: str, temperature: float, system_prompt: str) -> dict:
    """
    Assemble a validated settings dict from sidebar widget values.
    - temperature clamped to [0.0, 1.0]
    - system_prompt stripped; empty falls back to a default
    """
    sp = system_prompt.strip() or 'You are a helpful assistant.'
    return {
        'model': model,
        'temperature': float(clamp(temperature, 0.0, 1.0)),
        'system_prompt': sp,
    }


def build_messages(state: dict, user_text: str) -> list:
    """
    Build the messages list for ollama.chat:
        [system_prompt] + prior conversation + new user turn.
    Reads the system prompt from state['settings']. Does NOT mutate state.
    """
    settings = state.get('settings', {})
    system_prompt = settings.get('system_prompt', 'You are a helpful assistant.')
    messages = [{'role': 'system', 'content': system_prompt}]
    messages.extend(state.get('messages', []))
    messages.append({'role': 'user', 'content': user_text})
    return messages


def chat_with_history(state: dict, user_text: str, model: str = 'llama3.2') -> str:
    """
    Send the full conversation to Ollama and return the assistant's reply.
    Reads temperature from state['settings']. Returns a fallback string if
    Ollama is unavailable so the app never crashes on a model error.
    """
    settings = state.get('settings', {})
    temperature = settings.get('temperature', 0.7)
    messages = build_messages(state, user_text)
    try:
        response = ollama.chat(
            model=model,
            messages=messages,
            options={'temperature': temperature},
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f'[Model unavailable: {e}]' 


def format_transcript(messages: list) -> str:
    """
    Render the conversation as a plain-text transcript for st.download_button.
    One block per turn as 'ROLE: content'. System messages are skipped.
    """
    lines = []
    for m in messages:
        role = m.get('role', '')
        if role == 'system':
            continue
        lines.append(f"{role.upper()}: {m.get('content', '')}")
    return '\n\n'.join(lines)


def chat_stats(messages: list) -> dict:
    """
    Compute display metrics for st.metric widgets. System messages excluded.
    Returns: {'total', 'user', 'assistant', 'chars'}.
    """
    non_system = [m for m in messages if m.get('role') != 'system']
    user = sum(1 for m in non_system if m.get('role') == 'user')
    assistant = sum(1 for m in non_system if m.get('role') == 'assistant')
    chars = sum(len(m.get('content', '')) for m in non_system)
    return {
        'total': len(non_system),
        'user': user,
        'assistant': assistant,
        'chars': chars,
    }


class ChatApp:
    """
    The logic core of the Streamlit chat app. One instance is stored in
    st.session_state and reused across reruns. The Streamlit layer only calls
    these methods and renders their return values — no business logic in the UI.

    Usage (inside app.py):
        if 'app' not in st.session_state:
            st.session_state.app = ChatApp()
        app = st.session_state.app
        reply = app.send(prompt)          # on chat_input submit
        st.metric('Messages', app.stats()['total'])
    """

    def __init__(self, model: str = 'llama3.2',
                 system_prompt: str = 'You are a helpful assistant.'):
        self.state = {}
        init_session(self.state)
        self.state['settings']['model'] = model
        self.state['settings']['system_prompt'] = system_prompt
        self.model = model

    def send(self, user_text: str) -> str:
        """
        Validate -> append user turn -> call model -> append assistant turn.
        Returns the assistant reply, or a validation error string (in which
        case NOTHING is appended to the conversation).
        """
        ok, result = validate_user_input(user_text)
        if not ok:
            return result
        add_message(self.state, 'user', result)
        reply = chat_with_history(self.state, result, self.model)
        add_message(self.state, 'assistant', reply)
        return reply

    def stats(self) -> dict:
        return chat_stats(self.state['messages'])

    def transcript(self) -> str:
        return format_transcript(self.state['messages'])

    def reset(self) -> None:
        reset_messages(self.state)


# ---- Streamlit UI (runs only under: streamlit run app.py) ----
st.set_page_config(page_title="Local AI Chat", page_icon="💬")
st.title("💬 Local AI Chat")

# One ChatApp instance per browser session, persisted across reruns.
if "app" not in st.session_state:
    st.session_state.app = ChatApp()
app = st.session_state.app

# Sidebar: settings + live stats + controls.
with st.sidebar:
    st.header("Settings")
    temp = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    sysp = st.text_area("System prompt", app.state["settings"]["system_prompt"])
    app.state["settings"] = build_settings(app.model, temp, sysp)

    st.header("Stats")
    s = app.stats()
    c1, c2 = st.columns(2)
    c1.metric("Messages", s["total"])
    c2.metric("Characters", s["chars"])

    if st.button("Clear chat"):
        app.reset()
        st.rerun()

    st.download_button("Download transcript", app.transcript(), "chat.txt")

# Replay the whole conversation from session state.
for m in app.state["messages"]:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Handle a new user turn.
prompt = st.chat_input("Type a message...")
if prompt:
    with st.spinner("Thinking..."):
        app.send(prompt)          # appends user + assistant to session state
    st.rerun()                    # rerun so the replay loop renders them
