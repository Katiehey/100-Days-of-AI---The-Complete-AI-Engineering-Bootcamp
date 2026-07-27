#!/usr/bin/env python3
"""gen_day076.py — generate Day 076: Multimodal Agents."""
from pathlib import Path
import json

ROOT    = Path(__file__).parent.parent
DAY     = "076"
SECTION = "05_vision_multimodal"
OUT     = ROOT / SECTION / f"day_{DAY}"

(OUT / "exercises").mkdir(parents=True, exist_ok=True)
(OUT / "lessons").mkdir(parents=True, exist_ok=True)
(OUT / "project" / "solution").mkdir(parents=True, exist_ok=True)

# ── deliverable: screen_agent.py ──────────────────────────────────────────────
_SCREEN_AGENT_SRC = '''\
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
    context_prompt = '\\n'.join(lines)
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
'''

# ── notebook helpers ──────────────────────────────────────────────────────────
def nb(cells):
    return {
        "nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3",
                                    "language": "python",
                                    "name": "python3"}},
        "cells": cells,
    }

def md(src):
    return {"cell_type": "markdown", "metadata": {}, "source": src}

def code(src):
    return {"cell_type": "code", "metadata": {}, "source": src,
            "outputs": [], "execution_count": None}

def save(path, notebook):
    Path(path).write_text(json.dumps(notebook, indent=1))

# ── YAML lessons ──────────────────────────────────────────────────────────────
_LESSON_01 = """\
day: "076"
lesson: 1
title: "Multimodal Agents — Perception and Reasoning"
slides:
  - type: title
    heading: "Multimodal Agents"
    subheading: "Vision + text reasoning in a single agent loop"
    narration: >
      A multimodal agent combines a vision model to perceive images with a
      language model to reason about what it perceives. Day 76 builds a
      screenshot-understanding assistant that can describe screens, extract
      text, find UI elements, and answer questions about what is visible
      using a two-LLM pipeline.

  - type: concept
    label: "Agent types"
    heading: "Three Kinds of AI Agents"
    body: >
      Agents differ by how they perceive the world and what actions they can take.
    bullets:
      - "Text agents: input is text, output is text (Days 3-20)"
      - "Tool-using agents: input is text, can call Python functions (Day 17)"
      - "Multimodal agents: input is text plus images, reason across both"
      - "Screen agents: multimodal agent specialised for computer interfaces"
    narration: >
      The progression is natural. Once you can process text, you add tools
      so the agent can act. Once you add vision, the agent can perceive the
      visual world, not just the text world. Screen agents are the practical
      version: they look at a screenshot and help the user understand or
      interact with what is on screen.

  - type: concept
    label: "Two-LLM pipeline"
    heading: "The Two-LLM Pipeline"
    body: >
      Screen understanding uses two models in sequence.
    bullets:
      - "Stage 1 (vision LLM): screenshot -> natural-language description"
      - "Stage 2 (text LLM): description + task -> answer"
      - "Vision LLM: llava via Ollama (multimodal, introduced Day 67)"
      - "Text LLM: llama3.2 via Ollama (reasoning, introduced Day 3)"
      - "Separation of concerns: each model does what it is trained for"
    narration: >
      A vision-only LLM is good at translating images into words but may not
      be the best at complex reasoning. A text-only LLM cannot see images
      but excels at reasoning. By chaining them, the vision LLM converts the
      screenshot to text, and the text LLM reasons about the task using that
      text description. This two-step pipeline is modular and easy to test.

  - type: concept
    label: "Injection pattern"
    heading: "Three Injection Points for Testing"
    body: >
      Three injection points make ScreenAgent fully testable without hardware.
    bullets:
      - "screenshot_fn=None: replaces PIL.ImageGrab.grab (needs display)"
      - "analyze_fn=None: replaces llava call (needs GPU or Ollama)"
      - "llm_fn=None: replaces llama3.2 call (needs Ollama)"
      - "All three None: real models run in production"
      - "All three mocked: gate runs headlessly with no models or display"
    narration: >
      A real screen agent needs a display for screenshots and a running vision
      model. Neither is available in headless test environments. By injecting
      all three capabilities as optional callables, every function and the
      ScreenAgent class can be tested with deterministic mocks. The fn=None
      injection pattern is the same one used in Days 67 through 75.

  - type: exercise
    heading: "Exercise 1: capture_screenshot"
    prompt: >
      Implement capture_screenshot(region=None, screenshot_fn=None) -> Image.
      If screenshot_fn is not None: return screenshot_fn(region).
      Otherwise: from PIL import ImageGrab; return ImageGrab.grab(bbox=region).
    hint: >
      if screenshot_fn is not None: return screenshot_fn(region).
      from PIL import ImageGrab; return ImageGrab.grab(bbox=region).
    narration: >
      capture_screenshot is the perception entry point. The screenshot_fn
      injection lets the gate test the rest of the pipeline without a
      real display.

  - type: summary
    heading: "Lesson 1 Summary"
    bullets:
      - "Multimodal agents combine vision perception and text reasoning"
      - "Screen agents specialise in computer interfaces and screenshots"
      - "Two-LLM pipeline: llava describes the screen, llama3.2 reasons about tasks"
      - "Three injection points: screenshot_fn, analyze_fn, llm_fn"
      - "All three mock out hardware and model dependencies for testing"
    narration: >
      Lesson 2 implements capture_screenshot and introduces the PIL.ImageGrab API.
"""

