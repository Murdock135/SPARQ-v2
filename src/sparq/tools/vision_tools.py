"""
Vision tools — allows the Researcher agent to interpret its own generated plots.

The interpret_plot tool calls a multimodal LLM with the image and returns a
text description of the figure's key message. This closes the feedback loop
between generating a plot and understanding what it shows.

The vision LLM is initialised lazily from settings on first call.
It must be a multimodal model (e.g. gemini-2.0-flash, claude-3-5-sonnet, gpt-4o).
"""

from __future__ import annotations

import base64
from pathlib import Path

from langchain.tools import tool
from langchain_core.messages import HumanMessage


def _get_vision_llm():
    """Lazily load the vision LLM from settings."""
    from sparq.settings import AgenticSystemSettings
    from sparq.utils.get_llm import get_llm

    settings = AgenticSystemSettings()
    vision_cfg = settings.llm_config.vision
    if vision_cfg is None:
        raise ValueError(
            "No 'vision' LLM configured. Add [llm_config.vision] to config.toml "
            "with a multimodal model (e.g. gemini-2.0-flash or gpt-4o)."
        )
    return get_llm(model=vision_cfg.model_name, provider=vision_cfg.provider)


@tool
def interpret_plot(file_path: str) -> str:
    """Interpret a saved plot image and return a description of its key findings.

    Call this after saving a figure to understand what the plot shows before moving on.
    The description will be used by the synthesizer to reference the figure accurately.

    Args:
        file_path: Absolute path to the image file (.png, .jpg, .jpeg, .svg).

    Returns:
        A text description of the figure's main message and key visual patterns.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: file not found at {file_path}"

    suffix = path.suffix.lower()
    mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml"}
    mime = mime_map.get(suffix, "image/png")

    b64 = base64.b64encode(path.read_bytes()).decode()

    llm = _get_vision_llm()
    message = HumanMessage(content=[
        {
            "type": "text",
            "text": (
                "You are a scientific figure analyst. Describe the key findings shown in this figure "
                "in 2-4 sentences. Be specific: mention axis labels, trends, notable values, and "
                "what the visual pattern implies for the research question. Do not describe the "
                "visual style — focus only on the scientific content."
            ),
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        },
    ])

    response = llm.invoke([message])
    return response.content
