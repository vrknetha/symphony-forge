"""Fake only the Forge project endpoint, leaving other HTTP clients alone."""

import io
import json
from pathlib import Path
from urllib import error, request

original = request.urlopen


def open_pypi(url, *args, **kwargs):
    if url != "https://pypi.org/pypi/symphony-forge/json":
        return original(url, *args, **kwargs)
    folder = Path(__file__).resolve().parent
    with (folder / "pypi-calls.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(kwargs.get("timeout")) + "\n")
    path = folder / "pypi-responses.json"
    answers = json.loads(path.read_text("utf-8")) if path.exists() else []
    answer = answers.pop(0) if len(answers) > 1 else next(iter(answers), 404)
    if path.exists():
        path.write_text(json.dumps(answers), encoding="utf-8")
    if isinstance(answer, int):
        raise error.HTTPError(url, answer, "Unavailable", {}, None)
    if answer == "timeout":
        raise TimeoutError("PyPI timed out")
    return io.BytesIO(json.dumps({"info": {"version": answer}, "futureField": True}).encode())


request.urlopen = open_pypi
