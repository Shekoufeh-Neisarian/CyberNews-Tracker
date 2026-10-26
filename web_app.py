"""CyberNews Tracker — Flask news reader with RSS and protected accounts."""
import hmac
import hashlib
import html
from html.parser import HTMLParser
import json
import os
import secrets
import re
import sqlite3
import time
import xml.etree.ElementTree as ET
import threading
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from contextlib import closing
from datetime import datetime, timezone, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urljoin
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler

from flask import Flask, jsonify, make_response, redirect, render_template, request, url_for, Response
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Small SQLite table for the new real-world bookmarks feature.
# This is separate from the larger Base44 reference project database.
BOOKMARKS_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cybernews_bookmarks.db")

# Accounts and login activity are saved in the existing local SQLite file.
# Existing bookmarks are preserved: we only add new tables.
ACCESS_ROLES = ("user", "admin")
PROFILE_TITLES = (
    "Reader", "Student", "Teaching Assistant", "Professor",
    "Researcher", "Security Analyst", "Guest",
)


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def open_accounts_db():
    db = sqlite3.connect(BOOKMARKS_DB, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def initialize_accounts():
    """Create tables once, preserving the existing bookmark database."""
    with closing(open_accounts_db()) as db:
        with db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY COLLATE NOCASE,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    access_role TEXT NOT NULL DEFAULT 'user',
                    profile_title TEXT NOT NULL DEFAULT 'Reader',
                    registered_at TEXT NOT NULL,
                    previous_login_at TEXT,
                    last_login_at TEXT,
                    login_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS login_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    logged_in_at TEXT NOT NULL,
                    FOREIGN KEY (username) REFERENCES users(username)
                );
                CREATE INDEX IF NOT EXISTS idx_login_events_time
                    ON login_events(logged_in_at DESC);
                CREATE TABLE IF NOT EXISTS translation_cache (
                    input_hash TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (input_hash, target_language)
                );
                CREATE TABLE IF NOT EXISTS rss_cache (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT NOT NULL,
                    published_at TEXT,
                    image_url TEXT,
                    cached_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS contact_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    message TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'unread'
                        CHECK (status IN ('unread', 'read'))
                );
                CREATE INDEX IF NOT EXISTS idx_contact_messages_time
                    ON contact_messages(id DESC);
            """)
            # Known demo accounts are hashed in SQLite instead of storing
            # plaintext passwords in the application code.
            for username, display_name, password, role, title in (
                ("user", "User", "user123", "user", "Reader"),
                ("admin", "Administrator", "admin123", "admin", "Security Analyst"),
            ):
                if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone() is None:
                    db.execute(
                        """INSERT INTO users
                        (username, display_name, password_hash, access_role, profile_title, registered_at)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (username, display_name, generate_password_hash(password), role, title, utc_now()),
                    )


initialize_accounts()

# Session details stay on the server. Browser holds only a random token.
SESSIONS = {}
SESSION_LIFETIME = 30 * 60  # seconds
SESSION_COOKIE = "session_token"
# Use False for HTTP at 127.0.0.1; set COOKIE_SECURE=1 when using HTTPS.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"

# Separate API bearer tokens for this LOCAL exercise.
# These are demonstration credentials, not production secrets.
# Token access is intentionally independent of Flask login sessions.
ACTIVE_TOKENS = {
    "analyst-demo-2026": {"username": "intel_analyst", "role": "analyst"},
    "admin-demo-2026": {"username": "intel_admin", "role": "admin"},
}