_LESSON_02 = """\
day: "076"
lesson: 2
title: "Screenshot Capture with PIL.ImageGrab"
slides:
  - type: title
    heading: "Screenshot Capture"
    subheading: "PIL.ImageGrab — turn the screen into a PIL Image"
    narration: >
      Before any analysis can happen, the agent needs to see the screen.
      PIL.ImageGrab.grab converts the visible pixels of the screen or a
      region into a PIL Image. Once captured, the image enters the same
      processing pipeline as any other PIL Image from Day 66.

  - type: code
    label: "capture_screenshot"
    heading: "capture_screenshot Implementation"
    code: |
      from PIL import Image

      def capture_screenshot(region=None, screenshot_fn=None):
          if screenshot_fn is not None:
              return screenshot_fn(region)
          from PIL import ImageGrab
          return ImageGrab.grab(bbox=region)

      # Full screen:
      # img = capture_screenshot()
      # Top-left quadrant of a 1920x1080 display:
      # img = capture_screenshot(region=(0, 0, 960, 540))
    narration: >
      PIL.ImageGrab.grab captures the screen as a PIL Image in RGB mode.
      The bbox parameter is a four-tuple: left, top, right, bottom in screen
      pixels. If bbox is None, the entire screen is captured. The import of
      ImageGrab is inside the else branch so the module loads without a
      display in test environments.

  - type: concept
    label: "PIL.ImageGrab"
    heading: "PIL.ImageGrab API"
    body: >
      ImageGrab.grab returns a PIL Image you can process with all Day 66 tools.
    bullets:
      - "PIL.ImageGrab.grab(bbox=None) -> Image: full screen or region"
      - "bbox=(left, top, right, bottom): pixel coordinates, top-left origin"
      - "Returns RGB mode Image (no alpha channel)"
      - "Requires display: fails headlessly without screenshot_fn mock"
      - "macOS: may need Screen Recording permission in System Preferences"
      - "Result is a standard PIL Image: resize, crop, save, convert all work"
    narration: >
      On macOS you may see a permission prompt the first time you call
      ImageGrab.grab. On Linux it requires Xlib. In all testing and gate
      contexts, the screenshot_fn mock replaces this call. The returned PIL
      Image can be processed with any tool from Day 66.

  - type: concept
    label: "Region capture"
    heading: "Region Capture and Coordinates"
    body: >
      Region captures focus the vision model on the relevant part of the screen.
    bullets:
      - "Full capture: capture_screenshot() or grab(bbox=None)"
      - "Region: capture_screenshot(region=(x1, y1, x2, y2))"
      - "Capture size is (right - left) by (bottom - top) pixels"
      - "Multi-monitor: coordinates extend past primary display width"
      - "Smaller region means faster encoding and faster vision model call"
    narration: >
      Capturing the full screen is simple but creates a large image that is
      slower to process. Capturing only the relevant region reduces the image
      size and focuses the vision model on the right content. On multi-monitor
      setups, coordinates can extend to the right or left of the primary
      display.

  - type: exercise
    heading: "Exercise 2: analyze_screenshot, describe_screen, read_screen_text"
    prompt: >
      Implement: (1) analyze_screenshot(image, question, analyze_fn=None) -> str:
      if analyze_fn: return analyze_fn(image, question); else convert image to
      base64 and call ollama llava. (2) describe_screen(image, analyze_fn=None)
      -> str: call analyze_screenshot with "Describe what you see on this screen
      in detail." (3) read_screen_text(image, analyze_fn=None) -> str: call
      analyze_screenshot with "Extract all visible text from this image exactly
      as it appears."
    hint: >
      analyze_screenshot: if analyze_fn: return analyze_fn(image, question).
      import io, base64, ollama; buf=BytesIO(); image.save(buf, 'PNG');
      img_b64=base64.b64encode(buf.getvalue()).decode();
      resp=ollama.chat(model='llava', messages=[{role/content/images}]);
      return resp['message']['content'].
      describe_screen and read_screen_text delegate to analyze_screenshot with
      a fixed prompt string.
    narration: >
      analyze_screenshot is the core vision tool. describe_screen and
      read_screen_text are convenience wrappers with purpose-built prompts.

  - type: summary
    heading: "Lesson 2 Summary"
    bullets:
      - "PIL.ImageGrab.grab(bbox=None) -> Image: full or region screenshot"
      - "bbox=(left, top, right, bottom) in screen pixel coordinates"
      - "Import inside else branch: avoids display requirement on module load"
      - "analyze_screenshot converts PIL Image to base64, calls llava"
      - "describe_screen and read_screen_text are fixed-prompt wrappers"
    narration: >
      Lesson 3 adds find_elements and answer_about_screen, completing the
      vision tool layer.
"""

_LESSON_03 = """\
day: "076"
lesson: 3
title: "Vision Analysis Tools"
slides:
  - type: title
    heading: "Vision Tools"
    subheading: "describe, read text, find elements, answer questions"
    narration: >
      The vision tools are the agent's perception layer. Each tool wraps
      analyze_screenshot with a purpose-built prompt. Having separate named
      functions makes the agent's intent clear and makes each tool
      independently testable with the same analyze_fn mock.

  - type: code
    label: "analyze_screenshot"
    heading: "analyze_screenshot — Core Vision Function"
    code: |
      import io
      import base64

      def analyze_screenshot(image, question, analyze_fn=None):
          if analyze_fn is not None:
              return analyze_fn(image, question)
          import ollama
          buf = io.BytesIO()
          image.save(buf, format='PNG')
          img_b64 = base64.b64encode(buf.getvalue()).decode()
          resp = ollama.chat(
              model='llava',
              messages=[{
                  'role': 'user',
                  'content': question,
                  'images': [img_b64],
              }],
          )
          return resp['message']['content']
    narration: >
      analyze_screenshot is the single function that all vision tools delegate
      to. It converts the PIL Image to a PNG in a BytesIO buffer, base64-
      encodes it, and passes it to llava along with the question. The base64
      conversion pattern is the same one used in Day 67's image_to_base64,
      here inlined so screen_agent.py is self-contained.

  - type: code
    label: "vision tools"
    heading: "Four Vision Tools"
    code: |
      def describe_screen(image, analyze_fn=None):
          return analyze_screenshot(
              image,
              'Describe what you see on this screen in detail.',
              analyze_fn=analyze_fn,
          )

      def read_screen_text(image, analyze_fn=None):
          return analyze_screenshot(
              image,
              'Extract all visible text from this image exactly as it appears.',
              analyze_fn=analyze_fn,
          )

      def find_elements(image, element_type, analyze_fn=None):
          question = (
              f'List all {element_type} elements visible in this screenshot. '
              'Be specific about their labels, text, or content.'
          )
          return analyze_screenshot(image, question, analyze_fn=analyze_fn)

      def answer_about_screen(image, question, analyze_fn=None):
          return analyze_screenshot(image, question, analyze_fn=analyze_fn)
    narration: >
      Each tool has a clear name and purpose. describe_screen gives a full
      description of the screen content. read_screen_text extracts all visible
      text verbatim, using the exactly-as-appears instruction to prevent the
      model from paraphrasing. find_elements builds a question that names
      the element type being searched: button, menu, input field, and so on.
      answer_about_screen passes the question through directly for ad-hoc
      queries.

  - type: concept
    label: "Question-driven dispatch"
    heading: "Question-Driven Tool Design"
    body: >
      All four tools share one underlying function. The question string directs
      what the vision model focuses on.
    bullets:
      - "describe: open question, full scene description"
      - "read_text: extraction instruction, verbatim output"
      - "find_elements: type-specific query, lists matching UI components"
      - "answer_about_screen: caller-supplied question for ad-hoc queries"
      - "Same analyze_fn mock tests all four tools with a single lambda"
    narration: >
      The prompt is the tool. By choosing the right question string, you direct
      the vision model to describe, extract, or enumerate. The mock function
      that returns a fixed string for any question tests all four tools with
      the same lambda. In production, the question text shapes the quality of
      the answer significantly.

  - type: exercise
    heading: "Exercise 3: find_elements and answer_about_screen"
    prompt: >
      Implement: (1) find_elements(image, element_type, analyze_fn=None) -> str:
      build question f"List all {element_type} elements visible in this screenshot.
      Be specific about their labels, text, or content." then call
      analyze_screenshot(image, question, analyze_fn=analyze_fn).
      (2) answer_about_screen(image, question, analyze_fn=None) -> str:
      return analyze_screenshot(image, question, analyze_fn=analyze_fn).
    hint: >
      find_elements: question = f"List all {element_type} elements visible in
      this screenshot. Be specific about their labels, text, or content."
      return analyze_screenshot(image, question, analyze_fn=analyze_fn).
      answer_about_screen: one line, passes question straight through.
    narration: >
      find_elements is the most useful tool for UI understanding: ask for all
      buttons, links, input fields, or any other element type by name.

  - type: summary
    heading: "Lesson 3 Summary"
    bullets:
      - "analyze_screenshot: PIL Image + question -> llava -> str"
      - "All vision tools delegate to analyze_screenshot with a fixed prompt"
      - "describe_screen: open question, full scene description"
      - "read_screen_text: verbatim text extraction"
      - "find_elements: element-type query, lists matching UI components"
      - "answer_about_screen: pass-through for ad-hoc questions"
    narration: >
      Lesson 4 adds the text reasoning layer: run_screen_task chains the visual
      description with llama3.2 to answer higher-level tasks.
"""

