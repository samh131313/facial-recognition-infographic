"""Runs once when a Cloud Run instance starts, before the app.

1. Writes ~/.flask_session_key from the FLASK_SESSION_KEY secret, so logins and the
   site-password cookie keep working across restarts (same key as PythonAnywhere).
2. For chat.db and gpt.db:
   - restore the latest copy from the Litestream backup in Cloud Storage, or
   - on the very first start, download the PythonAnywhere export from seed/<name>, or
   - create an empty database (the app makes its tables itself).
"""
import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HOME = os.path.expanduser("~")
CONFIG = "/opt/liquidity/litestream.yml"
BUCKET = os.environ.get("LIQUIDITY_DB_BUCKET", "")


def log(*parts):
    print("[bootstrap]", *parts, file=sys.stderr, flush=True)


def write_session_key():
    key = os.environ.get("FLASK_SESSION_KEY", "").strip()
    if key:
        with open(os.path.join(HOME, ".flask_session_key"), "w") as fh:
            fh.write(key)
        log("session key installed")
    else:
        log("FLASK_SESSION_KEY not set; a random key will be generated (logins reset on restart)")


def gcs_token():
    req = urllib.request.Request(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers={"Metadata-Flavor": "Google"},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.load(resp)["access_token"]


def download_seed(name, dest):
    if not BUCKET:
        return False
    obj = urllib.parse.quote("seed/" + name, safe="")
    url = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/{obj}?alt=media"
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + gcs_token()})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest + ".tmp", "wb") as fh:
            while chunk := resp.read(1 << 20):
                fh.write(chunk)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            log("seed download failed for", name, exc)
        return False
    except Exception as exc:  # metadata server missing when run locally
        log("seed download skipped for", name, exc)
        return False
    os.replace(dest + ".tmp", dest)
    return True


def prepare_db(name):
    path = os.path.join(HOME, name)
    if os.path.exists(path):
        return
    if BUCKET:
        subprocess.run(
            ["litestream", "restore", "-config", CONFIG, "-if-replica-exists", path],
            check=False,
        )
        if os.path.exists(path):
            log(name, "restored from Litestream backup")
            return
        if download_seed(name, path):
            log(name, "imported from PythonAnywhere export (first start)")
            return
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()
    log(name, "created empty")


if __name__ == "__main__":
    os.makedirs(HOME, exist_ok=True)
    write_session_key()
    for db in ("chat.db", "gpt.db"):
        prepare_db(db)
