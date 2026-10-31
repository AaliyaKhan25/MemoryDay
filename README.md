# MemoryDay · Our Ofrenda (El Altar de los Recuerdos)
*Hacktoberfest 2026 Memorial Experience*

A digital **Día de los Muertos (Day of the Dead)** family altar and heirloom memorial book generator. Each beloved person receives a flickering veladora (candle), a portrait, their story, their favorite food and song, sacred ofrenda offerings (Pan de Muerto, water, salt, copal, cempasúchil), voice recordings, and private letters.

Transform their life into an exquisite, **10+ page printed memorial volume** with an interactive **10-photo journey**. A local open-weight model running privately on your own computer observes each photo with the understanding that **your loved one is the primary focal heart**, generating warm, realistic captions and cohesive narrative pages.

---

## 🌟 The Complete Día de los Muertos Experience

### 1. 🎙️ Voice & Audio Keepsakes
- **In-Browser Voice & Audio Recorder**: Record directly from your microphone or attach saved audio files (voicemails, laughs, favorite songs).
- **Soundwave & Audio QR Badge in Book**: The printed memorial booklet features a dedicated **Audio Memory Badge and QR Code** so family members can scan the page with their phone to hear their voice and laughter forever.

### 2. ✉️ "Letters Across the Marigold Bridge" (*Cartas al Mictlán*)
- **Sacred Letter Writing**: Write private letters, heartfelt gratitude, or quiet family updates to anyone on the altar.
- **"Send with Copal Smoke" Ceremony**: An interactive ceremony where the letter parchment softly transforms, dissolves into glowing embers, and rises as fragrant copal smoke across the stars.
- **The Sacred Chest of Memories (*Cofre de Recuerdos*)**: An archive where all sent letters are kept safe so the family can read them together every Día de los Muertos.

### 3. 🌙 Midnight Candlelight Vigil Mode (*La Vigilia*)
- Click **"Midnight Vigil (La Vigilia)"** in the top bar to enter an immersive midnight vigil.
- Ambient lighting fades to a deep starry night; UI buttons dissolve away, leaving only the radiant altar.
- **Kindle the Flame**: Click on any veladora to flare their flame, play a sacred chime, and reveal their glowing memorial inscription.
- Accompanied by soothing Spanish classical guitar arpeggios, nighttime breeze, and mission bells.

### 4. 🍲 The Heirloom Recipe Card (*El Recetario de la Abuela*)
- Connected directly to their favorite food:
  - Generates their signature recipe, sensory aromas, the secret family ritual (e.g. *"stir clockwise with the wooden spoon, add two cinnamon sticks"*), and notes on who carries the recipe forward.
  - Generates a dedicated **Heirloom Recipe Keepsake Page** inside the 10+ page printed memorial book.

### 5. 🌳 The Constellation of Ancestors (*El Árbol de la Vida*)
- An interactive **Tree of Life** view:
  - Connects generations: Grandparents & Elders (*Los Sabios Ancestros*) ➔ Parents & Protectors (*Los Protectores*) ➔ Youth & Companions (*La Nueva Semilla*).
  - Highlights the eternal flow of love, traits, recipes, and smiles down the family line.

### 6. 💭 Sacred Remembrance Prompt Cards (*Cartas del Recuerdo*)
- An interactive 3D flippable deck of 12 profound, healing questions:
  1. *"What did their hands feel like when they held yours?"*
  2. *"What was their parting phrase every time you left their home?"*
  3. *"What was a quiet sacrifice they made that you only understood years later?"*
  4. *"What was their laugh like? Who in the family has that laugh now?"*
  5. *"What scent or sound immediately brings them back into the room?"*
  6. *"What did they forgive you for without ever holding a grudge?"*
  7. *"What was the funniest disaster or holiday mishap they laughed through?"*
  8. *"What was something they always carried in their pocket or purse?"*
  9. *"If you could share one more meal together tonight, what would you talk about?"*
  10. *"What advice of theirs turned out to be completely true?"*
  11. *"What song did they sing or hum when they thought no one was listening?"*
  12. *"What is one habit or value of theirs that you proudly carry today?"*
- Save family answers directly into their story archive!

### 7. 📜 Framable Altar Blessing Certificate (*Certificado del Altar*)
- One-click printable ceremonial certificate with Mexican baroque borders, official Day of the Dead seal, names of all honored loved ones, and sacred family dedication.
- Designed to be printed and framed in glass on your real, physical ofrenda at home.

### 8. 📖 10+ Page Heirloom Memorial Booklet (10 to 14 Pages)
- **10-Photo Memorial Journey**: Batch drop or select up to 10 photos in a single click, or use the **"✨ Add 10 Guided Life Chapters"** preset.
- **Person-as-Main-Element AI Captions**: The vision model focuses on the person as the primary subject, describing their smile, expression, posture, and action with warmth and realism.
- **Page Flip Reader vs. Continuous Scroll**: Read page-by-page like a real book, or view as a gallery.
- **Print or Save as A5 PDF & Standalone HTML**: Tuned for borderless A5 printing and exports a self-contained `.html` keepsake.

---

## 🔒 Privacy & Local Processing

- The page communicates with `server.py` on `127.0.0.1`, which connects to Ollama on `127.0.0.1`.
- **Zero cloud API, zero account, zero tracking.**
- Photos, audio recordings, and letters are stored securely in browser **IndexedDB** on your computer.
- Works 100% offline once the open-weight model is downloaded.

---

## 🚀 Getting Started

1. **Install Ollama** from [https://ollama.com](https://ollama.com) and pull a vision-capable model:
   ```bash
   ollama pull gemma3:4b
   ```
2. **Start the server** (Python 3.8+, no pip packages required):
   ```bash
   python server.py
   ```
3. **Open in your browser**:
   ```
   http://localhost:8000
   ```

To specify another model or port:
```bash
# PowerShell:
$env:OLLAMA_MODEL="gemma3:4b"; python server.py
```
