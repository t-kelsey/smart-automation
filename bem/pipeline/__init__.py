"""Settings come from the environment, else from `bem/.env`, else from a `.env` further up (e.g. the repo root)."""

import pathlib

from dotenv import find_dotenv, load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")  # never overrides real env vars
load_dotenv(find_dotenv(usecwd=True))
