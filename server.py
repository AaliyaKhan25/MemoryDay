#!/usr/bin/env python3
"""Our Ofrenda: serves the altar page and talks to a local open-weight model through Ollama.

Everything stays on this computer. The page talks to this server on 127.0.0.1,
and this server talks to Ollama on 127.0.0.1. No cloud API, no account, no key.

Run:
    ollama pull gemma3:4b
    python server.py
Then open http://localhost:8000

Settings (environment variables):
    OLLAMA_MODEL   model to use            (default: gemma3:4b)
    OLLAMA_HOST    where Ollama listens    (default: http://127.0.0.1:11434)
    PORT           port for this page      (default: 8000)

The photo caption feature needs a model that can read images (gemma3:4b and larger can).
"""
import json
import os
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE / "ofrenda.html"
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:4b")
OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
if not OLLAMA.startswith("http"):
    OLLAMA = "http://" + OLLAMA
PORT = int(os.environ.get("PORT", "8000"))
MAX_BODY = 300_000
MAX_IMAGE_BODY = 4_000_000

LANGS = {
    "en": "English",
    "hi": "Hindi in Devanagari script, using simple everyday words",
}

STORY_SYSTEM = """You help a family write a short remembrance of someone they love who has died, for a Dia de los Muertos altar.

Rules:
- Use ONLY the facts the family gives you. Never invent names, places, dates, events, quotes, or feelings that the family did not state.
- If the notes are thin, write less. A short true paragraph is better than a long invented one.
- Write 90 to 150 words in warm, plain language. Use "we" or the third person, whichever fits the notes.
- No poetry cliches, no headings, no lists.
- After the story, add one last line that starts with "To add:" and asks for ONE specific detail that would make the story richer.
- Reply with the story and that last line only."""

ASK_SYSTEM = """You answer questions about a family's loved ones using ONLY the archive below, which the family wrote themselves.

Rules:
- If the archive does not contain the answer, reply exactly: "No one has told this story yet." Then suggest one thing worth recording.
- Never guess or invent details. Say whose card a detail comes from.
- Keep the answer under 120 words, warm and plain."""

CHAPTER_SYSTEM = """You are writing one page of a printed memory book about a person who has died. The family supplied the facts below.

Rules:
- Use ONLY the facts provided. Never invent names, places, dates, ages, quotes, feelings, or events. If the facts are thin, write only 2 or 3 sentences.
- Write in the third person and the past tense, in warm plain language, the way a family member would tell it. Never write as the person who died and never put words in their mouth.
- 60 to 110 words, one paragraph. No heading, no list, no cliches such as "journey", "tapestry" or "legacy".
- Reply with the paragraph only."""

FOREWORD_SYSTEM = """You are writing the short opening note, from the family, for a printed memory book about a person who has died.

Rules:
- Use ONLY the facts supplied: who they were to the family, their years, favorite food, favorite song, what the family wrote about them, and the moments the book covers. Never invent anything else.
- Write in the third person and the past tense, in warm plain language. Never write as the person who died.
- 70 to 110 words, one paragraph. No heading, no list, no cliches such as "journey", "tapestry" or "legacy".
- Reply with the note only."""

DESCRIBE_SYSTEM = """You write a caption for a photograph in a family album.

Rules:
- Write ONE plain sentence of at most 20 words.
- Say only what you can actually see: the setting, the activity, objects, clothing.
- Do not guess who anyone is, their age, their relationship, their feelings, or where or when the photo was taken.
- If the photo is too unclear to describe, say so briefly.
- Reply with the sentence only."""


def clip(value, limit=1500):
    return str(value or "").strip()[:limit]


def lang_line(code):
    return "Write in " + LANGS.get(code, LANGS["en"]) + "."


def ollama_request(path, payload=None, timeout=240):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        OLLAMA + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def chat(system, user, images=None, temperature=0.5):
    message = {"role": "user", "content": user}
    if images:
        message["images"] = images
    result = ollama_request(
        "/api/chat",
        {
            "model": MODEL,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": [{"role": "system", "content": system}, message],
        },
    )
    return (result.get("message", {}).get("content") or "").strip()


def health():
    try:
        tags = ollama_request("/api/tags", timeout=2)
    except Exception:
        return {"ok": True, "ollama": False, "model": MODEL, "model_ready": False}
    names = [m.get("name", "") for m in tags.get("models", [])]
    wanted = MODEL if ":" in MODEL else MODEL + ":latest"
    ready = any(n == wanted or n == MODEL for n in names)
    return {"ok": True, "ollama": True, "model": MODEL, "model_ready": ready}


def story_prompt(body):
    lines = [
        f"Name: {clip(body.get('name'), 60)}",
        f"Who they were to us: {clip(body.get('rel'), 80)}",
        f"Years: {clip(body.get('years'), 40)}",
        f"Favorite food: {clip(body.get('food'), 100)}",
        f"Their song: {clip(body.get('song'), 100)}",
        "",
        "The family's notes:",
        clip(body.get("notes")),
    ]
    return "\n".join(lines)


