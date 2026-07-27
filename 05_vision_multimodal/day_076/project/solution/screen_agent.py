"""screen_agent.py — Day 076: Multimodal Screen-Understanding Agent.

Two-LLM pipeline: vision LLM (llava) describes the screen;
text LLM (llama3.2) reasons about a task in that visual context.

Functions:
    capture_screenshot  — PIL.ImageGrab -> PIL Image
    analyze_screenshot  — PIL Image + question -> str (llava)
    describe_screen     — full scene description
    read_screen_text    — verbatim text extraction
    find_elements       — list UI elements of a given type
    answer_about_screen — ad-hoc visual question
    run_screen_task     — vision + text LLM -> {description, answer, task}
    ScreenAgent         — stateful assistant, 3 injection points

Setup:
    pip install pillow ollama
    ollama pull llava
    ollama pull llama3.2
"""
import io
import base64
from pathlib import Path


def capture_screenshot(region=None, screenshot_fn=None):
    """Capture a screenshot of the screen or a rectangular region.

    Args:
        region:        (left, top, right, bottom) pixel box, or None for full screen
        screenshot_fn: callable(region) -> PIL.Image for testing
    Returns:
        PIL Image in RGB mode
    """
    if screenshot_fn is not None:
        return screenshot_fn(region)
    from PIL import ImageGrab
    return ImageGrab.grab(bbox=region)


def analyze_screenshot(image, question, analyze_fn=None):
    """Ask a vision LLM a question about an image.

    Args:
        image:      PIL Image
        question:   natural-language question about the image
        analyze_fn: callable(image, question) -> str for testing
    Returns:
        model answer string
    """
    if analyze_fn is not None:
        return analyze_fn(image, question)
    import ollama
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    resp = ollama.chat(
        model='llava',
        messages=[{'role': 'user', 'content': question, 'images': [img_b64]}],
    )
    return resp['message']['content']


def describe_screen(image, analyze_fn=None):
    """Describe what is visible on screen."""
    return analyze_screenshot(
        image,
        'Describe what you see on this screen in detail.',
        analyze_fn=analyze_fn,
    )


def read_screen_text(image, analyze_fn=None):
    """Extract all visible text from the screen verbatim."""
    return analyze_screenshot(
        image,
        'Extract all visible text from this image exactly as it appears.',
        analyze_fn=analyze_fn,
    )


def find_elements(image, element_type, analyze_fn=None):
    """Find UI elements of a given type on screen."""
    question = (
        f'List all {element_type} elements visible in this screenshot. '
        'Be specific about their labels, text, or content.'
    )
    return analyze_screenshot(image, question, analyze_fn=analyze_fn)


def answer_about_screen(image, question, analyze_fn=None):
    """Answer an ad-hoc question about what is visible on screen."""
    return analyze_screenshot(image, question, analyze_fn=analyze_fn)


def run_screen_task(image, task, analyze_fn=None, llm_fn=None):
    """Analyze screenshot with vision LLM, then reason about task with text LLM.

    Args:
        image:      PIL Image (screenshot)
        task:       task or question to answer using visual context
        analyze_fn: callable(image, question) -> str (vision mock)
        llm_fn:     callable(prompt) -> str (text LLM mock)
    Returns:
        dict with keys: description, answer, task
    """
    description = describe_screen(image, analyze_fn=analyze_fn)
    lines = [
        'You are a screen-reading assistant.',
        'Here is what is visible on screen:',
        '',
        description,
        '',
        f'Task: {task}',
        '',
        'Answer based only on what is visible on screen.',
    ]
    context_prompt = '\n'.join(lines)
    if llm_fn is not None:
        answer = llm_fn(context_prompt)
    else:
        import ollama
        resp = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': context_prompt}],
        )
        answer = resp['message']['content']
    return {'description': description, 'answer': answer, 'task': task}


class ScreenAgent:
    """Stateful screen-understanding assistant.

    Captures screenshots, analyzes them with a vision LLM, and reasons about
    tasks using a text LLM. All three capabilities are injectable for testing.

    Example::

        from PIL import Image
        agent = ScreenAgent(
            screenshot_fn=lambda r: Image.new("RGB", (100, 100)),
            analyze_fn=lambda img, q: "Mock description",
            llm_fn=lambda p: "Mock answer",
        )
        img = agent.capture()
        desc = agent.describe()
        result = agent.run("What is the title of this window?")
    """

    def __init__(self, screenshot_fn=None, analyze_fn=None, llm_fn=None):
        self._screenshot_fn = screenshot_fn
        self._analyze_fn = analyze_fn
        self._llm_fn = llm_fn
        self._last_image = None
        self._history = []

    def capture(self, region=None):
        """Capture a screenshot and store it as the current image."""
        img = capture_screenshot(region=region, screenshot_fn=self._screenshot_fn)
        self._last_image = img
        self._history.append({'action': 'capture', 'region': region})
        return img

    def describe(self, image=None):
        """Describe what is visible on screen."""
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = describe_screen(img, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'describe', 'result': result})
        return result

    def read_text(self, image=None):
        """Extract text visible on screen."""
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = read_screen_text(img, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'read_text', 'result': result})
        return result

    def ask(self, question, image=None):
        """Answer a question about what is visible on screen."""
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = answer_about_screen(img, question, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'ask', 'question': question, 'result': result})
        return result

    def find(self, element_type, image=None):
        """Find UI elements of a given type on screen."""
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = find_elements(img, element_type, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'find', 'element_type': element_type, 'result': result})
        return result

    def run(self, task, image=None):
        """Run a task against the current screenshot using vision + text reasoning."""
        img = image if image is not None else self._last_image
        if img is None:
            img = self.capture()
        result = run_screen_task(img, task, analyze_fn=self._analyze_fn, llm_fn=self._llm_fn)
        self._history.append({'action': 'run', 'task': task, 'result': result['answer']})
        return result

    def history(self):
        """Return a copy of the action history."""
        return list(self._history)

    def clear_history(self):
        """Clear the action history."""
        self._history.clear()
