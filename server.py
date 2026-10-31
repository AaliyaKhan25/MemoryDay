#!/usr/bin/env python3
"""Our Ofrenda: serves the altar page and talks to a local open-weight model through Ollama
or cloud Gemini API if GEMINI_API_KEY is configured.

Runs anywhere: locally on 127.0.0.1 or deployed to Render / cloud hosts.

Run locally:
    python server.py
Then open http://localhost:8000

Settings (environment variables):
    PORT              port for this web service (Render injects this automatically)
    GEMINI_API_KEY    optional Google Gemini API key for cloud inference on Render
    OLLAMA_MODEL      local model to use (default: gemma3:4b)
    OLLAMA_HOST       where Ollama listens (default: http://127.0.0.1:11434)
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MAX_BODY = 500_000
MAX_IMAGE_BODY = 6_000_000

LANGS = {
    "en": "English",
    "es": "Spanish (Español), warm, respectful, and dignified in the authentic Día de los Muertos memorial tradition",
    "hi": "Hindi in Devanagari script, using warm, respectful and emotional everyday words",
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

DESCRIBE_SYSTEM = """You write an evocative, realistic, and touching caption for a photograph in a Día de los Muertos (Day of the Dead) family memorial book.

CORE DIRECTIVE: The person in the photograph is the PRIMARY SUBJECT, focal point, and main element of the image.
Rules:
- Treat the person as the main element: describe their posture, expression, smile, gaze, gesture, activity, or what they are holding or wearing.
- The environment and surrounding elements are the supportive setting that highlights their character, presence, and life story.
- If the family gave you their name or relationship, refer to them naturally (e.g. "Grandmother Elena smiling warmly in her kitchen...", or "Nani proudly tending to her mango saplings...").
- Ground the description in what is genuinely visible. Never write cold, detached object lists ("A person next to a plate").
- Write 1 to 2 warm, realistic sentences (around 20 to 35 words). Dignified, heartfelt, and lifelike.
- Reply with the caption text only, without quotes or preface."""

CALAVERITA_SYSTEM = """You write an authentic, affectionate Calaverita Literaria (or memorial poetic verse) honoring a loved one for Día de los Muertos.

Rules:
- In Mexican tradition, a Calaverita Literaria is a rhyming, rhythmic folk poem honoring someone's joyful quirks, passions, favorite food, or laughter, saying that even La Catrina (Death) paused to admire them.
- Use only facts from the family (name, relation, favorite food, song, personality traits).
- 4 to 8 lines in rhythmic stanzas.
- Celebratory, loving, and respectful—celebrating life and memory.
- Reply with the verse only."""

BLESSING_SYSTEM = """You write a warm, poignant Día de los Muertos ofrenda dedication and spirit welcome for a family memorial book.

Rules:
- Honor their spirit returning home along the golden trail of cempasúchil marigold petals.
- Bless the offerings placed for them: the warm candle light, pan de muerto, pure water, and salt.
- 60 to 100 words in one touching paragraph.
- Write in warm family third-person or collective "we".
- Reply with the dedication paragraph only."""

RECIPE_SYSTEM = """You write an evocative heirloom culinary remembrance and recipe story for a Día de los Muertos memorial book.

Rules:
- Focus on the signature dish their family remembers them cooking or loving.
- Evoke the sensory aromas: the roasting spices, simmering broths, sweetness of canela (cinnamon), vanilla, or fresh herbs.
- Highlight the love and family ritual poured into preparing this dish.
- 80 to 130 words in warm, poetic prose.
- Reply with the recipe remembrance only."""

LETTER_SYSTEM = """You write a gentle, poetic Día de los Muertos ancestral blessing in response to a family member's letter sent across the marigold bridge with copal smoke.

