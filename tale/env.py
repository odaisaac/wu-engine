"""Shared helpers: repo paths and keys from a local .env file.

Keys are read from the environment first, then from `.env` in the repo root
(created by `python setup.py`). `.env` is git-ignored: never commit it.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "models")
FONTS = os.path.join(ROOT, "tale", "fonts")


def load_env():
    p = os.path.join(ROOT, ".env")
    if not os.path.exists(p):
        return
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v and not os.environ.get(k):
            os.environ[k] = v


def key(name):
    load_env()
    return os.environ.get(name, "")
