"""Runs before the app on every start.

1. First start only: if /data/liquidity-export.tar.gz exists and there is no chat.db yet,
   unpack the PythonAnywhere export into /data (databases) and /data/mysite (everything else).
2. Copy flask_app.py / gpt_router.py from the image (if the repo has them) over the volume copy.
3. Build /data/mysite/secret.py = imported secret.py + any LIQ_SECRET_<NAME> env vars
   (so keys can be changed in the Appliku dashboard without touching files).
"""
import os
import shutil
import sqlite3
import tarfile
import time

DATA = os.environ.get("LIQ_DATA", "/data")
SITE = os.path.join(DATA, "mysite")
EXPORT = os.path.join(DATA, "liquidity-export.tar.gz")
BASE_SECRET = os.path.join(DATA, "secret_base.py")
DB_FILES = ("chat.db", "gpt.db")


def log(*a):
    print("[prepare]", *a, flush=True)


def safe_members(tar, dest):
    root = os.path.realpath(dest)
    for m in tar.getmembers():
        target = os.path.realpath(os.path.join(dest, m.name))
        if not (target == root or target.startswith(root + os.sep)) or m.issym() or m.islnk():
            log("skipping unsafe entry", m.name)
            continue
        yield m


def import_export():
    if os.path.exists(os.path.join(DATA, "chat.db")) or not os.path.exists(EXPORT):
        return
    log("importing", EXPORT)
    stage = os.path.join(DATA, ".import")
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    with tarfile.open(EXPORT) as tar:
        tar.extractall(stage, members=safe_members(tar, stage), filter="data")
    for name in os.listdir(stage):
        src = os.path.join(stage, name)
        if name in DB_FILES:
            shutil.move(src, os.path.join(DATA, name))
        elif name == "flask_session_key.txt":
            shutil.move(src, os.path.join(DATA, ".flask_session_key"))
        elif name == "secret.py":
            shutil.move(src, BASE_SECRET)
        elif name == "requirements.txt":
            continue
        else:
            dst = os.path.join(SITE, name)
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            elif os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)
    shutil.rmtree(stage, ignore_errors=True)
    os.rename(EXPORT, EXPORT + ".imported")
    for db in DB_FILES:
        path = os.path.join(DATA, db)
        if os.path.exists(path):
            conn = sqlite3.connect(path)
            log(db, "integrity:", conn.execute("PRAGMA quick_check").fetchone()[0])
            conn.close()
    log("import finished")


def install_code():
    for name in ("flask_app.py", "gpt_router.py"):
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(SITE, name))
            log("code from repo:", name)
    if not os.path.exists(os.path.join(SITE, "flask_app.py")):
        raise SystemExit(
            "[prepare] No flask_app.py found. Copy liquidity-export.tar.gz into /data "
            "(see README) or add app/flask_app.py to the repo, then restart."
        )


def build_secret():
    lines = []
    if os.path.exists(BASE_SECRET):
        lines.append(open(BASE_SECRET, encoding="utf-8").read().rstrip("\n"))
    overrides = sorted((k[len("LIQ_SECRET_"):], v) for k, v in os.environ.items() if k.startswith("LIQ_SECRET_"))
    for key, value in overrides:
        if key.isidentifier():
            lines.append(f"{key} = {value!r}")
    path = os.path.join(SITE, "secret.py")
    with open(path + ".tmp", "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.replace(path + ".tmp", path)
    os.chmod(path, 0o600)
    log("secret.py ready:", len(overrides), "override(s) from env")


if __name__ == "__main__":
    for d in ("media", "pages", "downloads"):
        os.makedirs(os.path.join(SITE, d), exist_ok=True)
    import_export()
    repo_code = os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app", "flask_app.py"))
    while not repo_code and not os.path.exists(os.path.join(SITE, "flask_app.py")):
        log("waiting for liquidity-export.tar.gz in", DATA, "(run scripts/server_import.sh on the server)")
        time.sleep(10)
        import_export()
    install_code()
    build_secret()
