import secrets
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Agentic URL Shortener")

DB_NAME = "urls.db"


class ShortenRequest(BaseModel):
    original_url: str


def get_db():
    return sqlite3.connect(DB_NAME)


def setup_database():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                short_code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)


setup_database()


@app.get("/")
def health_check():
    return {"message": "URL Shortener is running"}


@app.post("/shorten")
def shorten_url(request: ShortenRequest):
    parsed_url = urlparse(request.original_url)

    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid URL starting with http:// or https://"
        )

    short_code = secrets.token_urlsafe(5)

    with get_db() as conn:
        conn.execute(
            "INSERT INTO urls (short_code, original_url, created_at) VALUES (?, ?, ?)",
            (short_code, request.original_url, datetime.now(timezone.utc).isoformat())
        )

    return {
        "short_code": short_code,
        "short_url": f"http://127.0.0.1:8000/{short_code}"
    }


@app.get("/{short_code}")
def redirect_to_original_url(short_code: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT original_url FROM urls WHERE short_code = ?",
            (short_code,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Short URL not found")

        conn.execute(
            "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?",
            (short_code,)
        )

    return RedirectResponse(url=row[0], status_code=307)


@app.get("/analytics/{short_code}")
def get_analytics(short_code: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT original_url, clicks, created_at FROM urls WHERE short_code = ?",
            (short_code,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return {
        "short_code": short_code,
        "original_url": row[0],
        "clicks": row[1],
        "created_at": row[2]
    }