# Nova Agro-Vet 24/7 Business AI Assistant

- **What it does:** A 24/7 customer support chatbot grounded strictly in a business's own product catalog, delivery policies, and FAQs, answering questions in English, Swahili, or Sheng with source citations.
- **Who it helps:** Kenyan agro-vets, feed distributors, veterinary clinics, hardware depots, and wholesale suppliers (1 to 30 staff).
- **Problem it solves:** Eliminates repetitive WhatsApp and phone inquiries about prices, bulk discounts, M-Pesa Paybill numbers, and delivery days while preventing staff or AI from quoting wrong prices or giving unauthorized veterinary prescriptions.
- **Stack:** Python 3.13, Flask, Gunicorn, Anthropic Claude API (`claude-haiku-5-5` with `claude-haiku-4-5-20251001` fallback), `pypdf`, `python-docx`, deployed on Render.
- **GitHub:** https://github.com/Kimnovix/kimnovix-ai-client-operations/tree/main/week6/day30_ai_assistant

*Nova Agro-Vet & Feeds Ltd is a sample business. Its phone, email, Paybill and Till numbers are placeholders; replace the files in `docs/` and the values in `.env` with the client's real ones before going live.*

## Local Setup (3 Steps)

1. Copy `.env.example` to `.env` and paste your `ANTHROPIC_API_KEY` (and business details if customizing). On Windows, double-clicking `run.bat` does this for you and opens `.env` in Notepad.
2. Drop any `.md`, `.txt`, `.pdf`, or `.docx` business documents into `docs/`.
3. Run tests and start the server:
   ```powershell
   python pipeline.py --self-test
   python app.py --check-config
   python app.py
   ```

On a client PC with no virtual environment, `run.bat` finds Python 3.10 or newer, builds a private `venv\` on the first run, installs `requirements.txt`, checks the settings and opens the chat page.

## Commands

```powershell
python pipeline.py --self-test                       # 14 isolated tests, fake Claude clients, no API cost
python pipeline.py --dry-run -q "Delivery to Turbo?" # offline retrieval preview, no API cost
python pipeline.py -q "Bei ya Sow Lactation Meal?"   # one live answer with telemetry
python app.py --check-config                         # validate .env and docs, then exit
python app.py --dry-run                              # chat UI offline
python app.py --no-browser                           # start without opening a browser tab
```

## Deploy on Render

Live demo: https://nova-agrovet-assistant.onrender.com (free tier, so the first visit after 15 idle minutes takes 30 to 50 seconds).

- **Build command:** `pip install -r week6/day30_ai_assistant/requirements.txt`
- **Start command:** `gunicorn --chdir week6/day30_ai_assistant --workers 2 --threads 4 --timeout 180 --bind 0.0.0.0:$PORT "app:create_wsgi_app()"`
- **Environment:** `ANTHROPIC_API_KEY` plus any business settings from `.env.example`. Render sets `PORT`, `RENDER` and `RENDER_EXTERNAL_HOSTNAME` itself. Add a custom domain to `ALLOWED_HOSTS`.
- **Health check path:** `/api/health` (exempt from the Host check, because Render's checker does not use the public hostname).

`--timeout 180` matters: one question can take up to about 127 seconds in the worst case (four 30-second attempts plus 1/2/4-second backoff), and Gunicorn's default 30-second timeout would kill the worker mid-answer. On Render the log is also printed to stdout, because the disk is wiped on every deploy.

## Safety and Cost Controls

- Answers only from the documents in `docs/`, cites the file name, and sends sick-animal or dosage questions to the duty vet line.
- Customer text and documents are wrapped in tags and treated as data. Look-alike tags typed by a visitor are neutralised, and the system prompt tells the model that a price or policy from earlier chat turns is not a fact unless it is in the documents.
- `RATE_LIMIT_PER_10_MIN` (default 20 per visitor IP) and `DAILY_CHAT_CAP` (default 1,000 per worker) stop a public page from running up the API bill. Counts are in memory and reset on restart.
- `SHOW_CITATIONS` and `SHOW_TELEMETRY` (both `true` by default) put `[file.md]` citations in answers and a sources / model / response time / KES cost line under each one. They are on for demo transparency. For a client's production customer chat, set both to `false`: answers read like the shop's own staff wrote them, and the cost and model details stay in `logs/app.log` for the owner.
- `logs/app.log` records an 8-character hash and the length of each question, never the words.