_LESSON_04 = """\
day: "076"
lesson: 4
title: "Two-LLM Reasoning with run_screen_task"
slides:
  - type: title
    heading: "Two-LLM Reasoning"
    subheading: "Vision description + text reasoning = run_screen_task"
    narration: >
      Vision tools answer direct perceptual questions: what is on screen,
      what text is there. run_screen_task goes further: it captures the
      visual description, injects it into a text prompt, and uses a second
      language model to reason about a task in the context of what is visible.

  - type: code
    label: "run_screen_task"
    heading: "run_screen_task Implementation"
    code: |
      def run_screen_task(image, task, analyze_fn=None, llm_fn=None):
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
    narration: >
      run_screen_task has two injection points: analyze_fn for the vision step
      and llm_fn for the reasoning step. The function returns a dict with three
      keys: description (raw vision output), answer (reasoning output), and
      task (the original task string). Building the prompt as a list of lines
      and joining with newline avoids escape sequences in the string literals.

  - type: concept
    label: "Why two models"
    heading: "Why Use Two Models?"
    body: >
      Specialisation beats a single model trying to do both vision and reasoning.
    bullets:
      - "Vision LLMs (llava): trained on image-text pairs, strong at describing"
      - "Text LLMs (llama3.2): trained on reasoning corpora, strong at inference"
      - "Each model does what it is best at"
      - "Swap either model without rewriting the other"
      - "Same retrieve-then-generate pattern as RAG from Day 13"
    narration: >
      Routing different subtasks to different specialised models is a general
      pattern. In RAG from Day 13, retrieval and generation are separate steps.
      Here, perception (vision LLM) and reasoning (text LLM) are separate.
      The output of the first step is a text description, a natural bridge
      between the two models.

  - type: concept
    label: "Context prompt"
    heading: "Context Prompt Design"
    body: >
      How you structure the visual context in the text prompt affects answer quality.
    bullets:
      - "Lead with a role statement to calibrate the model"
      - "Label the screen content block so the model knows where visual info ends"
      - "State the task explicitly after the context"
      - "Constrain to visible information to reduce hallucination"
      - "Return dict includes description for logging and debugging"
    narration: >
      The prompt structure matters. Starting with a role statement calibrates
      the model. Labelling the screen content block helps the model know where
      the visual information ends and the task begins. Telling the model to
      answer based only on what is visible on screen discourages hallucination
      about content not in the description.

  - type: exercise
    heading: "Exercise 4: run_screen_task"
    prompt: >
      Implement run_screen_task(image, task, analyze_fn=None, llm_fn=None) -> dict.
      Call describe_screen(image, analyze_fn=analyze_fn) to get description.
      Build a context_prompt joining: role statement, screen content header,
      empty line, description, empty line, "Task: {task}", empty line,
      constraint. If llm_fn: answer = llm_fn(context_prompt); else call
      ollama.chat llama3.2. Return {"description": description, "answer":
      answer, "task": task}.
    hint: >
      description = describe_screen(image, analyze_fn=analyze_fn).
      lines = ['You are a screen-reading assistant.', 'Here is what is
      visible on screen:', '', description, '', f'Task: {task}', '',
      'Answer based only on what is visible on screen.'].
      context_prompt = '\n'.join(lines).
      if llm_fn: answer = llm_fn(context_prompt); else ollama.chat llama3.2.
      return {'description': description, 'answer': answer, 'task': task}.
    narration: >
      run_screen_task is the highest-level function before the class wrapper.
      It combines vision and reasoning into a single reusable pipeline.

  - type: summary
    heading: "Lesson 4 Summary"
    bullets:
      - "run_screen_task: describe_screen + text LLM -> {description, answer, task}"
      - "describe_screen uses analyze_fn; text reasoning uses llm_fn"
      - "Two injection points: analyze_fn (vision) and llm_fn (text)"
      - "Build prompt as list of lines joined with newline (no escape sequences)"
      - "Constrain to visible content to reduce hallucination"
    narration: >
      Lesson 5 wraps everything into the ScreenAgent class with history tracking.
"""

