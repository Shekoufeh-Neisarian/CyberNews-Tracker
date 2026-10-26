
/* =========================================
   CyberNews Tracker
   Main JavaScript
   ========================================= */



/* =========================================
   Cookie preferences + theme (real-world practice)
   Essential session cookies are created by Flask only after login.
   The optional theme cookie is set ONLY after opt-in.
   ========================================= */
function readCyberCookie(name) {
    return document.cookie.split(";").map(p => p.trim())
        .find(p => p.startsWith(name + "="))?.slice(name.length + 1) || "";
}
function writeCyberCookie(name, value, maxAge = 15552000) {
    const secure = location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${name}=${value}; Path=/; Max-Age=${maxAge}; SameSite=Lax${secure}`;
}
const themeButton = document.getElementById("theme-toggle");
const cookieBanner = document.getElementById("cookieConsent");
const preferenceCheckbox = document.getElementById("themeCookieOptIn");
const cookieSettings = document.getElementById("cookieSettingsButton");
let cookieConsent = readCyberCookie("cybernews_consent");
if (!['essential', 'preferences'].includes(cookieConsent)) cookieConsent = '';

// Older classroom versions used localStorage. Remove that legacy preference;
// future persistence is controlled by the optional cookie choice.
try { localStorage.removeItem("cybernews-theme"); } catch (_) { /* ignore */ }

function updateThemeButton() {
    if (!themeButton) return;
    const dark = document.documentElement.classList.contains("dark-theme");
    themeButton.textContent = dark ? "☀" : "☾";
    themeButton.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
    themeButton.setAttribute("aria-pressed", String(dark));
}
updateThemeButton();
if (themeButton) themeButton.addEventListener("click", () => {
    const dark = document.documentElement.classList.toggle("dark-theme");
    if (cookieConsent === "preferences") {
        writeCyberCookie("cybernews_theme", dark ? "dark" : "light");
    }
    updateThemeButton();
});
function showCookieChoices() {
    if (!cookieBanner) return;
    cookieBanner.hidden = false;
    if (preferenceCheckbox) preferenceCheckbox.checked = cookieConsent === "preferences";
}
function saveCookieChoices(allowPreference) {
    cookieConsent = allowPreference ? "preferences" : "essential";
    writeCyberCookie("cybernews_consent", cookieConsent);
    if (allowPreference) {
        writeCyberCookie("cybernews_theme", document.documentElement.classList.contains("dark-theme") ? "dark" : "light");
    } else {
        writeCyberCookie("cybernews_theme", "", 0); // Delete optional cookie.
    }
    if (cookieBanner) cookieBanner.hidden = true;
}
if (!cookieConsent) showCookieChoices();
if (cookieSettings) cookieSettings.addEventListener("click", showCookieChoices);
document.getElementById("essentialCookiesButton")?.addEventListener("click", () => saveCookieChoices(false));
document.getElementById("saveCookieChoiceButton")?.addEventListener("click", () => saveCookieChoices(Boolean(preferenceCheckbox?.checked)));

/* =========================================
   Publisher news dates + account dates
   RSS timestamps are UTC; display explicitly in Europe/Berlin.
   ========================================= */
function berlinTimestamp(value) {
    if (!value || typeof value !== "string") return "Publication date unavailable";
    let iso = value.trim();
    if (iso.endsWith(" UTC")) iso = iso.slice(0, -4).replace(" ", "T") + "Z";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "Publication date unavailable";
    return new Intl.DateTimeFormat("en-GB", {
        timeZone: "Europe/Berlin", day: "numeric", month: "short",
        year: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short"
    }).format(date);
}
for (const element of document.querySelectorAll("time.berlin-datetime[data-utc]")) {
    const time = berlinTimestamp(element.dataset.utc);
    if (time !== "Publication date unavailable") {
        element.textContent = time;
        element.title = "Europe/Berlin time";
    }
}

/* =========================================
   Homepage: publisher RSS editorial feed.
   Never fake breaking headlines or images.
   ========================================= */
const homeRefreshButton = document.getElementById("refreshButton");
const featuredStory = document.getElementById("featuredStory");
const homeWireFeed = document.getElementById("homeWireFeed");
const homeStoryGrid = document.getElementById("homeStoryGrid");
const homeNewsStatus = document.getElementById("homeNewsStatus");

function publisherImage(story, className, eager = false) {
    const frame = document.createElement("div");
    frame.className = `publisher-photo ${className}`;
    const placeholder = document.createElement("div");
    placeholder.className = "publisher-photo-fallback";
    placeholder.textContent = "PUBLISHER IMAGE NOT PROVIDED";
    frame.appendChild(placeholder);
    const url = safeArticleUrl(story.image_url);
    if (url && url.startsWith("https://")) {
        const photo = document.createElement("img");
        photo.src = url;
        photo.alt = `Publisher image for ${story.title || "this news article"}`;
        photo.loading = eager ? "eager" : "lazy";
        photo.decoding = "async";
        photo.referrerPolicy = "no-referrer";
        photo.addEventListener("load", () => placeholder.hidden = true);
        photo.addEventListener("error", () => photo.remove());
        frame.appendChild(photo);
    }
    return frame;
}
function textElement(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value;
    return element;
}
function publisherLink(story, className = "") {
    const link = document.createElement("a");
    link.className = className;
    link.textContent = story.title || "Publisher article";
    link.href = safeArticleUrl(story.url) || "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
}
function renderHomePublisherStories(stories) {
    if (!featuredStory || !homeWireFeed || !homeStoryGrid) return;
    featuredStory.replaceChildren();
    homeWireFeed.replaceChildren();
    homeStoryGrid.replaceChildren();
    const lead = stories[0];
    const cover = publisherImage(lead, "lead-photo", true);
    const content = document.createElement("div");
    content.className = "editorial-lead-caption";
    content.append(
        textElement("span", "editorial-story-kicker", `${lead.source} · FEATURED`),
        publisherLink(lead, "editorial-lead-title"),
        textElement("p", "editorial-lead-date", `Published ${berlinTimestamp(lead.published_at)}`)
    );
    featuredStory.append(cover, content);
    for (const story of stories.slice(1, 6)) {
        const item = document.createElement("article");
        item.className = "wire-item";
        item.append(
            textElement("span", "wire-item-meta", `${story.source} · ${berlinTimestamp(story.published_at)}`),
            publisherLink(story, "wire-item-title")
        );
        homeWireFeed.appendChild(item);
    }
    for (const story of stories.slice(6, 12)) {
        const card = document.createElement("article");
        card.className = "editorial-small-card";
        card.append(
            publisherImage(story, "small-photo"),
            textElement("div", "editorial-small-source", story.source),
            publisherLink(story, "editorial-small-title"),
            textElement("p", "editorial-small-date", `Published ${berlinTimestamp(story.published_at)}`)
        );
        homeStoryGrid.appendChild(card);
    }
}
if (homeRefreshButton && featuredStory && homeWireFeed && homeStoryGrid) {
    async function loadHomeHeadlines() {
        homeRefreshButton.disabled = true;
        if (homeNewsStatus) homeNewsStatus.textContent = "Checking publisher RSS feeds…";
        try {
            const response = await fetch("/api/headlines", { cache: "no-store" });
            if (!response.ok) throw new Error("Publisher RSS unavailable");
            const stories = await response.json();
            if (!Array.isArray(stories) || stories.length === 0) throw new Error("No articles available");
            renderHomePublisherStories(stories);
            if (homeNewsStatus) homeNewsStatus.textContent = `${stories.length} publisher headlines · Images shown when included by the source · Dates in Berlin time`;
        } catch (error) {
            featuredStory.replaceChildren(textElement("p", "editorial-feed-error", "Publisher feeds are temporarily unavailable. Check Feed Status or read the original sources below."));
            homeWireFeed.replaceChildren();
            homeStoryGrid.replaceChildren();
            if (homeNewsStatus) homeNewsStatus.textContent = "Sources: The Hacker News · SecurityWeek · BleepingComputer · Krebs on Security. Feed status: /api/feed-status";
        } finally { homeRefreshButton.disabled = false; }
    }
    homeRefreshButton.addEventListener("click", loadHomeHeadlines);
    loadHomeHeadlines();
}

/* Fort Knox Cookies (PR): demonstrate JavaScript-visible cookies.
   This runs on /cookie_check only; HttpOnly values never appear here. */
const cookieOutput = document.getElementById("cookieOutput");
if (cookieOutput) {
    const visibleCookies = document.cookie;
    cookieOutput.textContent = visibleCookies || "(No JavaScript-readable cookies found)";
    console.log("JavaScript-visible cookies:", visibleCookies);
}


/* =========================================
   Article search, category filters, and personal bookmarks.
   Bookmark changes go to Flask + SQLite (not localStorage).
   ========================================= */
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
const liveNewsList = document.querySelector("ul#headlinesContainer");
const liveNewsButton = document.getElementById("liveNewsRefreshButton");
const liveNewsStatus = document.getElementById("newsStatus");
const newsSearchInput = document.getElementById("newsSearchInput");
const newsFilters = document.getElementById("newsCategoryFilters");
const newsCount = document.getElementById("newsResultsCount");
const newsEmpty = document.getElementById("newsEmptyState");

async function bookmarkRequest(method = "GET", data = null) {
    const options = {
        method,
        credentials: "same-origin",
        headers: { "Accept": "application/json" },
        cache: "no-store"
    };
    if (method !== "GET") {
        options.headers["Content-Type"] = "application/json";
        options.headers["X-CSRF-Token"] = csrfToken;
        options.body = JSON.stringify(data);
    }
    const response = await fetch("/api/bookmarks", options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    return result;
}
function categoryForStory(article) {
    const s = String(article.title || "").toLowerCase();
    if (/cve-|zero.day|vulnerabilit|exploit|patch|security flaw/.test(s)) return "vulnerabilities";
    if (/ransomware|extortion|encrypted files/.test(s)) return "ransomware";
    if (/malware|trojan|botnet|worm|backdoor|loader/.test(s)) return "malware";
    if (/breach|data leak|stolen data|exposed record/.test(s)) return "breaches";
    if (/\bai\b|artificial intelligence|llm|chatgpt|machine learning/.test(s)) return "ai";
    return "general";
}
function safeArticleUrl(value) {
    if (typeof value !== "string") return null;
    try {
        const u = new URL(value);
        return ["http:", "https:"].includes(u.protocol) ? u.href : null;
    } catch (_) { return null; }
}
function makeArticleCard(article, saved, removeMode = false) {
    const card = document.createElement("li");
    card.className = "news-card explore-story-card";
    card.dataset.category = categoryForStory(article);
    card.dataset.search = `${article.title || ""} ${article.source || ""}`.toLowerCase();
    const top = document.createElement("div");
    top.className = "story-card-top";
    const source = document.createElement("span");
    source.className = "story-source";
    source.textContent = article.source || "Unknown source";
    const category = document.createElement("span");
    category.className = "story-category";
    category.textContent = card.dataset.category === "general" ? "CYBERNEWS" : card.dataset.category.toUpperCase();
    top.append(source, category);
    const title = document.createElement("h3");
    const validUrl = safeArticleUrl(article.url);
    if (validUrl) {
        const link = document.createElement("a");
        link.href = validUrl;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = article.title || "Untitled article";
        title.appendChild(link);
    } else title.textContent = article.title || "Untitled article";
    const image = publisherImage(article, "news-card-photo");
    const dateInfo = textElement("p", "news-card-published",
        article.published_at ? `Published ${berlinTimestamp(article.published_at)}` : "Publication date unavailable");
    const footer = document.createElement("div");
    footer.className = "story-card-foot";
    const sourceNote = document.createElement("span");
    sourceNote.textContent = "Read original story ↗";
    const button = document.createElement("button");
    button.type = "button";
    button.className = "story-save-button";
    button.textContent = removeMode ? "★ Remove" : saved ? "★ Saved" : "☆ Save";
    button.setAttribute("aria-label", removeMode ? "Remove bookmark" : saved ? "Remove from saved articles" : "Save this article");
    button.disabled = !validUrl;
    button.dataset.saved = String(saved);
    button.addEventListener("click", async () => {
        if (!validUrl || button.disabled) return;
        button.disabled = true;
        try {
            const currentlySaved = button.dataset.saved === "true";
            await bookmarkRequest(currentlySaved ? "DELETE" : "POST", {
                url: validUrl,
                title: article.title,
                source: article.source,
                image_url: article.image_url || null,
                published_at: article.published_at || null
            });
            const nowSaved = !currentlySaved;
            button.dataset.saved = String(nowSaved);
            if (removeMode) {
                card.remove();
                window.dispatchEvent(new Event("bookmarks-changed"));
            } else {
                button.textContent = nowSaved ? "★ Saved" : "☆ Save";
                button.setAttribute("aria-label", nowSaved ? "Remove from saved articles" : "Save this article");
            }
        } catch (error) {
            if (error.message.includes("401") || error.message.includes("Login")) {
                if (confirm("Please sign in to save articles. Open sign-in page?")) {
                    location.href = "/login?required=1";
                }
            } else {
                alert("Could not update bookmark: " + error.message);
            }
        } finally { button.disabled = false; }
    });
    footer.append(sourceNote, button);
    card.append(image, top, title, dateInfo, footer);
    return card;
}

if (liveNewsList && liveNewsButton && liveNewsStatus) {
    let currentStories = [];
    let selectedCategory = "all";
    let savedUrls = new Set();
    // If reading saved bookmarks fails, the feed still loads normally.
    bookmarkRequest().then(rows => {
        savedUrls = new Set(rows.map(x => x.url));
        if (currentStories.length) renderStories(currentStories);
    }).catch(err => console.warn("Saved article status unavailable:", err));

    function applyNewsFilters() {
        const query = (newsSearchInput?.value || "").trim().toLowerCase();
        let visible = 0;
        for (const card of liveNewsList.children) {
            const matches = card.dataset.search.includes(query) &&
                (selectedCategory === "all" || selectedCategory === card.dataset.category);
            card.hidden = !matches;
            if (matches) visible++;
        }
        if (newsCount) newsCount.textContent = `${visible} of ${currentStories.length} stories`;
        if (newsEmpty) newsEmpty.hidden = visible !== 0;
    }
    function renderStories(articles) {
        currentStories = articles;
        liveNewsList.replaceChildren(...articles.map(a =>
            makeArticleCard(a, savedUrls.has(safeArticleUrl(a.url)))
        ));
        applyNewsFilters();
    }
    async function fetchStories(endpoint) {
        const response = await fetch(endpoint, {
            credentials: "same-origin", headers: { Accept: "application/json" }, cache: "no-store"
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        if (!Array.isArray(result) || !result.length) throw new Error("No articles found");
        return result;
    }
    async function showLocalNews(fallback = false) {
        // A real newsroom should not fabricate sample reports when RSS is offline.
        currentStories = [];
        liveNewsList.replaceChildren();
        liveNewsStatus.textContent = "Publisher feeds are unavailable. Check /api/feed-status for the source errors, then try Refresh RSS.";
        if (newsCount) newsCount.textContent = "0 stories";
    }
    async function showPublisherNews() {
        try {
            const articles = await fetchStories("/api/headlines");
            renderStories(articles);
            liveNewsStatus.textContent = `Showing ${articles.length} headlines from verified publisher RSS endpoints. Dates are displayed in Berlin time.`;
        } catch (error) {
            console.warn("Publisher RSS unavailable", error);
            await showLocalNews(true);
        }
    }
    liveNewsButton.addEventListener("click", async () => {
        liveNewsButton.disabled = true;
        liveNewsStatus.textContent = "Refreshing publisher RSS headlines…";
        try { await showPublisherNews(); }
        finally { liveNewsButton.disabled = false; }
    });
    if (newsSearchInput) newsSearchInput.addEventListener("input", applyNewsFilters);
    if (newsFilters) newsFilters.addEventListener("click", event => {
        const button = event.target.closest("button[data-category]");
        if (!button) return;
        selectedCategory = button.dataset.category;
        newsFilters.querySelectorAll("button[data-category]").forEach(item => {
            const active = item === button;
            item.classList.toggle("active", active);
            item.setAttribute("aria-pressed", String(active));
        });
        applyNewsFilters();
    });
    showPublisherNews();
}

/* Personal bookmark library: searchable without reloading. */
const bookmarksContainer = document.getElementById("bookmarksContainer");
if (bookmarksContainer) {
    const bookmarksSearch = document.getElementById("bookmarkSearchInput");
    const bookmarksStatus = document.getElementById("bookmarkStatus");
    const bookmarksEmpty = document.getElementById("bookmarksEmpty");
    const bookmarksCount = document.getElementById("bookmarkCount");
    let allBookmarks = [];
    function renderBookmarks() {
        const q = (bookmarksSearch?.value || "").trim().toLowerCase();
        const matched = allBookmarks.filter(row =>
            `${row.title} ${row.source}`.toLowerCase().includes(q));
        bookmarksContainer.replaceChildren(...matched.map(row =>
            makeArticleCard(row, true, true)));
        if (bookmarksCount) bookmarksCount.textContent =
            `${matched.length} of ${allBookmarks.length} saved`;
        if (bookmarksEmpty) {
            bookmarksEmpty.hidden = matched.length !== 0;
            const heading = bookmarksEmpty.querySelector("h2");
            if (heading) heading.textContent = allBookmarks.length && q
                ? "Nothing matches your search." : "No saved articles here yet.";
        }
    }
    async function loadBookmarks() {
        try {
            allBookmarks = await bookmarkRequest();
            if (bookmarksStatus) bookmarksStatus.textContent = "";
            renderBookmarks();
        } catch (error) {
            if (bookmarksStatus) bookmarksStatus.textContent = "Could not load bookmarks: " + error.message;
        }
    }
    window.addEventListener("bookmarks-changed", loadBookmarks);
    bookmarksSearch?.addEventListener("input", renderBookmarks);
    loadBookmarks();
}


/* =========================================
   Final polish: Reading progress + genuine RSS headline ticker.
   Use only the publisher-driven /api/headlines endpoint.
   No imaginary breaking stories; cached on the Flask server.
   ========================================= */
(function () {
    'use strict';
    const progress = document.getElementById('readingProgress');
    if (progress) {
        let pending = false;
        const update = () => {
            const documentHeight = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
            const viewport = window.innerHeight;
            const scrollable = documentHeight - viewport;
            const amount = scrollable > 0 ? Math.max(0, Math.min(100, window.scrollY / scrollable * 100)) : 0;
            progress.style.width = amount.toFixed(2) + '%';
            pending = false;
        };
        window.addEventListener('scroll', () => {
            if (!pending) { pending = true; requestAnimationFrame(update); }
        }, {passive: true});
        window.addEventListener('resize', update);
        window.addEventListener('load', update);
        update();
    }

    const ticker = document.getElementById('liveHeadlineTicker');
    if (!ticker) return;
    const setMessage = (message) => {
        ticker.classList.remove('is-scrolling');
        ticker.replaceChildren();
        const fallback = document.createElement('span');
        fallback.className = 'ticker-placeholder';
        fallback.textContent = message;
        ticker.appendChild(fallback);
    };
    function refreshTickerHeadlines() {
    fetch('/api/headlines', {headers: {'Accept': 'application/json'}, cache: 'no-store'})
        .then(response => {
            if (!response.ok) throw new Error('Publisher feed unavailable');
            return response.json();
        })
        .then(stories => {
            if (!Array.isArray(stories) || !stories.length) throw new Error('No stories');
            const group = document.createElement('div');
            group.className = 'ticker-story-group';
            let usable = 0;
            for (const story of stories.slice(0, 8)) {
                const url = typeof safeArticleUrl === 'function' ? safeArticleUrl(story.url) : null;
                if (!url || !story.title) continue;
                const link = document.createElement('a');
                link.href = url;
                link.target = '_blank';
                link.rel = 'noopener noreferrer';
                link.className = 'ticker-story';
                const source = document.createElement('span');
                source.className = 'ticker-story-source';
                source.textContent = story.source || 'Publisher';
                const headline = document.createElement('span');
                headline.className = 'ticker-story-title';
                headline.textContent = story.title;
                link.append(source, headline);
                group.appendChild(link);
                usable++;
            }
            if (!usable) throw new Error('No usable stories');
            // Duplicated text is visual-only so screen readers / keyboard users
            // encounter each publisher link just once.
            const repeat = group.cloneNode(true);
            repeat.setAttribute('aria-hidden', 'true');
            for (const node of repeat.querySelectorAll('a')) {
                node.removeAttribute('href');
                node.removeAttribute('target');
                node.setAttribute('tabindex', '-1');
            }
            ticker.replaceChildren(group, repeat);
            ticker.classList.add('is-scrolling');
        })
        .catch(() => setMessage('Publisher headlines temporarily unavailable'));
    }
    refreshTickerHeadlines();
    // RSS data is cached for 15 minutes on the Flask server.
    window.setInterval(refreshTickerHeadlines, 15 * 60 * 1000);
})();