def current_user():
    """Check an unexpired session AND the current role stored in SQLite."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user = SESSIONS.get(token)
    if not user or user["expires_at"] <= time.time():
        SESSIONS.pop(token, None)
        return None
    with closing(open_accounts_db()) as db:
        account = db.execute(
            "SELECT username, display_name, access_role, profile_title FROM users WHERE username=?",
            (user["username"],),
        ).fetchone()
    if account is None:
        SESSIONS.pop(token, None)
        return None
    # Authorizations always follow the server-side database, not stale sessions.
    user["role"] = account["access_role"]
    user["display_name"] = account["display_name"]
    user["profile_title"] = account["profile_title"]
    return user


@app.context_processor
def inject_user():
    """Provide trusted server-side user data to all Jinja templates."""
    user = current_user()
    return {"auth_user": user, "csrf_token": user.get("csrf_token", "") if user else ""}


@app.after_request
def no_cache_sensitive_pages(response):
    """Help avoid showing cached dashboard contents after logout."""
    if request.endpoint in {"login", "user_dashboard", "admin_dashboard", "cookie_check", "session_info", "logout", "news", "api_news", "api_live_news", "intelligence_page", "intelligence_feed", "bookmarks_page", "bookmarks_api", "register", "update_user_profile", "contact", "submit_message", "admin_contact_message"}:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        user = current_user()
        if user is not None:
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "user_dashboard"))
        return render_template(
            "login.html",
            login_required=request.args.get("required") == "1",
            registered=request.args.get("registered") == "1",
        )

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    with closing(open_accounts_db()) as db:
        account = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        valid = bool(account and check_password_hash(account["password_hash"], password))
        if not valid:
            return render_template("login.html", error="Invalid username or password."), 401

        # Login history persists even when the Flask process restarts.
        now = utc_now()
        with db:
            db.execute(
                """UPDATE users SET previous_login_at=last_login_at,
                   last_login_at=?, login_count=login_count+1 WHERE username=?""",
                (now, account["username"]),
            )
            db.execute(
                "INSERT INTO login_events (username, logged_in_at) VALUES (?, ?)",
                (account["username"], now),
            )

    old_token = request.cookies.get(SESSION_COOKIE)
    if old_token:
        SESSIONS.pop(old_token, None)
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "username": account["username"],
        "role": account["access_role"],
        "display_name": account["display_name"],
        "profile_title": account["profile_title"],
        "login_time": datetime.now(timezone.utc).isoformat(),
        "expires_at": time.time() + SESSION_LIFETIME,
        "csrf_token": secrets.token_urlsafe(24),
    }
    destination = "admin_dashboard" if account["access_role"] == "admin" else "user_dashboard"
    response = make_response(redirect(url_for(destination)))
    response.set_cookie(
        SESSION_COOKIE, token, httponly=True, samesite="Lax",
        secure=COOKIE_SECURE, max_age=SESSION_LIFETIME, path="/",
    )
    return response


@app.route("/register", methods=["GET", "POST"])
def register():
    """New visitors may register as regular users, never as admins."""
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip().lower()
    display_name = request.form.get("display_name", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    error = None
    if not re.fullmatch(r"[a-z][a-z0-9_-]{2,31}", username):
        error = "Username: 3–32 letters, numbers, underscores or hyphens; start with a letter."
    elif not display_name or len(display_name) > 80:
        error = "Enter a display name (maximum 80 characters)."
    elif not 8 <= len(password) <= 128:
        error = "Password must contain 8–128 characters."
    elif password != confirm:
        error = "The passwords do not match."

    if error:
        return render_template("register.html", error=error, username=username, display_name=display_name), 400

    try:
        with closing(open_accounts_db()) as db:
            with db:
                db.execute(
                    """INSERT INTO users
                    (username, display_name, password_hash, access_role, profile_title, registered_at)
                    VALUES (?, ?, ?, 'user', 'Reader', ?)""",
                    (username, display_name, generate_password_hash(password), utc_now()),
                )
    except sqlite3.IntegrityError:
        return render_template(
            "register.html", error="That username is already registered.",
            username=username, display_name=display_name,
        ), 409
    return redirect(url_for("login", registered="1"))


@app.route("/dashboard")
def user_dashboard():
    """Display account facts and recent sign-ins for the current user."""
    user = current_user()
    if user is None:
        return redirect(url_for("login", required="1"))
    with closing(open_accounts_db()) as db:
        account = db.execute(
            """SELECT username, display_name, access_role, profile_title, registered_at,
               last_login_at, previous_login_at, login_count FROM users WHERE username=?""",
            (user["username"],),
        ).fetchone()
        activity = db.execute(
            "SELECT logged_in_at FROM login_events WHERE username=? ORDER BY id DESC LIMIT 5",
            (user["username"],),
        ).fetchall()
    with closing(open_bookmarks_db()) as db:
        bookmark_count = db.execute(
            "SELECT COUNT(*) FROM bookmarks WHERE username=?", (user["username"],)
        ).fetchone()[0]
    return render_template(
        "user_dashboard.html", account=account, activity=activity,
        bookmark_count=bookmark_count, username=user["username"], role=user["role"],
    )


@app.route("/admin")
def admin_dashboard():
    """Only administrators can see the account directory and sign-in events."""
    user = current_user()
    if user is None:
        return redirect(url_for("login", required="1"))
    if user["role"] != "admin":
        return render_template("access_denied.html", username=user["username"]), 403
    with closing(open_accounts_db()) as db:
        accounts = db.execute(
            """SELECT username, display_name, access_role, profile_title, registered_at,
                      last_login_at, login_count FROM users
               ORDER BY CASE WHEN access_role='admin' THEN 0 ELSE 1 END,
                        registered_at DESC, username"""
        ).fetchall()
        events = db.execute(
            """SELECT username, logged_in_at FROM login_events
               ORDER BY id DESC LIMIT 10"""
        ).fetchall()
        account_count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        admin_count = db.execute(
            "SELECT COUNT(*) FROM users WHERE access_role='admin'"
        ).fetchone()[0]
        login_count = db.execute("SELECT COUNT(*) FROM login_events").fetchone()[0]
        new_count = db.execute(
            "SELECT COUNT(*) FROM users WHERE registered_at >= ?",
            ((datetime.now(timezone.utc) - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S UTC"),),
        ).fetchone()[0]
        messages = db.execute(
            "SELECT id, name, email, message, submitted_at, status "
            "FROM contact_messages ORDER BY id DESC LIMIT 100"
        ).fetchall()
        message_count = db.execute("SELECT COUNT(*) FROM contact_messages").fetchone()[0]
        unread_count = db.execute(
            "SELECT COUNT(*) FROM contact_messages WHERE status='unread'"
        ).fetchone()[0]
    return render_template(
        "admin_dashboard.html", accounts=accounts, events=events,
        account_count=account_count, admin_count=admin_count,
        login_count=login_count, new_count=new_count,
        titles=PROFILE_TITLES, updated=request.args.get("updated"),
        messages=messages, message_count=message_count, unread_count=unread_count,
        message_action=request.args.get("message_action"),
        username=user["username"], role=user["role"],
    )


@app.route("/admin/users/<username>/update", methods=["POST"])
def update_user_profile(username):
    """Admin-only, CSRF-protected account-role and professional-title update."""
    user = current_user()
    if user is None:
        return redirect(url_for("login", required="1"))
    if user["role"] != "admin":
        return jsonify({"error": "Administrator access required."}), 403
    submitted = request.form.get("csrf_token", "")
    expected = user.get("csrf_token", "")
    if not submitted or not expected or not hmac.compare_digest(submitted, expected):
        return jsonify({"error": "Invalid security token. Refresh and try again."}), 403
    access_role = request.form.get("access_role", "")
    title = request.form.get("profile_title", "")
    if access_role not in ACCESS_ROLES or title not in PROFILE_TITLES:
        return jsonify({"error": "Invalid role or professional title."}), 400
    with closing(open_accounts_db()) as db:
        account = db.execute("SELECT username, access_role FROM users WHERE username=?", (username,)).fetchone()
        if account is None:
            return jsonify({"error": "Account not found."}), 404
        if account["username"].lower() == user["username"].lower() and access_role != "admin":
            return jsonify({"error": "You cannot remove your own administrator access."}), 400
        with db:
            db.execute(
                "UPDATE users SET access_role=?, profile_title=? WHERE username=?",
                (access_role, title, account["username"]),
            )
    # Immediately invalidate other users' sessions if privileges changed.
    if account["access_role"] != access_role:
        for session_token, session_data in list(SESSIONS.items()):
            if session_data["username"].lower() == account["username"].lower():
                SESSIONS.pop(session_token, None)
    return redirect(url_for("admin_dashboard", updated=account["username"]))


# Curated publisher links used when NewsAPI is unavailable; not fabricated incidents.
LOCAL_NEWS = [
    {"title": "Sample: CISA Cybersecurity Advisories", "source": "CISA",
     "url": "https://www.cisa.gov/news-events/cybersecurity-advisories"},
    {"title": "Sample: Cybersecurity News Headlines", "source": "The Hacker News",
     "url": "https://thehackernews.com/"},
    {"title": "Sample: Known Exploited Vulnerabilities", "source": "CISA",
     "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"},
]


# Curated public RSS feeds. No arbitrary URLs are accepted from browsers.
TRUSTED_RSS_FEEDS = (
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("SecurityWeek", "https://www.securityweek.com/feed/"),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
)
_headlines_lock = threading.Lock()
_headlines_cache = {"checked_at": 0.0, "items": [], "source_status": {}, "last_success": None}
MEDIA_NS = "{http://search.yahoo.com/mrss/}"
CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}"
ATOM_NS = "{http://www.w3.org/2005/Atom}"

class FeedImageParser(HTMLParser):
    """Read publisher-supplied images from feed HTML, not invented illustrations."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "img":
            return
        attributes = dict(attrs)
        for name in ("src", "data-src", "data-original"):
            if attributes.get(name):
                self.images.append(attributes[name])
                break

