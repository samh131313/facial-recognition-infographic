# Liquidity → Google Cloud Run

Moves the Liquidity chat (Flask + Eaglercraft relay WebSockets) from
`gerbilzillo.pythonanywhere.com` to a **`*.run.app`** address, which opens on the Chromebook.

Your app code, `secret.py`, databases and uploads are **never committed here**. They come from a
one-off PythonAnywhere export and stay on your PC, in Google Secret Manager and in Cloud Storage.

## How it runs

| On PythonAnywhere | On Cloud Run |
|---|---|
| `~/chat.db`, `~/gpt.db` | Local disk inside the container, backed up to the `…-liq-db` bucket every second by [Litestream](https://litestream.io). Restored automatically on each start. |
| `mysite/media`, `pages`, `downloads` | Mounted Cloud Storage buckets `…-liq-media`, `…-liq-pages`, `…-liq-downloads` |
| `mysite/minecraft_game`, `fps_test` | Baked into the container image |
| `secret.py`, `~/.flask_session_key` | Secret Manager (`liquidity-secret-py`, `liquidity-session-key`) |
| ASGI `flask_app:multiplayer_asgi` | Same entry point, run by uvicorn with HTTPS proxy headers |

`flask_app.py` and `gpt_router.py` run **unmodified**: the container recreates the same folder
layout (`HOME=/home/gerb`, code in `/home/gerb/mysite`).

The service runs **one instance at most** (SQLite and the game rooms live in one process) and
**scales to zero** when idle. CPU is billed only while requests are being handled, so a tab left
open costs almost nothing. Expect **about $2–8/month**.

## One-time setup (main PC, Windows)

1. **Google Cloud account.** Go to <https://console.cloud.google.com>, add your card, and create a project
   (e.g. `liquidity-chat`). Note the **project ID**.
2. **Budget alert.** In the console, open *Billing → Budgets & alerts → Create budget*, set $20, and
   alert at 50/90/100%.
3. **Install the Google Cloud SDK.** Download it from <https://cloud.google.com/sdk/docs/install>
   (the Windows installer). Then open a **new** PowerShell and run `gcloud auth login`.
4. **Get this repo.** Use *Code → Download ZIP* on GitHub (branch
   `claude/pythonanywhwre-chromebook-migration-yo2dk7`) and unzip it, or `git clone` it.

## Export from PythonAnywhere

Open a **Bash console** on PythonAnywhere and paste:

```bash
curl -fsSL https://raw.githubusercontent.com/samh131313/facial-recognition-infographic/claude/pythonanywhwre-chromebook-migration-yo2dk7/scripts/export_from_pythonanywhere.sh | bash
```

(Or create the file `export.sh` from `scripts/export_from_pythonanywhere.sh` in the Files tab and run `bash export.sh`.)

Then download `liquidity-export.tar.gz` from the **Files** page (home folder) onto your PC.
Anything posted on the old site after this point won't be copied, so stop using it now.

## Deploy

In PowerShell, inside the unzipped repo folder:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -ProjectId YOUR-PROJECT-ID -Export C:\Users\you\Downloads\liquidity-export.tar.gz
```

The first run takes about 10 minutes. At the end it prints your new address, e.g.
`https://liquidity-123456789.us-central1.run.app`. Open that on the Chromebook and enter the same site password.

### Updating later

Edit the files in `app\` (that is your code now), then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1 -ProjectId YOUR-PROJECT-ID
```

Your data is kept. To change API keys, edit `export\secret.py` and rerun with `-Export export`.
Or run `gcloud secrets versions add liquidity-secret-py --data-file secret.py`, then redeploy.

## Things that differ from PythonAnywhere

- **First load after idle** takes about 5–10 s while the container starts.
- **WebSockets are cut after 60 minutes** (Cloud Run's request limit). Eaglercraft/arena players
  need to reconnect at that point. Eaglercraft relay address: `wss://<your-run.app-host>/eagler-relay`.
- **Single uploads over 32 MB fail.** This only affects non-owner video/image uploads between 32 and 72 MB.
  Owner uploads are chunked (8 MB) and work at any size.
- **New origin:** everyone re-enters the site password once and re-enables push notifications.
  Accounts, messages and files carry over.
- **Deploying while people are chatting** can lose the last second or two of messages written to the old instance.
- To start over with a fresh import: `gcloud storage rm -r gs://YOUR-PROJECT-ID-liq-db/litestream`, then deploy with `-Export` again.

## Files

- `Dockerfile`: the container (Python 3.12, your requirements, Litestream)
- `deploy/start.sh`: restores the databases, then runs uvicorn under Litestream
- `deploy/bootstrap.py`: session key, plus database restore / first-time import
- `deploy/litestream.yml`: database backup targets
- `scripts/export_from_pythonanywhere.sh`: run on PythonAnywhere
- `scripts/deploy.ps1`: creates buckets, secrets and the service account, then builds and deploys