_LESSON_05 = """\
day: "076"
lesson: 5
title: "ScreenAgent — Stateful Screen-Understanding Assistant"
slides:
  - type: title
    heading: "ScreenAgent"
    subheading: "Stateful assistant that captures, analyzes, and reasons"
    narration: >
      ScreenAgent wraps all the module-level functions into a stateful class.
      It stores the last captured image and an action history, so you can
      capture once and call multiple analysis methods without repeating the
      screenshot. This is the Section 5 pattern: bind injections at
      construction, delegate to module-level functions, track state.

  - type: code
    label: "ScreenAgent init and capture"
    heading: "Constructor and capture"
    code: |
      class ScreenAgent:
          def __init__(self, screenshot_fn=None, analyze_fn=None, llm_fn=None):
              self._screenshot_fn = screenshot_fn
              self._analyze_fn = analyze_fn
              self._llm_fn = llm_fn
              self._last_image = None
              self._history = []

          def capture(self, region=None):
              img = capture_screenshot(
                  region=region, screenshot_fn=self._screenshot_fn
              )
              self._last_image = img
              self._history.append({'action': 'capture', 'region': region})
              return img
    narration: >
      The constructor stores all three injections. _last_image is None until
      the first capture. _history accumulates action dicts that record what
      the agent has done in the current session. capture() delegates to the
      module-level function, stores the result, appends a history entry, and
      returns the image.

  - type: code
    label: "ScreenAgent methods"
    heading: "describe, ask, find, run, history"
    code: |
          def describe(self, image=None):
              img = image if image is not None else self._last_image
              if img is None:
                  raise ValueError('No image: call capture() first or pass image.')
              result = describe_screen(img, analyze_fn=self._analyze_fn)
              self._history.append({'action': 'describe', 'result': result})
              return result

          def ask(self, question, image=None):
              img = image if image is not None else self._last_image
              if img is None:
                  raise ValueError('No image: call capture() first or pass image.')
              result = answer_about_screen(img, question, analyze_fn=self._analyze_fn)
              self._history.append({'action': 'ask', 'question': question, 'result': result})
              return result

          def run(self, task, image=None):
              img = image if image is not None else self._last_image
              if img is None:
                  img = self.capture()
              result = run_screen_task(
                  img, task, analyze_fn=self._analyze_fn, llm_fn=self._llm_fn
              )
              self._history.append({'action': 'run', 'task': task, 'result': result['answer']})
              return result

          def history(self):
              return list(self._history)

          def clear_history(self):
              self._history.clear()
    narration: >
      Every analysis method follows the same pattern: use the provided image
      or fall back to _last_image; raise ValueError if neither is available;
      call the module-level function; append to history; return the result.
      run() has an extra fallback: if no image is stored, it calls capture()
      automatically. history() returns a copy of the internal list to prevent
      external mutation.

  - type: concept
    label: "History tracking"
    heading: "History Tracking"
    body: >
      _history records every action the agent takes in the current session.
    bullets:
      - "Each entry is a dict with at least an 'action' key"
      - "capture entry: {action, region}"
      - "describe/read_text/find entries: {action, result}"
      - "ask entry: {action, question, result}"
      - "run entry: {action, task, result} where result is the answer string"
      - "history() returns list(self._history) — a copy, not the live list"
      - "clear_history() uses self._history.clear() — empties in place"
    narration: >
      Returning a copy from history() prevents callers from mutating the
      internal list. clear_history() uses list.clear() which empties the
      existing list object rather than replacing it with a new one. Both
      are small but important details for a class that maintains mutable state.

  - type: exercise
    heading: "Exercise 5: ScreenAgent"
    prompt: >
      Implement ScreenAgent(screenshot_fn=None, analyze_fn=None, llm_fn=None).
      Store all three. _last_image=None, _history=[].
      capture(region=None): delegate to capture_screenshot, store _last_image,
      append {action:'capture', region:region}, return image.
      describe(image=None): image-or-last-image guard (ValueError if None),
      describe_screen, append {action:'describe', result:result}.
      read_text(image=None): same pattern with read_screen_text.
      ask(question, image=None): answer_about_screen, append {action:'ask',
      question:question, result:result}.
      find(element_type, image=None): find_elements, append {action:'find',
      element_type:element_type, result:result}.
      run(task, image=None): if no image call capture(); run_screen_task with
      both analyze_fn and llm_fn; append {action:'run', task:task, result:answer}.
      history() -> list copy. clear_history(): self._history.clear().
    hint: >
      Each method: img = image if image is not None else self._last_image;
      if img is None: raise ValueError or call self.capture();
      result = module_fn(img, ..., analyze_fn=self._analyze_fn);
      self._history.append({...}); return result.
      history(): return list(self._history).
      clear_history(): self._history.clear().
    narration: >
      ScreenAgent is the capstone of Day 76. It is the same pattern as
      ImageProcessor, AudioTranscriber, PodcastGenerator, VideoProcessor,
      and TalkingHeadPipeline: bind injections at construction, delegate
      to module-level functions, track history.

  - type: summary
    heading: "Lesson 5 Summary — Day 76 Complete"
    bullets:
      - "ScreenAgent: 3 injections (screenshot_fn, analyze_fn, llm_fn) at construction"
      - "capture(region): stores _last_image, appends to history"
      - "describe/read_text/ask/find: image-or-last fallback, ValueError if None"
      - "run: auto-captures if no image stored, returns full result dict"
      - "history(): returns list copy; clear_history(): empties in place"
      - "Tomorrow (Day 77): Real-Time Vision with a live camera feed"
    narration: >
      Day 76 complete. The ScreenAgent can capture screenshots, describe them,
      extract text, find UI elements, answer questions, and reason about tasks
      using a two-LLM pipeline. Day 77 adds real-time vision with OpenCV
      and a live camera feed.
"""

for i, content in enumerate([_LESSON_01, _LESSON_02, _LESSON_03,
                               _LESSON_04, _LESSON_05], start=1):
    (OUT / "lessons" / f"day_{DAY}_lesson_0{i}.yaml").write_text(content)

# ── shared mock helpers ───────────────────────────────────────────────────────
_IMG_HELPER = """\
from PIL import Image as _PILImage

def _make_mock_image(width=100, height=100, color=(100, 100, 100)):
    return _PILImage.new('RGB', (width, height), color=color)
"""

_SCREENSHOT_MOCK = "_mock_screenshot_fn = lambda region=None: _make_mock_image()\n"
_ANALYZE_MOCK    = "_mock_analyze_fn    = lambda img, q: 'MOCK:' + q[:16]\n"
_LLM_MOCK        = "_mock_llm_fn        = lambda prompt: 'TASK:' + prompt[:12]\n"

# ── pre-built solutions for later exercises ───────────────────────────────────
_ANALYZE_SOL = """\
import io, base64

def analyze_screenshot(image, question, analyze_fn=None):
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
    return analyze_screenshot(
        image, 'Describe what you see on this screen in detail.',
        analyze_fn=analyze_fn)

def read_screen_text(image, analyze_fn=None):
    return analyze_screenshot(
        image, 'Extract all visible text from this image exactly as it appears.',
        analyze_fn=analyze_fn)

def find_elements(image, element_type, analyze_fn=None):
    question = (f'List all {element_type} elements visible in this screenshot. '
                'Be specific about their labels, text, or content.')
    return analyze_screenshot(image, question, analyze_fn=analyze_fn)

def answer_about_screen(image, question, analyze_fn=None):
    return analyze_screenshot(image, question, analyze_fn=analyze_fn)
"""