def valid_feed_image(url):
    if not isinstance(url, str):
        return None
    url = html.unescape(url.strip())
    try:
        parts = urlsplit(url)
        if parts.scheme == "https" and parts.hostname and not parts.username and not parts.password:
            return url[:2048]
    except ValueError:
        pass
    return None

def extract_feed_image(item):
    for tag in (MEDIA_NS + "thumbnail", MEDIA_NS + "content"):
        for element in item.findall(tag):
            src = valid_feed_image(element.attrib.get("url", ""))
            if src:
                return src
    for element in item.findall("enclosure"):
        if element.attrib.get("type", "").startswith("image/"):
            src = valid_feed_image(element.attrib.get("url", ""))
            if src:
                return src
    for field in (CONTENT_NS + "encoded", "description", ATOM_NS + "content", ATOM_NS + "summary"):
        snippet = item.findtext(field) or ""
        parser = FeedImageParser()
        parser.feed(snippet[:80000])
        for src in parser.images:
            parsed = valid_feed_image(src)
            if parsed:
                return parsed
    return None

# The RSS feed can omit a picture even when the article has a real cover.
# Article pages often advertise that cover through Open Graph metadata.
# Only visit links from the fixed publisher list; never accept arbitrary URLs.
PUBLISHER_ARTICLE_DOMAINS = {
    "The Hacker News": "thehackernews.com",
    "SecurityWeek": "securityweek.com",
    "BleepingComputer": "bleepingcomputer.com",
    "Krebs on Security": "krebsonsecurity.com",
}
_missing_cover_attempts = set()  # Avoid repeatedly probing pages with no usable preview.


