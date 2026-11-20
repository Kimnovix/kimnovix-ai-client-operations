# Customer Complaint Responder: Setup Guide

After the one-time setup below, you never type commands. You edit one settings file in Notepad and double-click `run.bat`.

## Before You Start (one time, about 10 minutes)

1. **Install Python 3.13** from https://www.python.org/downloads/windows/. On the first installer screen, tick **"Add python.exe to PATH"**, then click **Install Now**.
2. **Have your Anthropic API key ready.** Log in at https://console.anthropic.com, open **API Keys**, and create a key. Add a small credit balance under **Plans & Billing** (each reply costs a few cents of a shilling).
3. **Be online for the first launch.** The first double-click of `run.bat` downloads the tool's components (1 to 3 minutes). After that, the tool still needs internet to draft replies, but nothing is reinstalled.

## Setup (3 Steps)

1. **Extract the folder.** Right-click the ZIP file, choose **Extract All**, and put the folder somewhere permanent (for example Documents). Do not run the tool from inside the ZIP.
2. **Create `config.env`.** In the folder, copy `config.env.example`, paste it, and rename the copy to exactly `config.env`. Open it in Notepad and fill in `ANTHROPIC_API_KEY`, `COMPANY_NAME`, `SUPPORT_PHONE`, `SUPPORT_EMAIL`, `ESCALATION_WINDOW` and `BUSINESS_POLICY`. Click **File > Save** and close Notepad.
   - If Windows hides file extensions, your copy may really be called `config.env.txt`. In File Explorer choose **View > Show > File name extensions** and remove the `.txt`. The tool also tells you if it finds `config.env.txt`.
3. **Double-click `run.bat`.** It checks your settings, starts the tool, and opens it in your web browser. Paste a customer complaint, click **Generate Reply**, read the draft, then click **Copy Reply** and paste it into WhatsApp, SMS or email.

Keep the black `run.bat` window open while you use the tool. To stop it, close that window (or press Ctrl+C in it).

## Daily Use

- Paste only the customer's latest message or the relevant part of the chat (the box shows how many characters you have left).
- Always read the draft before sending. You stay responsible for what goes to the customer.
- If the draft has a yellow note saying it may be cut off, read the end carefully or click **Generate Reply** again.
- Changing your phone number, policy or brand colour: edit `config.env`, save, close the `run.bat` window, and double-click `run.bat` again.

## If Something Goes Wrong

| Message You See | What It Means and How to Fix It |
| :--- | :--- |
| `Could not find 'config.env'` | Copy `config.env.example` and rename the copy to exactly `config.env` in the same folder as `run.bat`. |
| `Windows saved it as 'config.env.txt'` | Turn on **View > Show > File name extensions** in File Explorer and rename the file to `config.env`. |
| `ANTHROPIC_API_KEY is missing or still set to the example placeholder` | Paste your real key after `ANTHROPIC_API_KEY=` in `config.env`, with no spaces, and save. |
| `BRAND_COLOR (...) is not a valid hex color` | Use a colour code such as `#0f766e`. |
| `Python 3.10 or newer was not found` | Install Python 3.13 (see "Before You Start") with "Add python.exe to PATH" ticked. |
| `Installing components failed` | Check the internet connection and double-click `run.bat` again. |
| `This is running from inside the ZIP file` | Right-click the ZIP, choose **Extract All**, and run `run.bat` from the extracted folder. |
| `Port 5000 is already in use` | The tool is probably already open in another `run.bat` window. Use that one, or close it and try again. If it keeps happening, set `APP_PORT=5050` in `config.env`. |
| `AI login failed. Double-check your ANTHROPIC_API_KEY` | Check the key in `config.env` has no extra spaces and is still active in the Anthropic Console. |
| `Your Anthropic account has run out of credit` | Top up under **Plans & Billing** at console.anthropic.com, then click **Generate Reply** again. |
| `Could not reach the AI service` | The computer is offline. Reconnect Wi-Fi or data and click **Generate Reply** again. |
| `The AI service is busy right now` | Wait 30 seconds and click **Generate Reply** again. |
| `The AI declined to draft a reply` | The message may contain content the AI will not respond to. Handle this complaint personally. |
| A yellow note says a backup model was used | Replies still work. Tell your support contact so the setup can be updated. |

## Privacy

- The complaint text is sent to Anthropic's AI service to draft the reply. It is not saved on this computer.
- `responder.log` in the folder records only times, message lengths, token counts and cost, never the customer's words.
- Keep `config.env` private: it contains your API key. Do not email it or put it on a shared drive.