def archive_prompt(body):
    people = body.get("people")
    if not isinstance(people, list) or not people:
        return None
    blocks = []
    for p in people[:40]:
        if not isinstance(p, dict):
            continue
        blocks.append(
            "\n".join(
                [
                    f"PERSON: {clip(p.get('name'), 60)} ({clip(p.get('rel'), 80)}, {clip(p.get('years'), 40)})",
                    f"Story: {clip(p.get('story'))}",
                    f"Favorite food: {clip(p.get('food'), 100)}",
                    f"Their song: {clip(p.get('song'), 100)}",
                ]
            )
        )
    if not blocks:
        return None
    return "ARCHIVE:\n\n" + "\n\n".join(blocks) + "\n\nQUESTION: " + clip(body.get("question"), 400)


def person_lines(person):
    return [
        f"Person: {clip(person.get('name'), 60)}",
        f"Who they were to us: {clip(person.get('rel'), 80)}",
        f"Years: {clip(person.get('years'), 40)}",
        f"Favorite food: {clip(person.get('food'), 100)}",
        f"Their song: {clip(person.get('song'), 100)}",
    ]


def chapter_prompt(person, moment):
    lines = person_lines(person) + [
        "",
        f"This page is about: {clip(moment.get('title'), 80)}",
        f"When: {clip(moment.get('when'), 40)}",
        f"Where: {clip(moment.get('where'), 80)}",
        f"Caption under the photo: {clip(moment.get('caption'), 120)}",
        "What the family told us:",
        clip(moment.get("notes"), 900),
    ]
    return "\n".join(lines)


def foreword_prompt(person, moments):
    lines = person_lines(person) + [
        "What the family wrote about them:",
        clip(person.get("story"), 800),
        "",
        "Moments in the book:",
    ]
    for m in moments[:30]:
        if isinstance(m, dict):
            lines.append(f"- {clip(m.get('title'), 80)} ({clip(m.get('when'), 40)})")
    return "\n".join(lines)


ROUTES = {"/api/story", "/api/ask", "/api/chapter", "/api/foreword", "/api/describe"}


class Handler(BaseHTTPRequestHandler):
    server_version = "Ofrenda/1.1"

    def log_message(self, fmt, *args):
        print("  " + fmt % args)

    def send_json(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/ofrenda.html"):
            try:
                raw = PAGE.read_bytes()
            except OSError:
                return self.send_json(404, {"error": "ofrenda.html must sit next to server.py."})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif path == "/api/health":
            self.send_json(200, health())
        else:
            self.send_json(404, {"error": "Not found."})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path not in ROUTES:
            return self.send_json(404, {"error": "Not found."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            limit = MAX_IMAGE_BODY if path == "/api/describe" else MAX_BODY
            if length > limit:
                return self.send_json(413, {"error": "That is too much at once."})
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except Exception:
            return self.send_json(400, {"error": "Could not read that request."})

        lang = body.get("lang") if body.get("lang") in LANGS else "en"
        images = None
        temperature = 0.5

        if path == "/api/story":
            if not clip(body.get("name")) or len(clip(body.get("notes"))) < 12:
                return self.send_json(400, {"error": "Add a name and a few lines of notes first."})
            system, user = STORY_SYSTEM, story_prompt(body)

        elif path == "/api/ask":
            if not clip(body.get("question")):
                return self.send_json(400, {"error": "Type a question first."})
            user = archive_prompt(body)
            if user is None:
                return self.send_json(400, {"error": "The archive is empty."})
            system = ASK_SYSTEM

        elif path == "/api/chapter":
            person, moment = body.get("person"), body.get("moment")
            if not isinstance(person, dict) or not isinstance(moment, dict):
                return self.send_json(400, {"error": "Could not read that request."})
            if not (clip(moment.get("title"), 80) or clip(moment.get("notes"), 900) or clip(moment.get("caption"), 120)):
                return self.send_json(400, {"error": "Add what they were doing or a few lines about this photo first."})
            system = CHAPTER_SYSTEM + "\n" + lang_line(lang)
            user = chapter_prompt(person, moment)

        elif path == "/api/foreword":
            person, moments = body.get("person"), body.get("moments")
            if not isinstance(person, dict) or not isinstance(moments, list) or not clip(person.get("name")):
                return self.send_json(400, {"error": "Could not read that request."})
            system = FOREWORD_SYSTEM + "\n" + lang_line(lang)
            user = foreword_prompt(person, moments)

        else:  # /api/describe
            image = clip(body.get("image"), 3_000_000)
            if "base64," in image:
                image = image.split("base64,", 1)[1]
            if len(image) < 100:
                return self.send_json(400, {"error": "Choose a photo first."})
            images = [image]
            temperature = 0.2
            system = DESCRIBE_SYSTEM + "\n" + lang_line(lang)
            user = "Write the caption for this photograph."

        try:
            text = chat(system, user, images=images, temperature=temperature)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                msg = f"The model {MODEL} is not installed. Run: ollama pull {MODEL}"
            elif images:
                msg = f"{MODEL} could not read the photo. Pick a model that can read images, such as gemma3:4b."
            else:
                msg = f"Ollama returned an error ({err.code})."
            return self.send_json(502, {"error": msg})
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            return self.send_json(
                503, {"error": f"Could not reach Ollama at {OLLAMA}. Start it with: ollama serve"}
            )
        except Exception:
            return self.send_json(500, {"error": "The model did not answer. Try again."})

        if not text:
            return self.send_json(502, {"error": "The model returned nothing. Try again."})
        self.send_json(200, {"text": text})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Our Ofrenda is lit: http://localhost:{PORT}")
    print(f"Model: {MODEL} via Ollama at {OLLAMA}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCandles out. Goodnight.")