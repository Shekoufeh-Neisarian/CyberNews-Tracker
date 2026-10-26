/* CyberNews English / Deutsch switch.
   Language is stored temporarily in sessionStorage (not in a cookie).
   RSS publishers' original headlines remain in their published language.
   Existing Flask routes, security/session cookies and RSS APIs are unchanged. */
(() => {
    "use strict";
    const KEY = "cybernews-language";
    const german = {
        // Header, navigation, footer
        "RSS NEWSWIRE": "RSS-NACHRICHTEN",
        "LATEST HEADLINES": "NEUESTE SCHLAGZEILEN",
        "All news": "Alle Meldungen",
        "Connecting to publisher feeds…": "Verbindung zu den Nachrichtenquellen …",
        "Publisher headlines temporarily unavailable": "Schlagzeilen momentan nicht verfügbar",
        "Browse latest news": "Neueste Meldungen",
        "TRACKER": "TRACKER",
        "Home": "Startseite", "Latest News": "Aktuelles", "Search": "Suche",
        "Bookmarks": "Lesezeichen", "My Account": "Mein Konto",
        "Admin Console": "Verwaltung", "Contact": "Kontakt",
        "Join": "Registrieren", "Sign in": "Anmelden", "Sign out": "Abmelden",
        "Log out": "Abmelden", "Member": "Mitglied", "MEMBER": "MITGLIED",
        "Administrator": "Administrator", "ADMINISTRATOR": "ADMINISTRATOR",
        "Teaching Assistant": "Tutor/in", "Student": "Student/in",
        "Researcher": "Forscher/in", "Reader": "Leser/in",
        "Security Analyst": "Sicherheitsanalyst/in", "Guest": "Gast",
        "Developed by Shekoufeh Neisarian": "Entwickelt von Shekoufeh Neisarian",
        "EXPLORE": "ENTDECKEN", "YOUR ACCOUNT": "DEIN KONTO",
        "News Home": "News-Startseite", "Latest News Feed": "Neueste Nachrichten",
        "Saved Bookmarks": "Gespeicherte Artikel", "Explore News": "Nachrichten entdecken",
        "Cookie settings": "Cookie-Einstellungen", "RSS feed": "RSS-Feed",
        "Explore cybersecurity reporting from trusted publications, with saved articles and secure member accounts.":
            "Entdecke Cybersicherheitsberichte vertrauenswürdiger Medien, speichere Artikel und verwalte dein Konto sicher.",
        // Cookie consent
        "YOUR PRIVACY / CYBERNEWS": "DEINE PRIVATSPHÄRE / CYBERNEWS",
        "Choose your cookies": "Cookie-Einstellungen auswählen",
        "Essential cookies support sign-in and store your cookie decision. You may also allow a theme-preference cookie to remember light or dark mode. We do not use advertising or analytics cookies.":
            "Notwendige Cookies ermöglichen die Anmeldung und speichern deine Cookie-Auswahl. Optional kannst du das helle oder dunkle Design als Einstellung speichern. Wir verwenden keine Werbe- oder Analyse-Cookies.",
        "Remember my theme (optional)": "Design merken (optional)",
        "Essential only": "Nur notwendige", "Save my choice": "Auswahl speichern",
        // Homepage editorial news
        "LIVE FROM PUBLISHER RSS FEEDS": "LIVE AUS DEN RSS-FEEDS DER MEDIEN",
        "Cybersecurity,": "Cybersicherheit,", "in focus.": "im Fokus.",
        "New vulnerabilities, attacks, and security research — linked to the original reporting.":
            "Neue Sicherheitslücken, Angriffe und Forschung – mit Links zu den Originalberichten.",
        "Explore all news": "Alle Meldungen entdecken",
        "The news wire": "Nachrichten-Ticker", "All headlines": "Alle Schlagzeilen",
        "All headlines ↗": "Alle Schlagzeilen ↗",
        "↻ Refresh RSS": "↻ RSS aktualisieren",
        "☆ Saved articles": "☆ Gespeicherte Artikel",
        "← Back to news": "← Zurück zu den Nachrichten",
        "Search & filter stories ↗": "Meldungen suchen und filtern ↗",
        "Explore all news ↗": "Alle Meldungen entdecken ↗",
        "PROFESSOR · MEMBER": "PROFESSOR/IN · MITGLIED",
        "TEACHING ASSISTANT · MEMBER": "TUTOR/IN · MITGLIED",
        "RESEARCHER · MEMBER": "FORSCHER/IN · MITGLIED",
        "SECURITY ANALYST · MEMBER": "SICHERHEITSANALYST/IN · MITGLIED",
        "LATEST REPORTING": "NEUESTE BERICHTE", "Fresh from the feed": "Frisch aus dem Feed",
        "Refresh RSS": "RSS aktualisieren", "Search & filter stories": "Meldungen suchen und filtern",
        "Loading the latest publisher story…": "Neueste Meldung wird geladen …",
        "Checking sources…": "Quellen werden überprüft …",
        "Connecting to publisher feeds…": "Verbindung zu den RSS-Feeds …",
        "PUBLISHER IMAGE NOT PROVIDED": "KEIN ARTIKELBILD VERFÜGBAR",
        "Publisher article": "Originalartikel", "FEATURED": "IM FOKUS",
        "Publication date unavailable": "Veröffentlichungsdatum unbekannt",
        "Checking publisher RSS feeds…": "RSS-Feeds werden abgerufen …",
        "Publisher feeds are temporarily unavailable. No sample incidents have been substituted.":
            "Die RSS-Feeds sind vorübergehend nicht erreichbar. Es werden keine erfundenen Vorfälle angezeigt.",
        "Try refreshing later or browse the original publishers.":
            "Bitte später erneut versuchen oder direkt die Originalquellen besuchen.",
        // Explore news and bookmarks
        "CYBERNEWS / EXPLORE": "CYBERNEWS / ENTDECKEN",
        "Stay ahead of the": "Bleib informiert über die", "story.": "Nachrichten.",
        "Browse cybersecurity coverage, filter what matters, and save useful reading for later.":
            "Entdecke Cybersicherheitsberichte, filtere nach Themen und speichere interessante Artikel.",
        "Saved articles": "Gespeicherte Artikel", "All": "Alle",
        "Vulnerabilities": "Sicherheitslücken", "Ransomware": "Ransomware",
        "Malware": "Schadsoftware", "Data Breaches": "Datenlecks",
        "AI Security": "KI-Sicherheit", "THE NEWS WIRE": "NACHRICHTEN-TICKER",
        "Discover what's happening": "Aktuelle Entwicklungen entdecken",
        "Loading publisher RSS articles…": "RSS-Artikel werden geladen …",
        "No matching headlines. Try another category or search term.":
            "Keine passenden Meldungen. Versuche eine andere Kategorie oder Suche.",
        "News comes from The Hacker News, SecurityWeek and BleepingComputer RSS feeds. Publication dates reflect the publishers’ feeds; original article images appear when supplied. Save articles to your personal reading list.":
            "Die Nachrichten stammen aus den RSS-Feeds von The Hacker News, SecurityWeek und BleepingComputer. Datum und Bilder werden aus den Quellen übernommen. Interessante Artikel kannst du speichern.",
        "YOUR LIBRARY / CYBERNEWS": "DEINE BIBLIOTHEK / CYBERNEWS",
        "Your reading": "Deine Lese", "list.": "liste.",
        "Back to news": "Zurück zu den Nachrichten",
        "Loading your library…": "Deine Bibliothek wird geladen …",
        "Loading bookmarks…": "Lesezeichen werden geladen …",
        "No saved articles here yet.": "Noch keine gespeicherten Artikel.",
        "Nothing matches your search.": "Keine Treffer für deine Suche.",
        "Open the news feed and select": "Öffne die Nachrichten und wähle",
        "on a story to keep it here.": "bei einem Artikel, um ihn zu speichern.",
        "Save": "Speichern", "Saved": "Gespeichert", "Remove": "Entfernen",
        "Read original story": "Originalartikel lesen",
        // Login, registration
        "CYBERNEWS / SECURE SIGN IN": "CYBERNEWS / SICHERE ANMELDUNG",
        "Welcome back.": "Willkommen zurück.",
        "Your next cybersecurity briefing starts here.": "Dein nächstes Cybersecurity-Briefing beginnt hier.",
        "Please sign in to access that page.": "Bitte melde dich an, um diese Seite zu öffnen.",
        "Account created! You can sign in now.": "Konto erstellt! Du kannst dich jetzt anmelden.",
        "USERNAME": "BENUTZERNAME", "PASSWORD": "PASSWORT",
        "DISPLAY NAME": "ANZEIGENAME", "CONFIRM PASSWORD": "PASSWORT BESTÄTIGEN",
        "TEST THE WEBSITE": "WEBSEITE TESTEN", "LOCAL DEMO": "LOKALER TEST",
        "Reader account": "Leserkonto", "New here? Create an account": "Neu hier? Konto erstellen",
        "For this learning project only. Sessions are stored on the Flask server.":
            "Nur für das Lernprojekt. Sitzungen werden auf dem Flask-Server gespeichert.",
        "CYBERNEWS / NEW ACCOUNT": "CYBERNEWS / NEUES KONTO",
        "Join the briefing.": "Jetzt anmelden.",
        "Account created.": "Konto erstellt.",
        "Your account is ready. Sign in to continue.": "Dein Konto ist bereit. Bitte melde dich an.",
        "Use 8–128 characters. Never reuse an important password for this local demo.": "Verwende 8–128 Zeichen und kein wichtiges Passwort für diese lokale Demo.",
        "Create a reader account. An administrator can update your professional title later.":
            "Erstelle ein Leserkonto. Eine Administratorin oder ein Administrator kann später deine Berufsbezeichnung ändern.",
        "Create account": "Konto erstellen", "Already registered?": "Schon registriert?",
        "Passwords are stored as hashes. New registrations receive standard User access.":
            "Passwörter werden gehasht gespeichert. Neue Konten erhalten standardmäßig Benutzerrechte.",
        // Account dashboard
        "YOUR CYBERNEWS DESK / ACCOUNT OVERVIEW": "DEIN CYBERNEWS-BEREICH / KONTOÜBERSICHT",
        "PERSONAL BRIEFING": "PERSÖNLICHER ÜBERBLICK",
        "Welcome back,": "Willkommen zurück,",
        "Your cybersecurity reading space, saved stories, and account activity, all in one place.":
            "Deine Nachrichten, Lesezeichen und Kontoaktivitäten an einem Ort.",
        "MEMBER SINCE": "MITGLIED SEIT", "LATEST SIGN-IN": "LETZTE ANMELDUNG",
        "SAVED ARTICLES": "GESPEICHERTE ARTIKEL", "SIGN-INS": "ANMELDUNGEN",
        "Account registration": "Kontoregistrierung", "Berlin local time": "Berliner Ortszeit",
        "Your personal collection": "Deine persönliche Sammlung",
        "Recorded by this app": "Von dieser App erfasst",
        "01 / YOUR WORKSPACE": "01 / DEIN ARBEITSBEREICH",
        "Continue your research": "Recherche fortsetzen",
        "A few useful places to start. No extra features to learn all at once.":
            "Einige hilfreiche Startpunkte, ohne unnötige Zusatzfunktionen.",
        "Explore latest news": "Neueste Nachrichten entdecken",
        "Live cybersecurity articles and filters": "Aktuelle Cybersecurity-Artikel und Filter",
        "Saved reading list": "Gespeicherte Leseliste",
        "Find what you bookmarked earlier": "Deine früher gespeicherten Artikel finden",
        "Account administration": "Kontoverwaltung",
        "Review roles and sign-in activity": "Rollen und Anmeldeaktivität prüfen",
        "Security webinars": "Security-Webinare",
        "Explore learning opportunities from The Hacker News": "Weiterbildungsangebote von The Hacker News entdecken",
        "02 / SECURITY ACTIVITY": "02 / SICHERHEITSAKTIVITÄT",
        "Your sign-in history": "Deine Anmeldehistorie",
        "Only your account activity is shown here.": "Hier wird nur deine eigene Kontoaktivität angezeigt.",
        "Successful sign-in": "Erfolgreiche Anmeldung", "LATEST": "NEUESTE",
        "No sign-ins recorded yet.": "Noch keine Anmeldungen erfasst.",
        "Previous sign-in:": "Vorherige Anmeldung:",
        "This is your first recorded sign-in": "Dies ist deine erste erfasste Anmeldung",
        "LEARNING CORNER / EXTERNAL RESOURCE": "LERNBEREICH / EXTERNE RESSOURCE",
        "Keep up with security research": "Bei Sicherheitsforschung auf dem Laufenden bleiben",
        "Explore upcoming and recorded cybersecurity webinars from The Hacker News. This is an external resource, not a CyberNews booking feature.":
            "Entdecke anstehende und aufgezeichnete Cybersecurity-Webinare von The Hacker News. Dies ist ein externer Link, keine CyberNews-Buchungsfunktion.",
        "Explore webinars": "Webinare entdecken",
        // Admin dashboard and role controls
        "CYBERNEWS / ADMIN OPERATIONS": "CYBERNEWS / ADMINISTRATION",
        "ACCOUNT CONTROL CENTER": "KONTOVERWALTUNG",
        "People &": "Personen &", "permissions.": "Berechtigungen.",
        "REGISTERED USERS": "REGISTRIERTE PERSONEN", "ADMINISTRATORS": "ADMINISTRATOREN",
        "SUCCESSFUL SIGN-INS": "ERFOLGREICHE ANMELDUNGEN", "NEW (24H)": "NEU (24 STD.)",
        "All local accounts": "Alle lokalen Konten", "Can manage accounts": "Dürfen Konten verwalten",
        "Recorded since tracking began": "Seit Beginn der Erfassung",
        "In the last 24 hours": "In den letzten 24 Stunden",
        "01 / ACCOUNT DIRECTORY": "01 / KONTOVERZEICHNIS",
        "Registered people": "Registrierte Personen",
        "Access": "Zugriff", "Title": "Berufsbezeichnung", "Save": "Speichern",
        "Member": "Mitglied", "Account settings": "Kontoeinstellungen",
        "Registered": "Registriert", "Last login": "Letzte Anmeldung", "Sign-ins": "Anmeldungen",
        "User": "Benutzer/in", "Never": "Noch nie", "Berlin time": "Berliner Zeit",
        "MEMBERS": "MITGLIEDER", "you": "du",
        "02 / AUDIT TRAIL": "02 / PROTOKOLL", "Recent logins": "Letzte Anmeldungen",
        "Only successful sign-ins are listed. Entries persist across restarts.":
            "Nur erfolgreiche Anmeldungen werden angezeigt. Einträge bleiben nach Neustarts erhalten.",
        "No activity has been recorded.": "Noch keine Aktivität erfasst.",
        "03 / ADMIN QUICK GUIDE": "03 / ADMIN-KURZANLEITUNG",
        "How permissions work": "So funktionieren Berechtigungen",
        "Professional title": "Berufsbezeichnung",
        "Browse news, save articles, and use the personal dashboard.":
            "Nachrichten lesen, Artikel speichern und das persönliche Dashboard nutzen.",
        "All member features, plus account directory and role management.":
            "Alle Mitgliederfunktionen sowie Kontoverzeichnis und Rollenverwaltung.",
        "Student, TA, Professor, Researcher, or Security Analyst. Display only, not a permission.":
            "Student/in, Tutor/in, Professor/in, Forscher/in oder Security Analyst. Nur Anzeige, keine Berechtigung.",
        "Cybersecurity webinars for your team": "Cybersecurity-Webinare für dein Team",
        "People & permissions.": "Personen und Berechtigungen.",
        "View your account": "Mein Konto öffnen",
        "Subscribe to the CyberNews RSS feed": "CyberNews-RSS-Feed abonnieren",
        "Open RSS feed": "RSS-Feed öffnen",
        "Switch to dark mode": "Dunkles Design aktivieren",
        "Switch to light mode": "Helles Design aktivieren",
        "Sign-in": "Anmeldung",
        "ACCESS": "ZUGRIFF", "ADMIN QUICK GUIDE": "ADMIN-KURZANLEITUNG"
    };
    const translationsForAttributes = ["placeholder", "title", "aria-label"];
    const originalNodes = new WeakMap();
    const originalsForAttributes = new WeakMap();
    let language = "en";

    function translateValue(text) {
        if (typeof text !== "string") return text;
        const match = text.match(/^(\s*)([\s\S]*?)(\s*)$/);
        if (!match) return text;
        const [, start, content, end] = match;
        if (!content) return text;
        if (Object.prototype.hasOwnProperty.call(german, content)) {
            return start + german[content] + end;
        }
        // Preserve article publication dates and counts while translating UI labels.
        const patterns = [
            [/^Published (.+)$/i, "Veröffentlicht $1"],
            [/^(\d+) of (\d+) stories$/, "$1 von $2 Meldungen"],
            [/^(\d+) of (\d+) saved$/, "$1 von $2 gespeichert"],
            [/^(\d+) stories$/, "$1 Meldungen"],
            [/^Showing (\d+) headlines from verified publisher RSS endpoints\. Dates are displayed in Berlin time\.$/, "$1 Schlagzeilen aus überprüften RSS-Quellen. Datumsangaben in Berliner Zeit."],
            [/^(\d+) publisher headlines · Images shown when included by the source · Dates in Berlin time$/, "$1 Schlagzeilen · Bilder von den Originalquellen · Datumsangaben in Berliner Zeit"],
            [/^Welcome, (.+)\. Review registrations, successful logins, and assign appropriate access and professional titles\.$/, "Willkommen, $1. Hier kannst du Registrierungen und Anmeldungen überprüfen sowie Rollen und Berufsbezeichnungen verwalten."],
            [/^Account settings saved for (.+)\. Permission changes take effect immediately\.$/, "Kontoeinstellungen für $1 gespeichert. Änderungen der Berechtigungen gelten sofort."],
            [/^Articles you saved while signed in as (.+)\. Your list is stored in SQLite\.$/, "Als $1 gespeicherte Artikel. Deine Liste wird in SQLite gespeichert."],
            [/^(.+) access$/, "$1-Zugriff"],
            [/^(.+) signed in$/, "$1 hat sich angemeldet"],
            [/^Could not load bookmarks: (.+)$/, "Lesezeichen konnten nicht geladen werden: $1"],
            [/^Could not update bookmark: (.+)$/, "Lesezeichen konnte nicht geändert werden: $1"],
        ];
        for (const [expression, replacement] of patterns) {
            if (expression.test(content)) return start + content.replace(expression, replacement) + end;
        }
        return text;
    }

    function excluded(node) {
        const owner = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
        return owner && owner.closest && owner.closest(
            "script, style, code, pre, .publisher-original-title, .editorial-lead-title, .wire-item-title, .editorial-small-title, .story-card-title, .brand-wordmark, .header-account-name"
        );
    }
    function translateNode(node) {
        if (node.nodeType === Node.TEXT_NODE) {
            if (excluded(node)) return;
            if (!originalNodes.has(node)) originalNodes.set(node, node.nodeValue);
            const original = originalNodes.get(node);
            const next = language === "de" ? translateValue(original) : original;
            if (node.nodeValue !== next) node.nodeValue = next;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            if (excluded(node)) return;
            if (!originalsForAttributes.has(node)) originalsForAttributes.set(node, {});
            const saved = originalsForAttributes.get(node);
            for (const attribute of translationsForAttributes) {
                if (!node.hasAttribute(attribute)) continue;
                if (!Object.prototype.hasOwnProperty.call(saved, attribute)) saved[attribute] = node.getAttribute(attribute);
                const initial = saved[attribute];
                const next = language === "de" ? translateValue(initial) : initial;
                if (node.getAttribute(attribute) !== next) node.setAttribute(attribute, next);
            }
        }
    }
    function translateBranch(root) {
        translateNode(root);
        if (root.nodeType !== Node.ELEMENT_NODE && root.nodeType !== Node.DOCUMENT_NODE) return;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) translateNode(walker.currentNode);
    }
    function formatLocalTimes() {
        document.querySelectorAll("time.berlin-datetime[data-utc]").forEach(element => {
            const raw = element.dataset.utc;
            const iso = raw?.endsWith(" UTC") ? raw.slice(0, -4).replace(" ", "T") + "Z" : raw;
            const date = new Date(iso || "");
            if (Number.isNaN(date.getTime())) return;
            element.textContent = new Intl.DateTimeFormat(language === "de" ? "de-DE" : "en-GB", {
                timeZone: "Europe/Berlin", day: "2-digit", month: "short", year: "numeric",
                hour: "2-digit", minute: "2-digit", timeZoneName: "short"
            }).format(date);
        });
    }
    function setLanguage(next) {
        language = next === "de" ? "de" : "en";
        document.documentElement.lang = language;
        document.querySelectorAll("[data-lang-choice]").forEach(button => {
            const selected = button.dataset.langChoice === language;
            button.classList.toggle("is-current", selected);
            button.setAttribute("aria-pressed", String(selected));
        });
        translateBranch(document.body);
        formatLocalTimes();
        try { sessionStorage.setItem(KEY, language); } catch (_) { /* temporary choice only */ }
    }

    document.addEventListener("DOMContentLoaded", () => {
        let initial = "en";
        try { initial = sessionStorage.getItem(KEY) === "de" ? "de" : "en"; } catch (_) { /* no storage */ }
        // A URL with ?lang=de or ?lang=en can also set the active translation.
        const requested = new URLSearchParams(location.search).get("lang");
        if (requested === "de" || requested === "en") initial = requested;
        document.querySelectorAll("[data-lang-choice]").forEach(button => {
            button.addEventListener("click", () => setLanguage(button.dataset.langChoice));
        });
        setLanguage(initial);
        // Other scripts insert RSS cards asynchronously; translate UI labels when added.
        const observer = new MutationObserver(records => {
            for (const record of records) {
                record.addedNodes.forEach(node => {
                    if (node.nodeType === Node.TEXT_NODE || node.nodeType === Node.ELEMENT_NODE) {
                        translateBranch(node);
                    }
                });
            }
        });
        observer.observe(document.body, { subtree: true, childList: true });
    });
})();