_TASK_SOL = """\
def run_screen_task(image, task, analyze_fn=None, llm_fn=None):
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
    context_prompt = '\\n'.join(lines)
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
"""

_CAPTURE_SOL = """\
def capture_screenshot(region=None, screenshot_fn=None):
    if screenshot_fn is not None:
        return screenshot_fn(region)
    from PIL import ImageGrab
    return ImageGrab.grab(bbox=region)
"""

# ── EX1: capture_screenshot ───────────────────────────────────────────────────
_EX1_GIVEN = _IMG_HELPER + _SCREENSHOT_MOCK

_EX1_STUB = """\
def capture_screenshot(region=None, screenshot_fn=None):
    \"\"\"Capture the screen or a region as a PIL Image.

    Args:
        region:        (left, top, right, bottom) or None for full screen
        screenshot_fn: callable(region) -> PIL.Image for testing
    \"\"\"
    raise NotImplementedError
"""

_EX1_SOLUTION = _CAPTURE_SOL

_EX1_CHECKS = r"""
score, total = 0, 4
try:
    from PIL import Image as PILImage

    img = capture_screenshot(screenshot_fn=_mock_screenshot_fn)
    assert isinstance(img, PILImage.Image), f"expected PIL Image, got {type(img)}"
    score += 1; print("✅ returns PIL Image")

    assert img.size == (100, 100), f"size mismatch: {img.size}"
    score += 1; print("✅ size matches mock (100, 100)")

    calls = []
    def _cap(region=None): calls.append(region); return _make_mock_image()
    capture_screenshot(region=(0, 0, 50, 50), screenshot_fn=_cap)
    assert calls[0] == (0, 0, 50, 50), f"region not passed: {calls}"
    score += 1; print("✅ region is passed to screenshot_fn")

    calls.clear()
    capture_screenshot(screenshot_fn=_cap)
    assert calls[0] is None, f"expected None region, got {calls[0]}"
    score += 1; print("✅ None region passed when region not specified")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX1 = nb([
    md("# Day 076 — Exercise 1: capture_screenshot\n\n"
       "**What you'll build:** `capture_screenshot(region=None, screenshot_fn=None) -> Image` — "
       "capture the screen as a PIL Image using PIL.ImageGrab.\n\n"
       "**Why it matters:** The perception entry point of the agent. The screenshot_fn "
       "injection lets the rest of the pipeline run in a headless test environment."),
    code(_EX1_GIVEN),
    md("## Task\n\n"
       "- **Mock path:** `if screenshot_fn is not None: return screenshot_fn(region)`\n"
       "- **Real path:** `from PIL import ImageGrab; return ImageGrab.grab(bbox=region)`\n\n"
       "**Key:** Import ImageGrab inside the else branch — not at module level."),
    md("## Your Implementation"),
    code(_EX1_STUB),
    code(_EX1_SOLUTION),
    md("## Automated checks"),
    code(_EX1_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX1_SOLUTION + "```\n\n"
       "**Why import ImageGrab inside the function?** PIL.ImageGrab requires a display "
       "server. Importing it at module level would fail in headless environments. "
       "Lazy import keeps the module loadable everywhere.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_01.ipynb", EX1)

# ── EX2: analyze_screenshot + describe_screen + read_screen_text ──────────────
_EX2_GIVEN = _IMG_HELPER + _ANALYZE_MOCK

_EX2_STUB = """\
import io, base64

def analyze_screenshot(image, question, analyze_fn=None):
    \"\"\"Ask a vision LLM a question about an image.\"\"\"
    raise NotImplementedError

def describe_screen(image, analyze_fn=None):
    \"\"\"Describe what is visible on screen.\"\"\"
    raise NotImplementedError

def read_screen_text(image, analyze_fn=None):
    \"\"\"Extract all visible text from the screen verbatim.\"\"\"
    raise NotImplementedError
"""

_EX2_SOLUTION = """\
import io, base64

def analyze_screenshot(image, question, analyze_fn=None):
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
    return analyze_screenshot(
        image, 'Describe what you see on this screen in detail.',
        analyze_fn=analyze_fn)

def read_screen_text(image, analyze_fn=None):
    return analyze_screenshot(
        image, 'Extract all visible text from this image exactly as it appears.',
        analyze_fn=analyze_fn)