Rules:
- Speak from the warm spirit of the altar and ancestral love: reminding the family that love never dies, that every memory keeps the flame alive, and that their words are heard across the stars.
- Do NOT impersonate the dead as a ghost; speak as the gentle wisdom of the Ofrenda honoring the eternal bond.
- 70 to 110 words in comforting, heartfelt language.
- Reply with the blessing only."""


def clip(value, limit=1500):
    return str(value or "").strip()[:limit]


def lang_line(code):
    return "Write in " + LANGS.get(code, LANGS["en"]) + "."


def gemini_request(system, user, images=None, temperature=0.5):
    parts = [{"text": user}]
    if images:
        for img in images:
            raw_b64 = img.split("base64,", 1)[1] if "base64," in img else img
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": raw_b64
                }
            })
    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature}
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        res = json.loads(resp.read().decode())
        candidates = res.get("candidates", [])
        if candidates:
            c_parts = candidates[0].get("content", {}).get("parts", [])
            if c_parts:
                return c_parts[0].get("text", "").strip()
    return ""


def ollama_request(path, payload=None, timeout=240):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        OLLAMA + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def chat(system, user, images=None, temperature=0.5):
    if GEMINI_API_KEY:
        try:
            txt = gemini_request(system, user, images=images, temperature=temperature)
            if txt:
                return txt
        except Exception as e:
            print("  [Gemini API Cloud fallback]:", e)

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
    if GEMINI_API_KEY:
        return {"ok": True, "ollama": True, "model": "Gemini 1.5 Flash (Cloud)", "model_ready": True}
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
        f"Caption under the photo: {clip(moment.get('caption'), 140)}",
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
    for m in moments[:40]:
        if isinstance(m, dict):
            lines.append(f"- {clip(m.get('title'), 80)} ({clip(m.get('when'), 40)})")
    return "\n".join(lines)


def describe_prompt(body):
    person = body.get("person") or {}
    name = clip(body.get("person_name") or person.get("name"), 60)
    rel = clip(body.get("person_rel") or person.get("rel"), 80)
    title = clip(body.get("title") or (body.get("moment") or {}).get("title"), 80)
    notes = clip(body.get("notes") or (body.get("moment") or {}).get("notes"), 400)
    when = clip(body.get("when") or (body.get("moment") or {}).get("when"), 40)
    where = clip(body.get("where") or (body.get("moment") or {}).get("where"), 60)

    lines = ["Write a realistic memorial caption for this photograph with the person as the main element."]
    if name:
        lines.append(f"Person honored: {name}" + (f" ({rel})" if rel else ""))
        lines.append(f"Focal rule: {name} is the primary subject in the frame. Focus on their expression, gaze, posture, and presence.")
    if title:
        lines.append(f"Moment title: {title}")
    meta = " · ".join([m for m in (when, where) if m])
    if meta:
        lines.append(f"When and where: {meta}")
    if notes:
        lines.append(f"Family remembrance notes: {notes}")
    lines.append("Describe what makes them the living heart of this scene.")
    return "\n".join(lines)


def calaverita_prompt(person):
    lines = person_lines(person) + [
        "",
        "What the family remembers:",
        clip(person.get("story"), 600),
    ]
    return "\n".join(lines)


def blessing_prompt(person, offerings=None):
    lines = person_lines(person)
    if offerings and isinstance(offerings, list):
        lines.append(f"Offerings on their altar: {', '.join([str(o) for o in offerings])}")
    lines.append("Write a touching ofrenda dedication welcoming their spirit home across the marigolds.")
    return "\n".join(lines)


def recipe_prompt(person, dish_notes=""):
    lines = person_lines(person) + [
        f"The signature dish they cooked or loved: {clip(person.get('food'), 100)}",
        f"Family notes about their cooking / ritual: {clip(dish_notes, 400)}",
    ]
    return "\n".join(lines)


def letter_prompt(person, letter_text):
    lines = person_lines(person) + [
        "",
        "Letter written to them by their loving family:",
        clip(letter_text, 1200),
    ]
    return "\n".join(lines)


ROUTES = {
    "/api/story",
    "/api/ask",
    "/api/chapter",
    "/api/foreword",
    "/api/describe",
    "/api/calaverita",
    "/api/blessing",
    "/api/recipe",
    "/api/letter",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "Ofrenda/2.0"

    def log_message(self, fmt, *args):
        print("  " + fmt % args)

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def send_json(self, status, payload):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_cors_headers()
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
            self.send_cors_headers()
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
            if not (clip(moment.get("title"), 80) or clip(moment.get("notes"), 900) or clip(moment.get("caption"), 140)):
                return self.send_json(400, {"error": "Add what they were doing or a few lines about this photo first."})
            system = CHAPTER_SYSTEM + "\n" + lang_line(lang)
            user = chapter_prompt(person, moment)

        elif path == "/api/foreword":
            person, moments = body.get("person"), body.get("moments")
            if not isinstance(person, dict) or not isinstance(moments, list) or not clip(person.get("name")):
                return self.send_json(400, {"error": "Could not read that request."})
            system = FOREWORD_SYSTEM + "\n" + lang_line(lang)
            user = foreword_prompt(person, moments)

        elif path == "/api/calaverita":
            person = body.get("person")
            if not isinstance(person, dict) or not clip(person.get("name")):
                return self.send_json(400, {"error": "Add the person's name first."})
            system = CALAVERITA_SYSTEM + "\n" + lang_line(lang)
            user = calaverita_prompt(person)
            temperature = 0.7

        elif path == "/api/blessing":
            person = body.get("person")
            offerings = body.get("offerings")
            if not isinstance(person, dict) or not clip(person.get("name")):
                return self.send_json(400, {"error": "Add the person's name first."})
            system = BLESSING_SYSTEM + "\n" + lang_line(lang)
            user = blessing_prompt(person, offerings)
            temperature = 0.5

        elif path == "/api/recipe":
            person = body.get("person")
            notes = body.get("notes") or ""
            if not isinstance(person, dict) or not clip(person.get("name")):
                return self.send_json(400, {"error": "Add the person's name first."})
            system = RECIPE_SYSTEM + "\n" + lang_line(lang)
            user = recipe_prompt(person, notes)
            temperature = 0.5

        elif path == "/api/letter":
            person = body.get("person")
            letter_text = body.get("letter") or ""
            if not isinstance(person, dict) or not clip(letter_text):
                return self.send_json(400, {"error": "Write a letter first."})
            system = LETTER_SYSTEM + "\n" + lang_line(lang)
            user = letter_prompt(person, letter_text)
            temperature = 0.5

        else:  # /api/describe
            image = clip(body.get("image"), 4_000_000)
            if "base64," in image:
                image = image.split("base64,", 1)[1]
            if len(image) < 100:
                return self.send_json(400, {"error": "Choose a photo first."})
            images = [image]
            temperature = 0.35
            system = DESCRIBE_SYSTEM + "\n" + lang_line(lang)
            user = describe_prompt(body)

        try:
            text = chat(system, user, images=images, temperature=temperature)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                msg = f"The model {MODEL} is not installed. Run: ollama pull {MODEL}"
            elif images:
                msg = f"{MODEL} could not read the photo. Pick a model that can read images, such as gemma3:4b."
            else:
                msg = f"Inference returned an error ({err.code})."
            return self.send_json(502, {"error": msg})
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            return self.send_json(
                503, {"error": f"Could not reach model server at {OLLAMA}."}
            )
        except Exception:
            return self.send_json(500, {"error": "The model did not answer. Try again."})

        if not text:
            return self.send_json(502, {"error": "The model returned nothing. Try again."})
        self.send_json(200, {"text": text})


def start_server():
    ThreadingHTTPServer.allow_reuse_address = True
    port_env = os.environ.get("PORT")

    if port_env:
        # Render / production cloud provides $PORT
        chosen_port = int(port_env)
        srv = ThreadingHTTPServer(("0.0.0.0", chosen_port), Handler)
    else:
        # Local development port hunting
        port_candidates = [8000, 8080, 8088, 8888, 5000]
        srv = None
        chosen_port = None
        for p in port_candidates:
            try:
                srv = ThreadingHTTPServer(("0.0.0.0", p), Handler)
                chosen_port = p
                break
            except OSError:
                try:
                    srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
                    chosen_port = p
                    break
                except OSError:
                    continue
        if not srv:
            print("ERROR: Could not bind to any available port.")
            return

    print("\n" + "=" * 60)
    print("  🌼 Our Ofrenda (MemoryDay) is lit and running! 🌼")
    print("=" * 60)
    print(f"  👉 Listening on port {chosen_port}")
    print(f"     http://localhost:{chosen_port}")
    print("=" * 60)
    ai_desc = "Gemini API (Cloud)" if GEMINI_API_KEY else f"{MODEL} via Ollama at {OLLAMA}"
    print(f"  Local/Cloud AI: {ai_desc}")
    print("  (Press Ctrl+C to stop the server)\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nCandles out. Goodnight.")


if __name__ == "__main__":
    start_server()
