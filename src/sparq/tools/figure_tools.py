from pathlib import Path

from langchain.tools import tool

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}


@tool
def get_next_figure_number(directory: str) -> str:
    """Return the next sequential figure label based on existing images in the directory.

    Call this before saving any plot. Use the returned label (e.g. "Figure 3") as the
    plot title prefix so the synthesizer can reference figures unambiguously.

    Args:
        directory: Path to the output directory where figures are being saved.

    Returns:
        A string like "Figure 1", "Figure 2", etc.
    """
    path = Path(directory)
    if not path.exists():
        return "Figure 1"
    count = sum(1 for f in path.iterdir() if f.suffix.lower() in _IMAGE_SUFFIXES)
    return f"Figure {count + 1}"
