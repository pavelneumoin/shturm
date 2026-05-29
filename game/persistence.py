"""Cross-platform key/value persistence.

Inside pygbag/WASM we tunnel through `platform.window.localStorage` so the score
survives between page loads. On the desktop we fall back to a JSON file next to
the executable. All operations are best-effort — failures are swallowed."""
import json
import os
import sys


_FILE_NAME = "shturm_save.json"


def _is_wasm():
    return sys.platform == "emscripten"


def _file_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(base), _FILE_NAME)


def _ls_get(key):
    try:
        import platform as _p
        val = _p.window.localStorage.getItem(key)
        return val
    except Exception:
        return None


def _ls_set(key, value):
    try:
        import platform as _p
        _p.window.localStorage.setItem(key, value)
        return True
    except Exception:
        return False


def _read_file():
    try:
        with open(_file_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_file(data):
    try:
        with open(_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False


def get_int(key, default=0):
    if _is_wasm():
        v = _ls_get(key)
        if v is None:
            return default
        try:
            return int(v)
        except (TypeError, ValueError):
            return default
    data = _read_file()
    try:
        return int(data.get(key, default))
    except (TypeError, ValueError):
        return default


def set_int(key, value):
    value = int(value)
    if _is_wasm():
        _ls_set(key, str(value))
        return
    data = _read_file()
    data[key] = value
    _write_file(data)


HI_SCORE_KEY = "shturm_hi_score"
MUTED_KEY = "shturm_muted"
CRT_KEY = "shturm_crt"
DIFFICULTY_KEY = "shturm_difficulty"
HI_TABLE_KEY = "shturm_hi_table"


def get_str(key, default=""):
    """String variant of get_int — used for the hi-score table JSON blob."""
    if _is_wasm():
        v = _ls_get(key)
        return v if v is not None else default
    data = _read_file()
    return str(data.get(key, default))


def set_str(key, value):
    value = str(value)
    if _is_wasm():
        _ls_set(key, value)
        return
    data = _read_file()
    data[key] = value
    _write_file(data)


def get_hi_table():
    """Returns a list of dicts: [{'name': 'AAA', 'score': N, 'diff': 'normal'}, ...]
    Sorted desc by score. Max 5 entries."""
    raw = get_str(HI_TABLE_KEY, "")
    if not raw:
        return []
    try:
        table = json.loads(raw)
        if not isinstance(table, list):
            return []
        # sanitise
        out = []
        for row in table[:5]:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name", "AAA"))[:3].upper()
            try:
                score = int(row.get("score", 0))
            except (TypeError, ValueError):
                score = 0
            diff = str(row.get("diff", "normal"))
            out.append({"name": name, "score": score, "diff": diff})
        out.sort(key=lambda r: r["score"], reverse=True)
        return out[:5]
    except Exception:
        return []


def commit_hi_table(table):
    """Persist a (already sorted, length-5) table back."""
    try:
        set_str(HI_TABLE_KEY, json.dumps(table))
    except Exception:
        pass


def qualifies_for_table(table, score):
    """Returns True if `score` would make it into top-5."""
    if score <= 0:
        return False
    if len(table) < 5:
        return True
    return score > table[-1]["score"]