"""

_EX2_CHECKS = r"""
score, total = 0, 5
try:
    from PIL import Image as PILImage
    img = PILImage.new('RGB', (100, 100))

    result = analyze_screenshot(img, 'Test?', analyze_fn=_mock_analyze_fn)
    assert isinstance(result, str), f"expected str, got {type(result)}"
    score += 1; print("✅ analyze_screenshot returns str")

    captured = {}
    def _cap(i, q): captured.update(img=i, q=q); return 'CAPTURED'
    analyze_screenshot(img, 'My question', analyze_fn=_cap)
    assert captured.get('q') == 'My question' and captured.get('img') is img
    score += 1; print("✅ analyze_fn receives (image, question)")

    prompts = []
    describe_screen(img, analyze_fn=lambda i, q: (prompts.append(q), 'D')[1])
    assert prompts and ('Describe' in prompts[0] or 'describe' in prompts[0])
    score += 1; print("✅ describe_screen passes a describe prompt")

    d = describe_screen(img, analyze_fn=_mock_analyze_fn)
    assert isinstance(d, str)
    score += 1; print("✅ describe_screen returns str")

    tprompts = []
    read_screen_text(img, analyze_fn=lambda i, q: (tprompts.append(q), 'T')[1])
    assert tprompts and any(w in tprompts[0].lower() for w in ('text', 'extract'))
    score += 1; print("✅ read_screen_text passes a text-extraction prompt")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX2 = nb([
    md("# Day 076 — Exercise 2: analyze_screenshot, describe_screen, read_screen_text\n\n"
       "**What you'll build:** The core vision function and two purpose-built wrappers.\n\n"
       "**Why it matters:** `analyze_screenshot` is the bridge between a PIL Image and a "
       "vision LLM answer. All other vision tools delegate to it with a fixed prompt."),
    code(_EX2_GIVEN),
    md("## Task\n\n"
       "1. `analyze_screenshot(image, question, analyze_fn=None) -> str`\n"
       "   - Mock: `return analyze_fn(image, question)`\n"
       "   - Real: convert PIL Image to base64 (BytesIO → PNG → b64encode), call "
       "`ollama.chat(model='llava', messages=[{role/content/images}])`, return `resp['message']['content']`\n\n"
       "2. `describe_screen(image, analyze_fn=None) -> str`\n"
       "   - Delegate to `analyze_screenshot` with prompt: "
       "`'Describe what you see on this screen in detail.'`\n\n"
       "3. `read_screen_text(image, analyze_fn=None) -> str`\n"
       "   - Delegate with: `'Extract all visible text from this image exactly as it appears.'`"),
    md("## Your Implementation"),
    code(_EX2_STUB),
    code(_EX2_SOLUTION),
    md("## Automated checks"),
    code(_EX2_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX2_SOLUTION + "```\n\n"
       "**Why inline the base64 conversion?** `screen_agent.py` is a standalone module. "
       "Inlining avoids importing from Day 67's path and keeps the module self-contained. "
       "The logic is identical to Day 67's `image_to_base64`.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_02.ipynb", EX2)

# ── EX3: find_elements + answer_about_screen ──────────────────────────────────
_EX3_GIVEN = _IMG_HELPER + _ANALYZE_MOCK + _ANALYZE_SOL

_EX3_STUB = """\
def find_elements(image, element_type, analyze_fn=None):
    \"\"\"Find UI elements of a given type on screen.\"\"\"
    raise NotImplementedError

def answer_about_screen(image, question, analyze_fn=None):
    \"\"\"Answer an ad-hoc question about what is visible on screen.\"\"\"
    raise NotImplementedError
"""

_EX3_SOLUTION = """\
def find_elements(image, element_type, analyze_fn=None):
    question = (
        f'List all {element_type} elements visible in this screenshot. '
        'Be specific about their labels, text, or content.'
    )
    return analyze_screenshot(image, question, analyze_fn=analyze_fn)

def answer_about_screen(image, question, analyze_fn=None):
    return analyze_screenshot(image, question, analyze_fn=analyze_fn)
"""

_EX3_CHECKS = r"""
score, total = 0, 4
try:
    from PIL import Image as PILImage
    img = PILImage.new('RGB', (100, 100))

    questions = []
    find_elements(img, 'button',
                  analyze_fn=lambda i, q: (questions.append(q), 'FOUND')[1])
    assert questions and 'button' in questions[0], f"element_type not in question: {questions}"
    score += 1; print("✅ find_elements includes element_type in question")

    r = find_elements(img, 'menu', analyze_fn=_mock_analyze_fn)
    assert isinstance(r, str)
    score += 1; print("✅ find_elements returns str")

    qs = []
    answer_about_screen(img, 'How many windows?',
                        analyze_fn=lambda i, q: (qs.append(q), 'A')[1])
    assert qs and qs[0] == 'How many windows?', f"question not passed: {qs}"
    score += 1; print("✅ answer_about_screen passes question to analyze_fn")

    a = answer_about_screen(img, 'Q?', analyze_fn=_mock_analyze_fn)
    assert isinstance(a, str)
    score += 1; print("✅ answer_about_screen returns str")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX3 = nb([
    md("# Day 076 — Exercise 3: find_elements and answer_about_screen\n\n"
       "**What you'll build:** Two more vision tools that complete the perception layer.\n\n"
       "**Why it matters:** `find_elements` is the most useful tool for UI understanding: "
       "ask for all buttons, menus, or input fields by type. `answer_about_screen` is the "
       "pass-through for ad-hoc visual questions."),
    code(_EX3_GIVEN),
    md("## Task\n\n"
       "1. `find_elements(image, element_type, analyze_fn=None) -> str`\n"
       "   - Build: `question = f'List all {element_type} elements visible in this "
       "screenshot. Be specific about their labels, text, or content.'`\n"
       "   - Return `analyze_screenshot(image, question, analyze_fn=analyze_fn)`\n\n"
       "2. `answer_about_screen(image, question, analyze_fn=None) -> str`\n"
       "   - One line: pass `question` straight through to `analyze_screenshot`"),
    md("## Your Implementation"),
    code(_EX3_STUB),
    code(_EX3_SOLUTION),
    md("## Automated checks"),
    code(_EX3_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX3_SOLUTION + "```\n\n"
       "**Why is element_type in the question?** The vision model has no other way to "
       "know what you are looking for. Embedding it in the question text is the "
       "zero-shot prompt engineering pattern.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_03.ipynb", EX3)

# ── EX4: run_screen_task ──────────────────────────────────────────────────────
_EX4_GIVEN = (
    _IMG_HELPER + _ANALYZE_MOCK + _LLM_MOCK + _ANALYZE_SOL
)

_EX4_STUB = """\
def run_screen_task(image, task, analyze_fn=None, llm_fn=None):
    \"\"\"Analyze screenshot with vision LLM, then reason with text LLM.

    Returns:
        dict with keys: description, answer, task
    \"\"\"
    raise NotImplementedError
"""

_EX4_SOLUTION = _TASK_SOL

_EX4_CHECKS = r"""
score, total = 0, 5
try:
    from PIL import Image as PILImage
    img = PILImage.new('RGB', (100, 100))

    result = run_screen_task(img, 'Find title',
                             analyze_fn=_mock_analyze_fn,
                             llm_fn=_mock_llm_fn)
    assert isinstance(result, dict), f"expected dict, got {type(result)}"
    score += 1; print("✅ returns dict")

    assert all(k in result for k in ('description', 'answer', 'task'))
    score += 1; print("✅ dict has description, answer, task keys")

    assert result['task'] == 'Find title'
    score += 1; print("✅ task is preserved in result")

    called = {}
    def _analyze(i, q): called['q'] = q; return 'SCREEN_DESC'
    r2 = run_screen_task(img, 'My task', analyze_fn=_analyze, llm_fn=lambda p: 'DONE')
    assert r2['description'] == 'SCREEN_DESC'
    score += 1; print("✅ description comes from describe_screen (analyze_fn used)")

    prompts = []
    def _llm(p): prompts.append(p); return 'ANSWER'
    r3 = run_screen_task(img, 'Task', analyze_fn=lambda i, q: 'VIS', llm_fn=_llm)
    assert r3['answer'] == 'ANSWER' and 'VIS' in prompts[0]
    score += 1; print("✅ answer from llm_fn; visual description in prompt")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX4 = nb([
    md("# Day 076 — Exercise 4: run_screen_task\n\n"
       "**What you'll build:** `run_screen_task(image, task, analyze_fn=None, llm_fn=None) -> dict` — "
       "the two-LLM reasoning pipeline.\n\n"
       "**Why it matters:** This is the core of the multimodal agent: vision LLM describes "
       "the screen, text LLM reasons about a task using that description."),
    code(_EX4_GIVEN),
    md("## Task\n\n"
       "1. `description = describe_screen(image, analyze_fn=analyze_fn)`\n"
       "2. Build `context_prompt`: join a list of lines with `'\\n'`:\n"
       "   - `'You are a screen-reading assistant.'`\n"
       "   - `'Here is what is visible on screen:'`\n"
       "   - `''` (blank line)\n"
       "   - `description`\n"
       "   - `''` (blank line)\n"
       "   - `f'Task: {task}'`\n"
       "   - `''` (blank line)\n"
       "   - `'Answer based only on what is visible on screen.'`\n"
       "3. If `llm_fn`: `answer = llm_fn(context_prompt)`; else call `ollama.chat` with `llama3.2`\n"
       "4. Return `{'description': description, 'answer': answer, 'task': task}`"),
    md("## Your Implementation"),
    code(_EX4_STUB),
    code(_EX4_SOLUTION),
    md("## Automated checks"),
    code(_EX4_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX4_SOLUTION + "```\n\n"
       "**Why join a list of lines?** Building the prompt as a list avoids backslash "
       "newline escape sequences inside string literals. Each line is a clear, "
       "readable element.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_04.ipynb", EX4)

# ── EX5: ScreenAgent ──────────────────────────────────────────────────────────
_EX5_GIVEN = (
    _IMG_HELPER
    + _SCREENSHOT_MOCK
    + _ANALYZE_MOCK
    + _LLM_MOCK
    + _CAPTURE_SOL
    + _ANALYZE_SOL
    + _TASK_SOL
)

_EX5_STUB = """\
class ScreenAgent:
    \"\"\"Stateful screen-understanding assistant with history tracking.\"\"\"

    def __init__(self, screenshot_fn=None, analyze_fn=None, llm_fn=None):
        raise NotImplementedError

    def capture(self, region=None):
        raise NotImplementedError

    def describe(self, image=None):
        raise NotImplementedError

    def read_text(self, image=None):
        raise NotImplementedError

    def ask(self, question, image=None):
        raise NotImplementedError

    def find(self, element_type, image=None):
        raise NotImplementedError

    def run(self, task, image=None):
        raise NotImplementedError

    def history(self):
        raise NotImplementedError

    def clear_history(self):
        raise NotImplementedError
"""

_EX5_SOLUTION = """\
class ScreenAgent:
    def __init__(self, screenshot_fn=None, analyze_fn=None, llm_fn=None):
        self._screenshot_fn = screenshot_fn
        self._analyze_fn = analyze_fn
        self._llm_fn = llm_fn
        self._last_image = None
        self._history = []

    def capture(self, region=None):
        img = capture_screenshot(region=region, screenshot_fn=self._screenshot_fn)
        self._last_image = img
        self._history.append({'action': 'capture', 'region': region})
        return img

    def describe(self, image=None):
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = describe_screen(img, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'describe', 'result': result})
        return result

    def read_text(self, image=None):
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = read_screen_text(img, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'read_text', 'result': result})
        return result

    def ask(self, question, image=None):
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = answer_about_screen(img, question, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'ask', 'question': question, 'result': result})
        return result

    def find(self, element_type, image=None):
        img = image if image is not None else self._last_image
        if img is None:
            raise ValueError('No image: call capture() first or pass image.')
        result = find_elements(img, element_type, analyze_fn=self._analyze_fn)
        self._history.append({'action': 'find', 'element_type': element_type, 'result': result})
        return result

    def run(self, task, image=None):
        img = image if image is not None else self._last_image
        if img is None:
            img = self.capture()
        result = run_screen_task(img, task, analyze_fn=self._analyze_fn, llm_fn=self._llm_fn)
        self._history.append({'action': 'run', 'task': task, 'result': result['answer']})
        return result

    def history(self):
        return list(self._history)

    def clear_history(self):
        self._history.clear()
"""

_EX5_CHECKS = r"""
score, total = 0, 6
try:
    from PIL import Image as PILImage

    agent = ScreenAgent(
        screenshot_fn=_mock_screenshot_fn,
        analyze_fn=_mock_analyze_fn,
        llm_fn=_mock_llm_fn,
    )

    img = agent.capture()
    assert isinstance(img, PILImage.Image)
    score += 1; print("✅ capture() returns PIL Image")

    d = agent.describe()
    assert isinstance(d, str)
    score += 1; print("✅ describe() returns str using stored image")

    a = agent.ask('What is this?')
    assert isinstance(a, str)
    score += 1; print("✅ ask() returns str")

    f = agent.find('button')
    assert isinstance(f, str)
    score += 1; print("✅ find() returns str")

    r = agent.run('Identify the app')
    assert isinstance(r, dict) and 'description' in r and 'answer' in r
    score += 1; print("✅ run() returns dict with description and answer")

    hist = agent.history()
    assert isinstance(hist, list) and len(hist) >= 4
    agent.clear_history()
    assert agent.history() == []
    score += 1; print("✅ history() and clear_history() work correctly")

except Exception as e:
    print(f"❌ {e}")

print(f"\n{score}/{total} checks passed")
if score == total:
    print("\U0001f389 Exercise complete!")
"""

EX5 = nb([
    md("# Day 076 — Exercise 5: ScreenAgent\n\n"
       "**What you'll build:** `ScreenAgent` — stateful screen-understanding assistant "
       "that wraps all vision tools with history tracking.\n\n"
       "**Why it matters:** The class binds all three injections at construction so callers "
       "use `agent.describe()` rather than passing mock functions on every call — "
       "the same pattern as ImageProcessor, AudioTranscriber, and TalkingHeadPipeline."),
    code(_EX5_GIVEN),
    md("## Task\n\n"
       "Implement `ScreenAgent(screenshot_fn=None, analyze_fn=None, llm_fn=None)`:\n\n"
       "- `__init__`: store all 3. `_last_image=None`, `_history=[]`\n"
       "- `capture(region=None)`: `capture_screenshot(region, self._screenshot_fn)` → store `_last_image` → append `{action:'capture', region:region}` → return img\n"
       "- `describe/read_text/ask/find`: `img = image if image is not None else self._last_image`; raise ValueError if None; call module fn; append history entry; return result\n"
       "  - `describe`: `{action:'describe', result:result}`\n"
       "  - `ask`: `{action:'ask', question:question, result:result}`\n"
       "  - `find`: `{action:'find', element_type:element_type, result:result}`\n"
       "- `run(task, image=None)`: if no image, call `self.capture()`; `run_screen_task(img, task, analyze_fn=self._analyze_fn, llm_fn=self._llm_fn)`; append `{action:'run', task:task, result:result['answer']}`\n"
       "- `history()`: `return list(self._history)`\n"
       "- `clear_history()`: `self._history.clear()`"),
    md("## Your Implementation"),
    code(_EX5_STUB),
    code(_EX5_SOLUTION),
    md("## Automated checks"),
    code(_EX5_CHECKS),
    md("## Solution\n\n"
       "<details><summary>Reveal</summary>\n\n"
       "```python\n" + _EX5_SOLUTION + "```\n\n"
       "**Why `image if image is not None else self._last_image`** and not `image or self._last_image`? "
       "A real PIL Image is truthy, so both work here — but the `is not None` form "
       "correctly handles the case where someone passes a 0×0 image (falsy) as an "
       "explicit override.\n\n"
       "</details>"),
])
save(OUT / "exercises" / "exercise_05.ipynb", EX5)

# ── PROJECT NOTEBOOK ──────────────────────────────────────────────────────────
PROJECT = nb([
    md(f"# Day {DAY} — Project: Screen-Understanding Assistant\n\n"
       "## Objective\n\n"
       "Build `screen_agent.py` — a multimodal agent that captures screenshots "
       "and answers questions about them using a two-LLM pipeline.\n\n"
       "## Deliverable\n\n"
       "`screen_agent.py` with:\n\n"
       "- `capture_screenshot(region=None, screenshot_fn=None) -> Image`\n"
       "- `analyze_screenshot(image, question, analyze_fn=None) -> str`\n"
       "- `describe_screen(image, analyze_fn=None) -> str`\n"
       "- `read_screen_text(image, analyze_fn=None) -> str`\n"
       "- `find_elements(image, element_type, analyze_fn=None) -> str`\n"
       "- `answer_about_screen(image, question, analyze_fn=None) -> str`\n"
       "- `run_screen_task(image, task, analyze_fn=None, llm_fn=None) -> dict`\n"
       "- `ScreenAgent(screenshot_fn=None, analyze_fn=None, llm_fn=None)` with\n"
       "  `capture`, `describe`, `read_text`, `ask`, `find`, `run`, `history`, `clear_history`\n\n"
       "## Usage\n\n"
       "```python\n"
       "# With real models (Ollama must be running: ollama pull llava && ollama pull llama3.2):\n"
       "agent = ScreenAgent()\n"
       "img = agent.capture()\n"
       "print(agent.describe())\n"
       "print(agent.run('What application is open?'))\n"
       "```"),
    code("# Your implementation here — build ScreenAgent and write screen_agent.py\n"),
])
save(OUT / "project" / "project.ipynb", PROJECT)

# ── SOLUTION NOTEBOOK ─────────────────────────────────────────────────────────
_SOL_CELL1 = (
    f"_SRC = {repr(_SCREEN_AGENT_SRC)}\n"
    "from pathlib import Path\n"
    "Path('screen_agent.py').write_text(_SRC, encoding='utf-8')\n"
    "print('screen_agent.py written.')"
)

_SOL_CELL2 = """\
import io, base64
from pathlib import Path
from PIL import Image as PILImage
from screen_agent import (
    capture_screenshot, analyze_screenshot, describe_screen,
    read_screen_text, find_elements, answer_about_screen,
    run_screen_task, ScreenAgent,
)

_mock_img = PILImage.new('RGB', (100, 100), color=(100, 100, 100))
_mock_screenshot_fn = lambda region=None: _mock_img
_mock_analyze_fn    = lambda img, q: 'SCREEN:' + q[:12]
_mock_llm_fn        = lambda p: 'ANSWER:' + p[:8]

# 1. capture_screenshot
img = capture_screenshot(screenshot_fn=_mock_screenshot_fn)
assert isinstance(img, PILImage.Image)
print("\\u2705 capture_screenshot correct")

# 2. analyze_screenshot
r = analyze_screenshot(_mock_img, 'Q?', analyze_fn=_mock_analyze_fn)
assert isinstance(r, str)
print("\\u2705 analyze_screenshot correct")

# 3. describe_screen
d = describe_screen(_mock_img, analyze_fn=_mock_analyze_fn)
assert isinstance(d, str)
print("\\u2705 describe_screen correct")

# 4. read_screen_text
t = read_screen_text(_mock_img, analyze_fn=_mock_analyze_fn)
assert isinstance(t, str)
print("\\u2705 read_screen_text correct")

# 5. find_elements
qs = []
find_elements(_mock_img, 'button', analyze_fn=lambda i, q: (qs.append(q), 'F')[1])
assert 'button' in qs[0]
print("\\u2705 find_elements correct")

# 6. answer_about_screen
a = answer_about_screen(_mock_img, 'Count?', analyze_fn=_mock_analyze_fn)
assert isinstance(a, str)
print("\\u2705 answer_about_screen correct")

# 7. run_screen_task
res = run_screen_task(_mock_img, 'Find title',
                      analyze_fn=_mock_analyze_fn, llm_fn=_mock_llm_fn)
assert isinstance(res, dict) and all(k in res for k in ('description', 'answer', 'task'))
print("\\u2705 run_screen_task correct")

# 8. ScreenAgent
agent = ScreenAgent(screenshot_fn=_mock_screenshot_fn,
                    analyze_fn=_mock_analyze_fn,
                    llm_fn=_mock_llm_fn)
agent.capture()
agent.describe()
agent.ask('Q?')
agent.find('button')
result = agent.run('Find the title')
assert isinstance(result, dict) and 'answer' in result
hist = agent.history()
assert len(hist) == 5
agent.clear_history()
assert agent.history() == []
print("\\u2705 ScreenAgent correct")
print("\\nMultimodal Agent complete!")
"""

SOLUTION = nb([
    md(f"# Day {DAY} — Solution: Screen-Understanding Agent"),
    code(_SOL_CELL1),
    code(_SOL_CELL2),
])
save(OUT / "project" / "solution" / "solution.ipynb", SOLUTION)
(OUT / "project" / "solution" / "screen_agent.py").write_text(_SCREEN_AGENT_SRC)

print(f"Day {DAY} notebooks written to {OUT}")
print("  lessons/    day_076_lesson_01.yaml – lesson_05.yaml")
print("  exercises/  exercise_01 – exercise_05")
print("  project/    project.ipynb")
print("  project/solution/  solution.ipynb + screen_agent.py")
