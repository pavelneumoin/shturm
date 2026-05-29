"""VK Mini App bridge — minimal best-effort wrapper.

When the build runs inside a VK Mini App webview, `platform.window.vkBridge`
is exposed by the VK Bridge JS SDK (loaded via index.html in the VK template).
We optionally call its methods through pyodide's `platform.window` proxy.

If anything is unavailable (running on desktop, or VK Bridge not initialised
yet), every call is a no-op. The game never depends on success."""
import asyncio
import sys


def _is_wasm():
    return sys.platform == "emscripten"


def _bridge():
    try:
        import platform as _p
        return _p.window.vkBridge
    except Exception:
        return None


async def init():
    """Send VKWebAppInit so VK considers the app loaded."""
    if not _is_wasm():
        return False
    b = _bridge()
    if b is None:
        return False
    try:
        await b.send("VKWebAppInit", {})
        return True
    except Exception:
        return False


async def share_score(score, difficulty="normal"):
    """Open the VK share dialog with the user's score.

    Best-effort: never raises, returns True on success."""
    if not _is_wasm():
        return False
    b = _bridge()
    if b is None:
        return False
    try:
        await b.send("VKWebAppShare", {
            "link": f"https://vk.com/app",  # filled in by the VK Mini App config
        })
        return True
    except Exception:
        return False


def call_sync(name, params=None):
    """Fire-and-forget call — returns immediately, errors swallowed."""
    if not _is_wasm():
        return
    b = _bridge()
    if b is None:
        return
    try:
        b.send(name, params or {})
    except Exception:
        pass
