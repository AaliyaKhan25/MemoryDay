# MemoryDay
Hacktober Fest 2k26 week-4
# Our Ofrenda

A digital Día de los Muertos altar for a family. Each person gets a candle, a photo, a story, their favorite food and song, and a private note to them. You can also turn photos of them into a printable memory book. A small open-weight model running on your own computer helps write the stories and the book, and answers questions about your family archive.

## What the model does

- **Shape my notes into a story:** you type rough lines about someone and the model turns them into a short remembrance using only the facts you gave it, then asks for one detail to add.
- **Ask the family archive:** you ask a question and the model answers only from the stories you recorded. If nobody recorded it, it says "No one has told this story yet."
- **Make their book:** you add moments, each with a photo, what they were doing, when and where, and what you remember. The model can suggest a caption by looking at the photo (it describes only what is visible, never who anyone is). When you press "Write the book", it writes an opening note and one page per photo, in English or Hindi, in the third person. It never writes as the person who died. Every page stays editable, and you can reorder moments, then print the book or save it as an A5 PDF.

## Privacy

The page talks to `server.py` on `127.0.0.1`, and `server.py` talks to Ollama on `127.0.0.1`. No cloud API, no account, no key. Photos and stories are saved in your browser on your computer. It works with the internet off once the model is downloaded.

## Run it

1. Install Ollama from https://ollama.com and download a model:
   ```
   ollama pull gemma3:4b
   ```
   `gemma3:4b` and larger can read photos. Smaller or text-only models can still write stories and pages but cannot suggest captions from a photo.
2. Keep `ofrenda.html` and `server.py` in the same folder, then start the server (Python 3.8+, no packages to install):
   ```
   python server.py
   ```
3. Open http://localhost:8000

To use another model:
```
OLLAMA_MODEL=qwen2.5:3b python server.py
```
On Windows PowerShell: `$env:OLLAMA_MODEL="qwen2.5:3b"; python server.py`

## Printing the book

Press "Print or save as PDF". In the print window choose Save as PDF, set margins to None and turn on background graphics. Pages are A5. Printing works from the localhost version or from the downloaded `ofrenda.html`, not from a hosted preview.

## Notes

- The three people shown first are examples. Edit or remove them. They are left out of the archive the model sees.
- If you open `ofrenda.html` without `server.py`, everything still works except the AI buttons. You can write every book page by hand by clicking it in the preview.
- Small models make mistakes. The prompts tell the model not to invent facts, and you should read every page before you print.

## Files

- `ofrenda.html`: the altar and the book builder
- `server.py`: serves the page and relays requests to Ollama