class _NoArticleRedirects(HTTPRedirectHandler):
    """Don't follow redirects into an untrusted hostname/IP."""
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class ArticleImageMetaParser(HTMLParser):
    """Find an original preview image declared by the publisher."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.image = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        props = {str(key).lower(): value for key, value in attrs if key and value}
        tag_name = (props.get("property") or props.get("name") or "").strip().lower()
        if tag_name in {"og:image", "og:image:url", "og:image:secure_url", "twitter:image"}:
            candidate = props.get("content", "").strip()
            if candidate and not self.image:
                self.image = candidate


def is_trusted_publisher_article(source, url):
    expected = PUBLISHER_ARTICLE_DOMAINS.get(source)
    if not expected or not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        return (parts.scheme == "https" and not parts.username and not parts.password
                and parts.port in (None, 443)
                and (host == expected or host.endswith("." + expected)))
    except ValueError:
        return False


def read_publisher_image_metadata(story):
    """Small, bounded request for an image URL (no downloading image files)."""
    article_url = story.get("url", "")
    if not is_trusted_publisher_article(story.get("source"), article_url):
        return None
    try:
        req = Request(article_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; CyberNewsTracker/1.0; article preview)",
            "Accept": "text/html,application/xhtml+xml",
        })
        with build_opener(_NoArticleRedirects()).open(req, timeout=3.5) as response:
            mime = response.headers.get("Content-Type", "").lower()
            if "text/html" not in mime and "application/xhtml+xml" not in mime:
                return None
            html_head = response.read(250_000).decode("utf-8", errors="replace")
        parser = ArticleImageMetaParser()
        parser.feed(html_head)
        if not parser.image:
            return None
        # Publishers sometimes store the image path as /images/preview.jpg.
        return valid_feed_image(urljoin(article_url, parser.image))
    except Exception:
        # Some publishers block automated reading, and that is acceptable.
        return None


def _fetch_publisher_feed(pair):
    """Fetch one fixed publisher; return news and a safe diagnostic string."""
    publisher, rss_url = pair
    try:
        req = Request(rss_url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; CyberNewsTracker/1.0; public RSS reader)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        })
        with urlopen(req, timeout=6) as response:
            body = response.read(750_001)
        if len(body) > 750_000:
            return publisher, [], "Feed exceeded size limit"
        root = ET.fromstring(body)
        rss = root.findall(".//item")[:12]
        atom = root.findall(".//" + ATOM_NS + "entry")[:12] if not rss else []
        articles = []
        for entry in rss + atom:
            title = html.unescape((entry.findtext("title") or entry.findtext(ATOM_NS + "title") or "").strip())
            if entry in atom:
                link_node = next((x for x in entry.findall(ATOM_NS + "link") if x.attrib.get("rel", "alternate") == "alternate"), None)
                link = link_node.attrib.get("href", "") if link_node is not None else ""
                raw_date = entry.findtext(ATOM_NS + "published") or entry.findtext(ATOM_NS + "updated") or ""
            else:
                link = (entry.findtext("link") or "").strip()
                raw_date = (entry.findtext("pubDate") or "").strip()
            parts = urlsplit(link)
            if not title or parts.scheme != "https" or not parts.hostname:
                continue
            try:
                if "T" in raw_date and ("+" in raw_date or raw_date.endswith("Z")):
                    published = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                else:
                    published = parsedate_to_datetime(raw_date)
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
                published = published.astimezone(timezone.utc).isoformat()
            except (TypeError, ValueError, IndexError, OverflowError):
                published = ""
            articles.append({
                "title": title[:240], "source": publisher, "url": link,
                "published_at": published, "image_url": extract_feed_image(entry),
            })
        return publisher, articles, "OK" if articles else "No usable entries in feed"
    except Exception as exc:
        # Diagnostics identify the problem without exposing server internals.
        app.logger.warning("RSS fetch failed for %s: %s", publisher, type(exc).__name__)
        return publisher, [], f"Fetch failed ({type(exc).__name__})"

def read_trusted_headlines():
    """Read curated feeds concurrently; short backoff when all feeds fail."""
    with _headlines_lock:
        now = time.monotonic()
        cache_for = 900 if _headlines_cache["items"] else 30
        if now - _headlines_cache["checked_at"] < cache_for:
            return list(_headlines_cache["items"])
        with ThreadPoolExecutor(max_workers=len(TRUSTED_RSS_FEEDS)) as pool:
            fetched = list(pool.map(_fetch_publisher_feed, TRUSTED_RSS_FEEDS))
        items = []
        status = {}
        for publisher, stories, result in fetched:
            items.extend(stories)
            status[publisher] = {"state": result, "count": len(stories)}
        unique = {story["url"]: story for story in items}
        items = sorted(unique.values(), key=lambda story: story["published_at"], reverse=True)[:36]
        if items:
            # Reuse genuine cover URLs already saved in SQLite. This keeps RSS
            # refreshes fast and prevents unnecessary visits to publisher sites.
            with closing(open_accounts_db()) as db:
                saved = db.execute(
                    "SELECT url, image_url FROM rss_cache WHERE image_url IS NOT NULL"
                ).fetchall()
            saved_images = {row["url"]: valid_feed_image(row["image_url"]) for row in saved}
            for story in items:
                story["image_url"] = story["image_url"] or saved_images.get(story["url"])

            # Opt-out: set CYBERNEWS_FETCH_OG_IMAGES=0 to use RSS images only.
            # Cap metadata lookups per refresh; never download actual image files.
            if os.environ.get("CYBERNEWS_FETCH_OG_IMAGES", "1") == "1":
                candidates = [story for story in items
                    if not story["image_url"]
                    and story["url"] not in _missing_cover_attempts
                    and is_trusted_publisher_article(story["source"], story["url"])][:24]
                _missing_cover_attempts.update(story["url"] for story in candidates)
                if candidates:
                    with ThreadPoolExecutor(max_workers=8) as image_pool:
                        for story, cover in zip(candidates, image_pool.map(read_publisher_image_metadata, candidates)):
                            if cover:
                                story["image_url"] = cover
            _headlines_cache["items"] = items
            _headlines_cache["items"] = items[:36]
            success_time = datetime.now(timezone.utc).isoformat()
            _headlines_cache["last_success"] = success_time
            # Only genuine publisher stories enter the local cache.
            with closing(open_accounts_db()) as db:
                with db:
                    for story in _headlines_cache["items"]:
                        db.execute("""INSERT INTO rss_cache
                            (url, title, source, published_at, image_url, cached_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(url) DO UPDATE SET
                            title=excluded.title, source=excluded.source,
                            published_at=excluded.published_at,
                            image_url=COALESCE(excluded.image_url, rss_cache.image_url),
                            cached_at=excluded.cached_at""",
                            (story["url"], story["title"], story["source"],
                             story["published_at"], story["image_url"], success_time))
                    # Keep storage bounded for the local exercise.
                    db.execute("""DELETE FROM rss_cache WHERE url NOT IN
                        (SELECT url FROM rss_cache ORDER BY cached_at DESC, published_at DESC LIMIT 120)""")
        else:
            # A previously fetched article is still real, even if the internet is offline.
            with closing(open_accounts_db()) as db:
                cached = db.execute("""SELECT title, source, url, published_at, image_url
                    FROM rss_cache ORDER BY published_at DESC LIMIT 36""").fetchall()
                latest = db.execute("SELECT MAX(cached_at) FROM rss_cache").fetchone()[0]
            _headlines_cache["items"] = [dict(row) for row in cached]
            _headlines_cache["last_success"] = latest
        _headlines_cache["source_status"] = status
        _headlines_cache["checked_at"] = time.monotonic()
        return list(_headlines_cache["items"])


# ------------------------------------------
# OPTIONAL GOOGLE CLOUD TRANSLATION (EN -> DE)
# ------------------------------------------
# Set GOOGLE_TRANSLATE_API_KEY on the Flask SERVER only. Never place it in HTML/JS.
# API requests are batched, cached in SQLite, and rate-/character-limited to
# reduce unwanted Google Cloud charges. Only PUBLIC page text should be sent.
TRANSLATE_API_URL = "https://translation.googleapis.com/language/translate/v2"
TRANSLATE_LOCK = threading.Lock()
TRANSLATE_USAGE = {"date": "", "characters": 0, "requests": {}}
TRANSLATE_CHAR_BUDGET = 40000  # per day, per Flask process, for local use


def translate_text_google(texts):
    """Google Cloud Translation Basic v2; returns translations in input order."""
    key = os.environ.get("GOOGLE_TRANSLATE_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Google Cloud translation is not configured")
    body = json.dumps({"q": texts, "target": "de", "format": "text"}).encode("utf-8")
    google_request = Request(
        TRANSLATE_API_URL + "?" + urlencode({"key": key}),
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Accept": "application/json", "User-Agent": "CyberNewsTracker/1.0"},
        method="POST",
    )
    with urlopen(google_request, timeout=12) as response:
        result = json.load(response)
    translations = result.get("data", {}).get("translations", [])
    if len(translations) != len(texts):
        raise ValueError("Unexpected translation response")
    return [html.unescape(entry["translatedText"]) for entry in translations]


@app.route("/api/translate", methods=["POST"])
def translate_public_text():
    """Same-origin translation for public CyberNews interface and RSS copy."""
    # This paid API proxy is intended for local use. Do not expose publicly
    # without deployment-grade authentication, quotas, monitoring and controls.
    site = request.headers.get("Sec-Fetch-Site", "")
    if site and site not in {"same-origin", "none"}:
        return jsonify({"error": "Same-origin access required."}), 403
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        return jsonify({"error": "Invalid request origin."}), 403
    if not request.is_json:
        return jsonify({"error": "Expected JSON request."}), 415
    payload = request.get_json(silent=True)
    texts = payload.get("texts") if isinstance(payload, dict) else None
    if (not isinstance(texts, list) or not 1 <= len(texts) <= 40 or
            any(not isinstance(s, str) or not s.strip() or len(s) > 500 for s in texts) or
            sum(len(s) for s in texts) > 6000):
        return jsonify({"error": "Invalid translation batch."}), 400

    hashes = [hashlib.sha256(s.encode("utf-8")).hexdigest() for s in texts]
    with closing(open_accounts_db()) as db:
        cached = {}
        for hashed in set(hashes):
            row = db.execute(
                "SELECT translated_text FROM translation_cache WHERE input_hash=? AND target_language='de'",
                (hashed,),
            ).fetchone()
            if row:
                cached[hashed] = row["translated_text"]
    pending_hashes = list(dict.fromkeys(h for h in hashes if h not in cached))
    pending_texts = [texts[hashes.index(h)] for h in pending_hashes]

    if pending_texts:
        if not os.environ.get("GOOGLE_TRANSLATE_API_KEY", "").strip():
            return jsonify({"error": "Google Translation API key not configured on Flask server."}), 503
        now = time.time()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        visitor = request.remote_addr or "unknown"
        with TRANSLATE_LOCK:
            if TRANSLATE_USAGE["date"] != today:
                TRANSLATE_USAGE.update({"date": today, "characters": 0, "requests": {}})
            recent = [t for t in TRANSLATE_USAGE["requests"].get(visitor, []) if t > now - 900]
            required = sum(len(s) for s in pending_texts)
            if len(recent) >= 30 or TRANSLATE_USAGE["characters"] + required > TRANSLATE_CHAR_BUDGET:
                return jsonify({"error": "Translation rate or daily limit reached."}), 429
            TRANSLATE_USAGE["requests"][visitor] = recent + [now]
            # Reserve the characters even if Google fails, to bound outgoing usage.
            TRANSLATE_USAGE["characters"] += required
        try:
            translated = translate_text_google(pending_texts)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError,
                KeyError, TypeError, RuntimeError) as exc:
            app.logger.warning("Google translation failed: %s", type(exc).__name__)
            return jsonify({"error": "Google translation unavailable. Existing translations remain usable."}), 502
        with closing(open_accounts_db()) as db:
            with db:
                for hashed, result in zip(pending_hashes, translated):
                    cached[hashed] = result
                    db.execute(
                        "INSERT OR REPLACE INTO translation_cache "
                        "(input_hash, target_language, translated_text, created_at) VALUES (?, 'de', ?, ?)",
                        (hashed, result, utc_now()),
                    )
                db.execute("DELETE FROM translation_cache WHERE rowid NOT IN "
                           "(SELECT rowid FROM translation_cache ORDER BY rowid DESC LIMIT 5000)")

    response = jsonify({"translations": [cached[h] for h in hashes], "target": "de"})
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/api/headlines")
def homepage_headlines():
    return jsonify(read_trusted_headlines())

@app.route("/api/feed-status")
def feed_status():
    """Public diagnostics: publisher availability without showing private data."""
    read_trusted_headlines()
    return jsonify({
        "article_count": len(_headlines_cache["items"]),
        "last_success_utc": _headlines_cache["last_success"],
        "sources": _headlines_cache["source_status"],
        "using_cached_articles": bool(_headlines_cache["items"]) and not any(
            row["count"] > 0 for row in _headlines_cache["source_status"].values()),
    })

@app.route("/rss")
def public_rss():
    """Public XML syndication from our curated publisher feeds."""
    channel = ET.Element("channel")
    ET.SubElement(channel, "title").text = "CyberNews | Publisher Headlines"
    ET.SubElement(channel, "link").text = url_for("home", _external=True)
    ET.SubElement(channel, "description").text = "Links to original cybersecurity reporting."
    for story in read_trusted_headlines():
        entry = ET.SubElement(channel, "item")
        ET.SubElement(entry, "title").text = story["title"]
        ET.SubElement(entry, "link").text = story["url"]
        ET.SubElement(entry, "guid").text = story["url"]
        ET.SubElement(entry, "source").text = story["source"]
        if story["published_at"]:
            from email.utils import format_datetime
            ET.SubElement(entry, "pubDate").text = format_datetime(datetime.fromisoformat(story["published_at"]))
    root = ET.Element("rss", version="2.0")
    root.append(channel)
    return Response(ET.tostring(root, encoding="utf-8", xml_declaration=True),
                    mimetype="application/rss+xml")


@app.route("/news")
def news():
    """Reading is public; bookmarking still needs a signed-in account."""
    user = current_user()
    return render_template("news.html", username=user["username"] if user else None,
                           role=user["role"] if user else None)


@app.route("/api/news")
def api_news():
    """Return the same static JSON list even when NewsAPI is unavailable."""
    if current_user() is None:
        return jsonify({"error": "Login required."}), 401
    return jsonify(LOCAL_NEWS)


@app.route("/api/live-news")
def api_live_news():
    """Fetch NewsAPI server-side; never expose the API key to JavaScript."""
    if current_user() is None:
        return jsonify({"error": "Login required."}), 401

    api_key = os.getenv("NEWS_API_KEY", "").strip()
    if not api_key:
        return jsonify({"error": "Live news is not configured."}), 503

    query = urlencode({
        "q": "cybersecurity", "language": "en", "pageSize": 12,
    })
    url = "https://newsapi.org/v2/everything?" + query
    upstream_request = Request(
        url,
        headers={
            "X-Api-Key": api_key,
            "Accept": "application/json",
            "User-Agent": "CyberNewsTracker-Lab/1.0",
        },
    )

    try:
        with urlopen(upstream_request, timeout=8) as upstream_response:
            data = json.load(upstream_response)

        if not isinstance(data, dict) or data.get("status") != "ok":
            raise ValueError("Unexpected NewsAPI response")

        upstream_articles = data.get("articles")
        if not isinstance(upstream_articles, list):
            raise ValueError("Invalid article list")

        articles = []
        for item in upstream_articles:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            link = item.get("url")
            source = item.get("source") or {}
            source_name = source.get("name") if isinstance(source, dict) else None

            if not isinstance(link, str):
                continue
            parsed_url = urlsplit(link)
            if (not isinstance(title, str) or not title.strip()
                    or title == "[Removed]"
                    or parsed_url.scheme not in {"http", "https"}
                    or not parsed_url.netloc):
                continue

            articles.append({
                "title": title.strip(),
                "source": source_name if isinstance(source_name, str) and source_name else "Unknown source",
                "url": link,
            })

        if not articles:
            raise ValueError("No usable articles")

        return jsonify(articles)

    except (HTTPError, URLError, TimeoutError, OSError,
            ValueError, json.JSONDecodeError) as exc:
        app.logger.warning("NewsAPI unavailable (%s)", type(exc).__name__)
        return jsonify({"error": "Live news unavailable right now."}), 502



# ------------------------------------------
# PERSONAL BOOKMARKS (Flask + SQLite)
# ------------------------------------------

def open_bookmarks_db():
    """Open a local SQLite database and create the table if necessary."""
    connection = sqlite3.connect(BOOKMARKS_DB, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT NOT NULL,
            saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, url)
        )
    """)
    # Non-destructive migration: older saved bookmarks remain available.
    columns = {row[1] for row in connection.execute("PRAGMA table_info(bookmarks)")}
    for name in ("image_url", "published_at"):
        if name not in columns:
            connection.execute(f"ALTER TABLE bookmarks ADD COLUMN {name} TEXT")
    connection.commit()
    return connection


