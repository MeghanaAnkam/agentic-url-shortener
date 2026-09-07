import secrets
import sqlite3
from datetime import datetime, timezone
from urllib.parse import urlparse
from contextlib import closing

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

app = FastAPI(title="Agentic URL Shortener")

DB_NAME = "urls.db"


class ShortenRequest(BaseModel):
    original_url: str


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class DailyCount(BaseModel):
    date: str
    count: int


class AnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    clicks: int
    created_at: str
    daily_counts: list[DailyCount]


class HealthResponse(BaseModel):
    message: str


def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=5)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def utc_today():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def setup_database():
    with closing(get_db()) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                short_code TEXT PRIMARY KEY,
                original_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_clicks (
                short_code TEXT NOT NULL,
                click_date TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (short_code, click_date),
                FOREIGN KEY (short_code) REFERENCES urls(short_code)
            )
        """)


setup_database()


@app.get("/", response_model=HealthResponse)
def health_check():
    return {"message": "URL Shortener is running"}


@app.post("/shorten", response_model=ShortenResponse)
def shorten_url(request: ShortenRequest):
    parsed_url = urlparse(request.original_url)

    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid URL starting with http:// or https://"
        )

    short_code = secrets.token_urlsafe(5)

    with closing(get_db()) as conn, conn:
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
    today = utc_today()
    try:
        with closing(get_db()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
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
            conn.execute("""
                INSERT INTO daily_clicks (short_code, click_date, count)
                VALUES (?, ?, 1)
                ON CONFLICT(short_code, click_date) DO UPDATE SET count = count + 1
            """, (short_code, today))
            conn.commit()
            return RedirectResponse(url=row[0], status_code=307)
    except sqlite3.OperationalError as error:
        code = getattr(error, "sqlite_errorcode", 0)
        if code & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise HTTPException(
                status_code=503,
                detail="Service temporarily busy",
            ) from error
        raise


@app.get("/analytics/{short_code}", response_model=AnalyticsResponse)
def get_analytics(short_code: str):
    with closing(get_db()) as conn, conn:
        conn.execute("BEGIN")
        row = conn.execute(
            "SELECT original_url, clicks, created_at FROM urls WHERE short_code = ?",
            (short_code,)
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Short URL not found")

        daily_rows = conn.execute(
            "SELECT click_date, count FROM daily_clicks WHERE short_code = ? ORDER BY click_date ASC",
            (short_code,)
        ).fetchall()

    return {
        "short_code": short_code,
        "original_url": row[0],
        "clicks": row[1],
        "created_at": row[2],
        "daily_counts": [{"date": r[0], "count": r[1]} for r in daily_rows]
    }
