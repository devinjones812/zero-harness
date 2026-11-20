"""Images in user messages: a path to an image file in the text attaches it. HEIC files, and images over MAX_EDGE, become
a JPEG through macOS sips."""

import base64
import mimetypes
import re
import subprocess
import tempfile
from pathlib import Path

from zero_harness.ui.notes import note

EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".heif"}
CONVERT = {".heic", ".heif"}
MAX_EDGE = 2000

# A path dragged into a terminal escapes spaces as "\ ". macOS screenshot names contain U+202F,
# so match any character except a plain space, tab, newline, or backslash.
IMAGE_PATH = re.compile(r"(?:[^ \t\n\\]|\\ )+\.(?:png|jpe?g|gif|webp|heic|heif)", re.IGNORECASE)


def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in EXTENSIONS


def content(path: str) -> dict:
    """An input_image item with the file inlined as a data URL.

    Images within MAX_EDGE are sent unchanged. Larger ones and HEIC become a JPEG at most MAX_EDGE px wide or tall.
    """
    file = Path(path).expanduser()
    side = longest_side(file)
    if side > MAX_EDGE or file.suffix.lower() in CONVERT:
        mime, data = "image/jpeg", to_jpeg(file, side)
    else:
        mime, data = mimetypes.guess_type(file)[0], file.read_bytes()
    return {"type": "input_image", "image_url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}


def longest_side(file: Path) -> int:
    output = sips("-g", "pixelWidth", "-g", "pixelHeight", str(file))
    sides = re.findall(r"pixel(?:Width|Height): (\d+)", output)
    if len(sides) != 2:
        raise ValueError(f"could not read {file.name}. Export it as PNG or JPEG and try again.")
    return max(int(side) for side in sides)


def to_jpeg(file: Path, side: int) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "image.jpg"
        resize = ["-Z", str(MAX_EDGE)] if side > MAX_EDGE else []
        sips(*resize, "-s", "format", "jpeg", str(file), "--out", str(out))
        return out.read_bytes()


def sips(*args: str) -> str:
    """Run macOS `sips`. Raises ValueError with a readable reason on any failure."""
    try:
        return subprocess.run(["sips", *args], capture_output=True, text=True, check=True, timeout=30).stdout
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ValueError(f"could not process {Path(args[-1]).name}. Export it as PNG or JPEG and try again.") from error


def user_message(text: str) -> dict:
    """A user message. Image file paths in the text are attached as images; failures become a note."""
    paths = [match.replace("\\ ", " ") for match in IMAGE_PATH.findall(text)]
    attached = []
    for path in paths:
        if not Path(path).expanduser().is_file():
            continue
        try:
            attached.append(content(path))
        except (ValueError, OSError) as error:
            note(f"[image] {error}")
            text += f"\n(image not attached: {error})"
    if not attached:
        return {"role": "user", "content": text}
    return {"role": "user", "content": [{"type": "input_text", "text": text}, *attached]}
