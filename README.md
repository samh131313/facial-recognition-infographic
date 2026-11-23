# Liquidity → Appliku (Hetzner server)

This moves the Liquidity chat (Flask + Eaglercraft relay WebSockets) from
`gerbilzillo.pythonanywhere.com` to **`yourname.applikuapp.com`**, which opens on the Chromebook.

- **Hetzner** rents you the server (about €4–5/month).
- **Appliku** (free plan) builds this repo's `Dockerfile` on that server and serves it over HTTPS.
- One **persistent volume at `/data`** holds everything, laid out like your PythonAnywhere home folder:

```
/data/chat.db  /data/gpt.db  /data/.flask_session_key
/data/mysite/  flask_app.py  gpt_router.py  secret.py
               media/  pages/  downloads/  minecraft_game/  fps_test/
```

`flask_app.py` runs **unchanged** through its ASGI entry point (`multiplayer_asgi`) under uvicorn.
`appliku/asgi_entry.py` only tells it that visitors are on HTTPS, so the site-password form and the
Eaglercraft relay's origin checks pass behind Appliku's proxy.

Your secrets, databases and uploads are never committed. They travel inside `liquidity-export.tar.gz`
straight onto the server volume.

---

## Step 1: Hetzner server

1. Sign up at <https://www.hetzner.com/cloud> and add your card. They may ask for ID verification.
2. Create a **project**, then **Add Server**:
   - **Location:** Ashburn or Hillsboro (US), or whichever is closest to you.
   - **Image:** Ubuntu (the LTS version Appliku lists as supported).
   - **Type:** shared vCPU, the smallest x86 option (CX22 / CPX11, 2 vCPU / 2–4 GB).
   - **SSH key:** skip it unless you have one. Hetzner then emails you the root password.
   - Create it and note the **IP address**.

## Step 2: Appliku

1. Sign up at <https://appliku.com> and connect your **GitHub** account.
2. **Servers → Add server**. Choose Hetzner or a custom server and follow the prompts to connect the
   server from step 1. Appliku installs its tools on it, which takes a few minutes.
3. **Create application**:
   - **Repository:** `samh131313/facial-recognition-infographic`
   - **Branch:** `claude/pythonanywhwre-chromebook-migration-yo2dk7`
   - **Build:** *Dockerfile* (`Dockerfile` in the repo root)
   - **Web process / port:** container listens on **8000** (it also honours `$PORT`)
   - **Volume:** add one with **target / container path `/data`**. *This is essential: without it,
     every deploy wipes your data.*
   - **Name:** this becomes `NAME.applikuapp.com`.
4. **Deploy.** The app starts and *waits* for your data. Its logs say
   `waiting for liquidity-export.tar.gz`.

## Step 3: Move your data from PythonAnywhere

1. In a PythonAnywhere **Bash console**:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/samh131313/facial-recognition-infographic/claude/pythonanywhwre-chromebook-migration-yo2dk7/scripts/export_from_pythonanywhere.sh | bash
   ```
   Then download `liquidity-export.tar.gz` from the **Files** page (home folder). Stop using the old
   site from this point.
2. On your Windows PC, in **PowerShell** (from the folder holding the download):
   ```powershell
   scp liquidity-export.tar.gz root@SERVER_IP:/root/
   ssh root@SERVER_IP
   ```
3. Now on the server:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/samh131313/facial-recognition-infographic/claude/pythonanywhwre-chromebook-migration-yo2dk7/scripts/server_import.sh | bash
   ```
   Within 10 seconds the app imports everything and starts. Open `https://NAME.applikuapp.com`
   and enter your usual site password.

## Step 4: Check it on the Chromebook

- `https://NAME.applikuapp.com` loads; log in and see your old messages.
- `https://NAME.applikuapp.com/multiplayer-test`, join a room: **this confirms WebSockets (wss) get
  through your Chromebook's filter.**
- Upload a file of about 10 MB in chat. If that fails, raise the upload / body size limit in Appliku's
  app settings (Liquidity sends up to 8 MB chunks, and single uploads up to 72 MB).
- Eaglercraft relay address: `wss://NAME.applikuapp.com/eagler-relay`.

---

## Changing API keys

In Appliku, open the app's **Environment variables** and add `LIQ_SECRET_<NAME>`, e.g.
`LIQ_SECRET_GROQ_KEY`, `LIQ_SECRET_OPENROUTER_KEY`, `LIQ_SECRET_CHAT_PASSWORD`. Then restart or redeploy.
These override the matching values from your old `secret.py`.

## Editing the code

Right now the code comes from the PythonAnywhere export (stored on the volume). To edit it through
GitHub, make this repo **private**, then put `flask_app.py` and `gpt_router.py` in `app/` and push.
Every deploy copies them over the volume's copy.

## Files

- `Dockerfile`: Python 3.12 plus your requirements
- `appliku/start.sh`: runs `prepare.py`, then uvicorn on port 8000
- `appliku/prepare.py`: first-time import, code install and `secret.py` build
- `appliku/asgi_entry.py`: HTTPS-aware wrapper around `flask_app:multiplayer_asgi`
- `scripts/export_from_pythonanywhere.sh`: run on PythonAnywhere
- `scripts/server_import.sh`: run on the Hetzner server

A Cloud Run version of this kit is in this branch's history (commit `Cloud Run migration kit…`), if you ever need it.
