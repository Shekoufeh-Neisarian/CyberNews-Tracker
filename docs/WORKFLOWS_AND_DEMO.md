# CyberNews — workflows and demo guide

**Developed by Shekoufeh Neisarian**

This guide explains exactly what the browser, Flask server, and SQLite database do when a user interacts with the website. Use it as speaker notes for a short presentation.

## Architecture: four main parts

1. **Browser** — Displays Jinja-generated HTML and uses CSS and JavaScript for styling and interaction.
2. **Flask (`web\_app.py`)** — Serves pages/APIs, authenticates, validates forms, handles RSS, processes messages, and calls translation service.
3. **SQLite (`cybernews\_bookmarks.db`)** — Persists user accounts, login history, bookmarks, Contact messages, and caches.
4. **Publisher sites and Google Cloud** — Supply news/preview images and optional German translation of public news text.

!\[Architecture infographic](architecture-and-features.png)

## Workflow A — News and publisher images

```text
Publisher RSS XML → Flask parses article metadata → cache → browser cards/ticker
                                         ↘ if image is missing: check publisher og:image
```

* **RSS** = an XML format publishers offer for updates. We read selected cybersecurity publisher feeds, not an arbitrary internet search.
* **Article metadata** = headline, source, publication date, article URL and optional preview image URL.
* **Search and filters** = JavaScript compares text/category keywords against already loaded headlines; no external search credentials required.
* **Original report** = the user follows the publisher URL to read the full article.
* **Refresh** = reloads the current feed response; a 15-minute cache limits repeat publisher requests.

## Workflow B — Registration, login and bookmarks

```text
Register → validate input → hash password → SQLite users
Sign in → verify hash → issue random session cookie → server checks session
Save story → check logged-in user → SQLite bookmarks → My Bookmarks
```

* `user` / `admin` are permission levels; professional titles such as Student and Researcher are descriptive labels.
* Login events and login totals are recorded in SQLite and shown in dashboards.
* Session cookie: random identifier, `HttpOnly` and `SameSite=Lax`; its server-side session entry is stored in Python memory.
* Bookmark ownership comes from the authenticated account, not from user-supplied query text.

## Workflow C — Contact form and administrator inbox

```text
Visitor enters name + email + message
            ↓
Flask validates fields and checks CSRF token
            ↓
INSERT contact\_messages (status='unread', submitted\_at=UTC)
            ↓
Confirmation page
            ↓
Admin Console → Contact Inbox → Mark read / unread / Delete
```

* **Validation** rejects missing/overlong/incorrectly formatted fields before storing them.
* **CSRF token** reduces the risk of an unrelated website submitting forms on a visitor's behalf.
* **Parameterized SQL** inserts the message without concatenating visitor text into SQL commands.
* **HTML escaping** avoids rendering visitor-supplied message text as executable markup.
* **Access control** ensures only administrators can view/manage the inbox.
* **No email delivery** is needed for this workflow: messages are stored in the project's local database.

## Workflow D — EN/DE display and Google Translation API

```text
EN/DE toggle → built-in UI translations
           ↘ dynamic public news text → Flask /api/translate
                                     → Google Translation Basic v2
                                     → SQLite translation cache
                                     → German text displayed
```

* The Google API key is set in the server environment, not included in frontend JavaScript.
* Cached translations reduce repeat requests.
* Clicking EN returns the interface to its original English display.
* The Google Cloud free-trial screenshot, if shown separately, represents the trial state at capture time; it is not a claim that the API is permanently free.

## Workflow E — Cookie and theme choices

* **Essential cookies** support login and required application functionality.
* **Optional preferences** can remember the theme when users consent.
* The latest theme fix remembers an explicit theme selection within the current tab using `sessionStorage` if optional cookies are declined.
* The colorful pink → purple → blue → turquoise → mint progress line indicates current scroll position. JavaScript updates its width, CSS provides the gradient.
* The top headline ticker is a separate feature; it scrolls publisher news headlines, not page progress.

## Short live demo (about 7 minutes)

|Step|Show in the browser|What to explain|
|-|-|-|
|1|Home|RSS news summaries, latest highlights and ticker.|
|2|Latest News|Search/filter, publisher image and article link.|
|3|EN / DE|Static UI translation vs external translation of changing news.|
|4|Theme, cookie settings, scroll|User preferences and visual feedback line.|
|5|Sign in and bookmarks|Password hashes, user-specific bookmarks, SQLite.|
|6|Contact|Submit a **fictional** name/email/message and see confirmation.|
|7|Admin Console|View inbox entry, mark read/unread, optionally delete; show user roles/titles/login counts.|
|8|DB Browser / source|`contact\_messages`, `users`, `bookmarks`, route handlers in `web\_app.py`.|

### Suggested contact demo data

Use a clearly fictional entry (for example, **Demo Visitor**, `demo@example.com`, "Please check the link to this article"). Do not upload real visitors' contact details to GitHub or include their data in screenshots.

## Quick answers

**Why Flask?** It links browser requests to Python operations, handles routes, and returns rendered HTML or JSON.

**Why SQLite?** It is a lightweight relational database that works locally with Python and needs no external DB server.

**Why RSS instead of manually entering every story?** The feeds provide continuously updated cybersecurity article metadata from publishers.

**Where do Contact messages go?** Into SQLite `contact\_messages`; authorized admins see them in the Admin Console.

**Is the preview image saved in SQLite?** The *URL* can be cached; the publisher's remote image remains hosted externally.

**Why cookie consent?** A login cookie is needed for authentication; optional theme preference storage follows the visitor's choice.