def bookmark_csrf_valid(user):
    supplied = request.headers.get("X-CSRF-Token", "")
    expected = user.get("csrf_token", "")
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))


@app.route("/bookmarks")
def bookmarks_page():
    user = current_user()
    if user is None:
        return redirect(url_for("login", required="1"))
    return render_template("bookmarks.html", username=user["username"])


@app.route("/api/bookmarks", methods=["GET", "POST", "DELETE"])
def bookmarks_api():
    user = current_user()
    if user is None:
        return jsonify({"error": "Please sign in to manage bookmarks."}), 401

    if request.method != "GET" and not bookmark_csrf_valid(user):
        return jsonify({"error": "Security token missing or invalid. Refresh the page."}), 403

    with closing(open_bookmarks_db()) as db:
        if request.method == "GET":
            rows = db.execute(
                "SELECT title, source, url, image_url, published_at, saved_at FROM bookmarks "
                "WHERE username = ? ORDER BY saved_at DESC, id DESC",
                (user["username"],),
            ).fetchall()
            return jsonify([dict(row) for row in rows])

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid JSON request."}), 400

        url = payload.get("url", "")
        if not isinstance(url, str):
            return jsonify({"error": "Invalid bookmark URL."}), 400
        url = url.strip()
        parsed = urlsplit(url)
        if (len(url) > 2048 or parsed.scheme not in {"http", "https"}
                or not parsed.netloc or parsed.username or parsed.password):
            return jsonify({"error": "Bookmark URLs must be valid HTTP(S) links."}), 400

        if request.method == "DELETE":
            with db:
                cursor = db.execute(
                    "DELETE FROM bookmarks WHERE username=? AND url=?",
                    (user["username"], url),
                )
            return jsonify({"success": True, "removed": cursor.rowcount > 0})

        title = payload.get("title", "")
        source = payload.get("source", "Unknown source")
        if not isinstance(title, str) or not title.strip():
            return jsonify({"error": "An article title is required."}), 400
        if not isinstance(source, str):
            source = "Unknown source"
        title, source = title.strip()[:250], (source.strip() or "Unknown source")[:100]
        image_url = valid_feed_image(payload.get("image_url"))
        published_at = payload.get("published_at")
        if not isinstance(published_at, str) or len(published_at) > 64:
            published_at = None
        with db:
            db.execute(
                """INSERT OR IGNORE INTO bookmarks
                (username, title, source, url, image_url, published_at)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (user["username"], title, source, url, image_url, published_at),
            )
        return jsonify({"success": True, "saved": True}), 201


# ------------------------------------------
# INTELLIGENCE DIVISION (PR)
# ------------------------------------------

@app.route("/intelligence")
def intelligence_page():
    """The page needs a login session, just like the other dashboards."""
    user = current_user()
    if user is None:
        return redirect(url_for("login", required="1"))
    return render_template(
        "intelligence.html", username=user["username"], role=user["role"]
    )


@app.route("/api/intelligence-feed")
def intelligence_feed():
    """Authorize ONLY by the bearer token; browser session is irrelevant."""
    authorization = request.headers.get("Authorization", "").strip()
    scheme, separator, token = authorization.partition(" ")

    if not separator or scheme.lower() != "bearer" or not token.strip():
        return jsonify({"error": "Missing or malformed Bearer token."}), 401

    token = token.strip()
    # Reject unexpected whitespace; one opaque token is expected.
    if any(character.isspace() for character in token):
        return jsonify({"error": "Invalid Bearer token format."}), 401

    identity = ACTIVE_TOKENS.get(token)
    if identity is None:
        return jsonify({"error": "Access Denied: Invalid token."}), 403

    role = identity["role"]
    if role == "admin":
        report = {
            "title": "Admin Security Intelligence Brief",
            "classification": "RESTRICTED (SIMULATED)",
            "summary": "Demo: Elevated alert volume across monitored systems.",
            "findings": [
                "Review authentication anomalies in the lab.",
                "Audit administrative access and permission changes.",
                "Verify incident response escalation contacts.",
            ],
        }
    elif role == "analyst":
        report = {
            "title": "Analyst Threat Intelligence Brief",
            "classification": "INTERNAL (SIMULATED)",
            "summary": "Demo: Phishing and suspicious login attempts require review.",
            "findings": [
                "Investigate simulated phishing indicators.",
                "Review suspicious login events in the lab.",
            ],
        }
    else:
        return jsonify({"error": "Access Denied: Unsupported role."}), 403

    return jsonify({
        "role": role,
        "issued_to": identity["username"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report": report,
    })


@app.route("/cookie_check")
def cookie_check():
    """Keep the previous Fort Knox HttpOnly-versus-JavaScript demo."""
    user = current_user()
    if user is None:
        return redirect(url_for("login", required="1"))
    response = make_response(render_template("cookie_check.html", username=user["username"]))
    response.set_cookie(
        "js_demo", "visible_to_javascript", httponly=False,
        samesite="Lax", secure=COOKIE_SECURE, path="/",
    )
    response.set_cookie(
        "http_only_demo", "hidden_from_javascript", httponly=True,
        samesite="Lax", secure=COOKIE_SECURE, path="/",
    )
    return response


@app.route("/session_info")
def session_info():
    user = current_user()
    if user is None:
        return jsonify({"logged_in": False}), 401
    return jsonify({
        "logged_in": True,
        "username": user["username"],
        "role": user["role"],
        "login_time": user["login_time"],
    })


@app.route("/logout", methods=["POST"])
def logout():
    user = current_user()
    submitted = request.form.get("csrf_token", "")
    expected = user.get("csrf_token", "") if user else ""
    if not submitted or not expected or not hmac.compare_digest(submitted, expected):
        return jsonify({"error": "Invalid logout security token."}), 403
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        SESSIONS.pop(token, None)
    response = make_response(redirect(url_for("login")))
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=COOKIE_SECURE,
        samesite="Lax", httponly=True,
    )
    response.delete_cookie("js_demo", path="/")
    response.delete_cookie("http_only_demo", path="/", httponly=True)
    return response


# Contact CSRF uses an unpredictable cookie token rather than a login session.
# This works for anonymous visitors and doesn't expose login-session tokens.
CONTACT_CSRF_COOKIE = "cybernews_contact_csrf"
CONTACT_TOKEN_MAX_AGE = 60 * 60
CONTACT_SUBMISSION_MAX = 100_000


def contact_form_response(error=None, name="", email="", message="", status=200):
    token = secrets.token_urlsafe(32)
    response = make_response(render_template(
        "contact_form.html", form_csrf_token=token, form_error=error,
        name=name, email=email, message=message,
    ), status)
    response.set_cookie(
        CONTACT_CSRF_COOKIE, token, max_age=CONTACT_TOKEN_MAX_AGE,
        httponly=True, samesite="Lax", secure=COOKIE_SECURE, path="/",
    )
    return response


@app.route("/contact", methods=["GET"])
def contact():
    return contact_form_response()


@app.route("/submit-message", methods=["POST"])
def submit_message():
    if request.content_length is not None and request.content_length > CONTACT_SUBMISSION_MAX:
        return contact_form_response("Message request is too large.", status=413)

    form_token = request.form.get("contact_csrf_token", "")
    cookie_token = request.cookies.get(CONTACT_CSRF_COOKIE, "")
    if not form_token or not cookie_token or not hmac.compare_digest(form_token, cookie_token):
        return contact_form_response("Form expired. Please try sending your message again.", status=403)

    # Hidden field deters simple automated spam submissions. No message is stored.
    if request.form.get("website", "").strip():
        return contact_form_response("Unable to submit the message.", status=400)

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    if not (2 <= len(name) <= 100):
        error = "Enter your name (2–100 characters)."
    elif not (3 <= len(email) <= 254) or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        error = "Enter a valid email address."
    elif not (5 <= len(message) <= 5000):
        error = "Message must be 5–5000 characters."
    else:
        error = None
    if error:
        return contact_form_response(error, name, email, message, status=400)

    with closing(open_accounts_db()) as db:
        with db:
            db.execute(
                "INSERT INTO contact_messages (name, email, message, submitted_at) "
                "VALUES (?, ?, ?, ?)", (name, email, message, utc_now()),
            )
    response = make_response(render_template(
        "confirmation.html", name=name, email=email, message=message,
    ))
    # Prevent a browser refresh from creating the same message a second time.
    response.delete_cookie(
        CONTACT_CSRF_COOKIE, path="/", secure=COOKIE_SECURE,
        samesite="Lax", httponly=True,
    )
    return response


@app.route("/admin/messages/<int:message_id>/<action>", methods=["POST"])
def admin_contact_message(message_id, action):
    """Only signed-in administrators may mark or delete contact messages."""
    user = current_user()
    if user is None:
        return redirect(url_for("login", required="1"))
    if user["role"] != "admin":
        return render_template("access_denied.html", username=user["username"]), 403
    submitted = request.form.get("csrf_token", "")
    expected = user.get("csrf_token", "")
    if not submitted or not expected or not hmac.compare_digest(submitted, expected):
        return jsonify({"error": "Invalid security token. Reload the page."}), 403
    if action not in ("read", "unread", "delete"):
        return jsonify({"error": "Unknown message action."}), 400
    with closing(open_accounts_db()) as db:
        with db:
            if action == "delete":
                db.execute("DELETE FROM contact_messages WHERE id=?", (message_id,))
            else:
                db.execute(
                    "UPDATE contact_messages SET status=? WHERE id=?",
                    (action, message_id),
                )
    return redirect(url_for("admin_dashboard", message_action=action) + "#contact-messages", code=303)


if __name__ == "__main__":
    # Development server for local exercises only. Never expose debug mode publicly.
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=5000)
