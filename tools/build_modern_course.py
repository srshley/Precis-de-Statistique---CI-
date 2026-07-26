from __future__ import annotations

import re
import shutil
from html import escape
from pathlib import Path

from lxml import html


SOURCE_ROOT = Path(r"E:\Precis de statistique descriptive\cours_statistique_html")
WORKSPACE_ROOT = Path(r"C:\Users\~Shley\Documents\Precis de statistique")


CHAPTER_FILES = [
    SOURCE_ROOT / "pages" / f"chapitre{index:02d}.html" for index in range(1, 8)
]


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def class_contains(name: str) -> str:
    return f'contains(concat(" ", normalize-space(@class), " "), " {name} ")'


def remove_nodes(root: html.HtmlElement, xpath: str) -> None:
    for node in root.xpath(xpath):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)


def strip_icon_nodes(root: html.HtmlElement) -> None:
    for icon in root.xpath(".//i"):
        parent = icon.getparent()
        if parent is not None:
            if icon.tail:
                previous = icon.getprevious()
                if previous is not None:
                    previous.tail = (previous.tail or "") + icon.tail
                else:
                    parent.text = (parent.text or "") + icon.tail
            parent.remove(icon)


def prefix_ids(root: html.HtmlElement, prefix: str) -> None:
    mapping: dict[str, str] = {}
    for node in root.xpath(".//*[@id]"):
        old_id = node.get("id")
        if old_id:
            new_id = f"{prefix}-{old_id}"
            mapping[old_id] = new_id
            node.set("id", new_id)

    for node in root.xpath(".//*[@data-toggle]"):
        old_target = node.get("data-toggle")
        if old_target in mapping:
            node.set("data-toggle", mapping[old_target])
            node.set("aria-expanded", "false")

    for node in root.xpath(".//a[@href]"):
        href = node.get("href")
        if href and href.startswith("#") and href[1:] in mapping:
            node.set("href", f"#{mapping[href[1:]]}")


def set_top_section_classes(root: html.HtmlElement) -> None:
    for section in root.xpath("./section"):
        classes = section.get("class", "")
        if "content-section" not in classes:
            section.set("class", clean_text(f"{classes} content-section"))

    for answer in root.xpath(f'.//*[self::div or self::section][{class_contains("answer")}]'):
        answer.attrib.pop("style", None)
        classes = answer.get("class", "")
        if "show" in classes:
            answer.set("class", clean_text(classes.replace("show", "")))


def extract_chapter(path: Path, number: int) -> dict[str, object]:
    document = html.fromstring(path.read_text(encoding="utf-8"))
    container = document.xpath(f'//div[{class_contains("container")}]')[0]

    header = container.xpath("./header")
    title = clean_text(header[0].xpath("string(.//h1)") if header else f"Chapitre {number}")
    subtitle = clean_text(header[0].xpath("string(.//p)") if header and header[0].xpath(".//p") else "")

    remove_nodes(container, f'.//*[self::div][{class_contains("loading-overlay")}]')
    remove_nodes(container, f'.//*[self::div][{class_contains("nav-buttons")}]')
    remove_nodes(container, ".//script")
    strip_icon_nodes(container)

    if header:
        container.remove(header[0])

    prefix_ids(container, f"c{number:02d}")
    set_top_section_classes(container)

    headings = []
    for heading in container.xpath("./section/h2"):
        section = heading.getparent()
        section_id = section.get("id") if section is not None else ""
        headings.append({"id": section_id, "text": clean_text(heading.text_content())})

    exercises = len(container.xpath(f'.//*[self::div or self::section][{class_contains("exercise")}]'))
    glossary_terms = [
        clean_text(term.text_content())
        for term in container.xpath(f'.//dl[{class_contains("glossary")}]/dt')
    ]

    content_html = "\n".join(
        html.tostring(child, encoding="unicode", method="html")
        for child in container
        if getattr(child, "tag", None) is not html.HtmlComment
    )

    return {
        "number": number,
        "slug": f"chapitre-{number:02d}",
        "title": title,
        "short_title": re.sub(r"^Chapitre\s+\d+\s*:\s*", "", title),
        "subtitle": subtitle,
        "headings": headings,
        "exercise_count": exercises,
        "glossary_terms": glossary_terms,
        "content": content_html,
    }


def build_chapter_card(chapter: dict[str, object]) -> str:
    headings = chapter["headings"]
    first_topics = ", ".join(escape(item["text"]) for item in headings[:3])  # type: ignore[index]
    return f"""
      <a class="chapter-card" href="#{chapter['slug']}" data-jump="{chapter['slug']}">
        <span class="chapter-number">Chapitre {chapter['number']}</span>
        <strong>{escape(str(chapter['short_title']))}</strong>
        <small>{first_topics}</small>
      </a>
    """


def build_sidebar_link(chapter: dict[str, object]) -> str:
    links = "\n".join(
        f'<a href="#{escape(str(item["id"]))}">{escape(str(item["text"]))}</a>'
        for item in chapter["headings"]  # type: ignore[index]
    )
    return f"""
      <details open>
        <summary>Chapitre {chapter['number']}</summary>
        {links}
      </details>
    """


def build_chapter_article(chapter: dict[str, object]) -> str:
    return f"""
      <article class="chapter-panel" id="{chapter['slug']}" data-chapter-panel data-search-text="{escape(str(chapter['title']).lower())}">
        <header class="chapter-header">
          <span>Chapitre {chapter['number']}</span>
          <h2>{escape(str(chapter['short_title']))}</h2>
          <p>{escape(str(chapter['subtitle']))}</p>
          <div class="chapter-meta">
            <strong>{len(chapter['headings'])}</strong> sections
            <strong>{chapter['exercise_count']}</strong> exercices et activites
          </div>
        </header>
        {chapter['content']}
      </article>
    """


def render_html(chapters: list[dict[str, object]]) -> str:
    total_exercises = sum(int(chapter["exercise_count"]) for chapter in chapters)
    total_sections = sum(len(chapter["headings"]) for chapter in chapters)
    glossary_terms = sorted(
        {term for chapter in chapters for term in chapter["glossary_terms"] if term}
    )
    glossary_preview = "".join(f"<span>{escape(term)}</span>" for term in glossary_terms[:18])

    return f"""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="description" content="Cours complet de statistique descriptive : 7 chapitres, exercices corriges, glossaire, cas pratiques et atelier interactif." />
    <title>Precis de statistique descriptive</title>
    <link rel="stylesheet" href="css/modern.css" />
    <script>
      window.MathJax = {{
        tex: {{
          inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
          displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
        }}
      }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
  </head>
  <body>
    <div class="reading-progress" aria-hidden="true"><span id="readingProgress"></span></div>

    <header class="topbar">
      <a class="brand" href="#accueil" aria-label="Retour a l'accueil">
        <span class="brand-mark">Σ</span>
        <span>
          <strong>Precis de statistique descriptive</strong>
          <small>7 chapitres complets</small>
        </span>
      </a>
      <nav class="nav" aria-label="Navigation principale">
        <a href="#parcours">Parcours</a>
        <a href="#atelier">Atelier</a>
        <a href="#chapitres">Cours</a>
        <a href="livre_complet.html">Ancien livre</a>
      </nav>
    </header>

    <main id="accueil">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">Statistique descriptive</p>
          <h1>Un cours complet pour lire, resumer et interpreter les donnees.</h1>
          <p class="lead">
            Cette version rassemble les contenus du cours source en une experience web plus claire :
            definitions, methodes, exemples guides, exercices corriges, glossaires et cas d'application.
          </p>
          <div class="hero-actions">
            <a class="button primary" href="#chapitres">Lire le cours complet</a>
            <a class="button secondary" href="#atelier">Ouvrir l'atelier</a>
          </div>
        </div>
        <div class="dashboard-card" aria-label="Resume du cours">
          <div class="dashboard-head">
            <span>Progression du cours</span>
            <strong>Complet</strong>
          </div>
          <div class="bars" aria-hidden="true">
            <span style="--h: 50%"></span>
            <span style="--h: 62%"></span>
            <span style="--h: 78%"></span>
            <span style="--h: 58%"></span>
            <span style="--h: 66%"></span>
            <span style="--h: 74%"></span>
            <span style="--h: 88%"></span>
          </div>
          <div class="metric-grid">
            <div><small>Chapitres</small><strong>{len(chapters)}</strong></div>
            <div><small>Sections</small><strong>{total_sections}</strong></div>
            <div><small>Exercices</small><strong>{total_exercises}+</strong></div>
          </div>
        </div>
      </section>

      <section id="parcours" class="course-map">
        <article>
          <span>01</span>
          <h2>Comprendre</h2>
          <p>Population, echantillon, variable, modalite et types de donnees.</p>
        </article>
        <article>
          <span>02</span>
          <h2>Organiser</h2>
          <p>Tableaux, effectifs, frequences, classes et representations graphiques.</p>
        </article>
        <article>
          <span>03</span>
          <h2>Interpreter</h2>
          <p>Moyenne, mediane, quartiles, dispersion, forme, correlation et regression.</p>
        </article>
      </section>

      <section class="section study-guide">
        <div class="section-title">
          <p class="eyebrow">Guide rapide</p>
          <h2>Comment utiliser ce cours</h2>
          <p>Chaque chapitre contient les notions, les formules, les exemples, puis les exercices avec correction masquee.</p>
        </div>
        <div class="guide-grid">
          <article><strong>1. Lire</strong><span>Commencez par les definitions et les exemples concrets.</span></article>
          <article><strong>2. Calculer</strong><span>Refaites les calculs a la main avant d'afficher les corrections.</span></article>
          <article><strong>3. Interpreter</strong><span>Expliquez toujours ce que le resultat signifie dans la situation etudiee.</span></article>
        </div>
      </section>

      <section id="atelier" class="section workshop">
        <div class="section-title compact">
          <p class="eyebrow">Atelier</p>
          <h2>Calculateur de serie statistique</h2>
          <p>Entrez des nombres separes par des virgules, espaces ou points-virgules.</p>
        </div>
        <div class="tool">
          <label for="dataset">Votre serie</label>
          <textarea id="dataset" rows="4">8, 10, 11, 12, 12, 13, 14, 15, 15, 16, 18</textarea>
          <div class="tool-actions">
            <button type="button" id="sampleA">Notes</button>
            <button type="button" id="sampleB">Ventes</button>
            <button type="button" id="sampleC">Revenus</button>
            <button type="button" id="clearData">Effacer</button>
          </div>
        </div>
        <div class="results" aria-live="polite">
          <article><small>Effectif</small><strong id="count">0</strong></article>
          <article><small>Moyenne</small><strong id="mean">0</strong></article>
          <article><small>Mediane</small><strong id="median">0</strong></article>
          <article><small>Mode</small><strong id="mode">0</strong></article>
          <article><small>Etendue</small><strong id="range">0</strong></article>
          <article><small>Q1</small><strong id="q1">0</strong></article>
          <article><small>Q3</small><strong id="q3">0</strong></article>
          <article><small>Ecart-type</small><strong id="stddev">0</strong></article>
        </div>
        <div class="histogram">
          <h3>Representation rapide</h3>
          <div id="histogramBars" class="histogram-bars" aria-label="Histogramme des valeurs"></div>
          <p id="feedback" class="feedback"></p>
        </div>
      </section>

      <section id="chapitres" class="section course-shell">
        <aside class="course-sidebar" aria-label="Sommaire detaille">
          <div class="sidebar-box">
            <label for="courseSearch">Rechercher dans le cours</label>
            <input id="courseSearch" type="search" placeholder="Ex. variance, quartile, regression" />
          </div>
          <nav class="toc">
            {"".join(build_sidebar_link(chapter) for chapter in chapters)}
          </nav>
        </aside>

        <div class="course-content">
          <div class="section-title">
            <p class="eyebrow">Cours complet</p>
            <h2>Les 7 chapitres enrichis</h2>
            <p>Utilisez le sommaire ou la recherche pour passer rapidement d'une notion a l'autre.</p>
          </div>
          <div class="chapter-strip" aria-label="Acces rapide aux chapitres">
            {"".join(build_chapter_card(chapter) for chapter in chapters)}
          </div>
          <div id="searchStatus" class="search-status" aria-live="polite"></div>
          {"".join(build_chapter_article(chapter) for chapter in chapters)}
        </div>
      </section>

      <section class="section glossary-preview">
        <div class="section-title compact">
          <p class="eyebrow">Glossaire</p>
          <h2>Notions a maitriser</h2>
        </div>
        <div class="term-cloud">{glossary_preview}</div>
      </section>
    </main>

    <button class="back-to-top" type="button" aria-label="Retour en haut">↑</button>

    <footer class="footer">
      <p>Precis de statistique descriptive - version web complete</p>
      <a href="#accueil">Retour en haut</a>
    </footer>

    <script src="js/modern.js"></script>
  </body>
</html>
"""


MODERN_CSS = r""":root {
  color-scheme: light;
  --ink: #17202a;
  --muted: #657281;
  --line: #dbe5ed;
  --paper: #fbfcf7;
  --surface: #ffffff;
  --mist: #eef5f1;
  --blue: #255c99;
  --blue-dark: #173f6f;
  --green: #2f8f72;
  --amber: #c88428;
  --coral: #c85043;
  --violet: #6c5aa8;
  --shadow: 0 20px 48px rgba(23, 32, 42, 0.12);
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Arial, Helvetica, sans-serif;
  color: var(--ink);
  background: var(--paper);
  line-height: 1.65;
}
a { color: inherit; }
img, svg { max-width: 100%; height: auto; }

.reading-progress {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  z-index: 30;
  background: transparent;
}
.reading-progress span {
  display: block;
  width: 0%;
  height: 100%;
  background: var(--green);
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 14px clamp(18px, 4vw, 56px);
  border-bottom: 1px solid rgba(217, 226, 234, 0.9);
  background: rgba(251, 252, 247, 0.94);
  backdrop-filter: blur(14px);
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 260px;
  text-decoration: none;
}
.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: var(--blue);
  color: #fff;
  font-size: 25px;
  font-weight: 700;
}
.brand strong, .brand small { display: block; }
.brand strong { line-height: 1.1; }
.brand small { color: var(--muted); font-size: 12px; }
.nav {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}
.nav a {
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--muted);
  font-size: 14px;
  text-decoration: none;
}
.nav a:hover, .nav a:focus-visible {
  color: var(--ink);
  background: var(--mist);
  outline: none;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: clamp(28px, 5vw, 70px);
  align-items: center;
  min-height: calc(100vh - 74px);
  padding: clamp(44px, 8vw, 92px) clamp(18px, 6vw, 76px) 36px;
}
.hero-copy { max-width: 780px; }
.eyebrow {
  margin: 0 0 12px;
  color: var(--green);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
}
h1, h2, h3, h4, p { margin-top: 0; }
h1 {
  margin-bottom: 18px;
  font-size: clamp(40px, 7vw, 78px);
  line-height: 0.98;
  letter-spacing: 0;
}
h2 {
  margin-bottom: 12px;
  font-size: clamp(28px, 4vw, 44px);
  line-height: 1.08;
  letter-spacing: 0;
}
h3 { margin-bottom: 8px; font-size: 21px; line-height: 1.25; letter-spacing: 0; }
h4 { margin-bottom: 8px; font-size: 17px; letter-spacing: 0; }
.lead { max-width: 700px; color: #3b4855; font-size: 20px; }
.hero-actions, .tool-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 26px;
}
.button, button {
  min-height: 44px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 11px 16px;
  background: var(--surface);
  color: var(--ink);
  font: inherit;
  font-weight: 700;
  text-decoration: none;
  cursor: pointer;
}
.button.primary, button.primary {
  border-color: var(--blue);
  background: var(--blue);
  color: #fff;
}
.button.secondary { background: transparent; }
.button:hover, button:hover, .button:focus-visible, button:focus-visible {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(23, 32, 42, 0.12);
  outline: none;
}

.dashboard-card {
  width: min(100%, 480px);
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.dashboard-head, .metric-grid {
  display: flex;
  justify-content: space-between;
  gap: 14px;
}
.dashboard-head { align-items: center; margin-bottom: 26px; }
.dashboard-head span { color: var(--muted); }
.bars {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  align-items: end;
  gap: 12px;
  height: 250px;
  padding: 16px;
  border-radius: 8px;
  background:
    linear-gradient(to top, rgba(217, 226, 234, 0.75) 1px, transparent 1px) 0 0 / 100% 25%,
    #f6faf8;
}
.bars span {
  min-width: 18px;
  height: var(--h);
  border-radius: 7px 7px 2px 2px;
  background: linear-gradient(180deg, var(--green), var(--blue));
}
.metric-grid { margin-top: 22px; }
.metric-grid div, .results article {
  flex: 1;
  min-width: 0;
  padding: 14px;
  border-radius: 8px;
  background: var(--mist);
}
.metric-grid small, .results small {
  display: block;
  color: var(--muted);
  font-size: 12px;
}
.metric-grid strong, .results strong {
  display: block;
  margin-top: 4px;
  font-size: 24px;
  line-height: 1.1;
}

.course-map {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  padding: 0 clamp(18px, 6vw, 76px) 46px;
}
.course-map article, .guide-grid article, .tool, .histogram, .chapter-panel,
.sidebar-box, .toc, .chapter-card, .highlight, .definition, .analogy,
.example-box, .exercise, .answer, .diagram, .formula, .case-study {
  border-radius: 8px;
}
.course-map article, .guide-grid article, .tool, .histogram, .chapter-panel,
.sidebar-box, .toc, .chapter-card {
  border: 1px solid var(--line);
  background: var(--surface);
}
.course-map article { padding: 22px; }
.course-map span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  margin-bottom: 16px;
  border-radius: 8px;
  background: var(--coral);
  color: #fff;
  font-weight: 700;
}
.course-map h2 { font-size: 23px; }
.course-map p, .section-title p, .feedback, .search-status,
.chapter-card small, .chapter-header p { color: var(--muted); }

.section { padding: clamp(50px, 8vw, 88px) clamp(18px, 6vw, 76px); }
.section-title { max-width: 820px; margin-bottom: 28px; }
.section-title.compact { max-width: 560px; }
.study-guide { background: #eef5f1; }
.guide-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.guide-grid article { padding: 20px; }
.guide-grid strong, .guide-grid span { display: block; }
.guide-grid span { margin-top: 8px; color: var(--muted); }

.workshop {
  display: grid;
  grid-template-columns: minmax(280px, 0.78fr) minmax(0, 1.22fr);
  gap: 18px;
}
.workshop .section-title, .workshop .tool { grid-column: 1; }
.results, .histogram { grid-column: 2; }
.tool { padding: 20px; }
.tool label, .sidebar-box label {
  display: block;
  margin-bottom: 8px;
  font-weight: 700;
}
textarea, input[type="search"] {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  line-height: 1.5;
}
textarea { resize: vertical; }
textarea:focus, input[type="search"]:focus {
  border-color: var(--blue);
  outline: 3px solid rgba(37, 92, 153, 0.16);
}
.results {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.histogram { padding: 22px; }
.histogram-bars {
  display: grid;
  align-items: end;
  gap: 10px;
  min-height: 230px;
  margin: 18px 0 12px;
  padding: 16px;
  border-radius: 8px;
  background:
    linear-gradient(to top, rgba(217, 226, 234, 0.75) 1px, transparent 1px) 0 0 / 100% 25%,
    #f7faf9;
}
.histogram-bar {
  display: flex;
  align-items: end;
  justify-content: center;
  min-width: 0;
  height: var(--height);
  border-radius: 7px 7px 2px 2px;
  background: var(--blue);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  overflow: hidden;
}

.course-shell {
  display: grid;
  grid-template-columns: minmax(250px, 300px) minmax(0, 1fr);
  align-items: start;
  gap: 24px;
}
.course-sidebar {
  position: sticky;
  top: 86px;
  display: grid;
  gap: 14px;
  max-height: calc(100vh - 104px);
  overflow: auto;
}
.sidebar-box, .toc { padding: 16px; }
.toc details + details { margin-top: 10px; }
.toc summary {
  cursor: pointer;
  color: var(--blue-dark);
  font-weight: 700;
}
.toc a {
  display: block;
  padding: 7px 0 7px 12px;
  border-left: 2px solid var(--line);
  color: var(--muted);
  font-size: 14px;
  text-decoration: none;
}
.toc a:hover, .toc a.active {
  border-left-color: var(--green);
  color: var(--ink);
}
.chapter-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}
.chapter-card {
  display: block;
  padding: 18px;
  text-decoration: none;
}
.chapter-card:hover { box-shadow: var(--shadow); transform: translateY(-2px); }
.chapter-number {
  display: inline-block;
  margin-bottom: 10px;
  color: var(--green);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}
.chapter-card strong { display: block; font-size: 18px; line-height: 1.25; }
.chapter-card small { display: block; margin-top: 8px; line-height: 1.45; }
.search-status { min-height: 24px; margin-bottom: 16px; font-weight: 700; }

.chapter-panel {
  margin-top: 26px;
  padding: clamp(20px, 4vw, 34px);
  box-shadow: 0 12px 32px rgba(23, 32, 42, 0.08);
}
.chapter-panel[hidden] { display: none; }
.chapter-header {
  margin: -1px -1px 28px;
  padding: clamp(22px, 4vw, 34px);
  border-radius: 8px 8px 0 0;
  background: #f2f7fb;
  border-bottom: 1px solid var(--line);
}
.chapter-header span {
  display: inline-block;
  margin-bottom: 10px;
  color: var(--green);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
}
.chapter-header h2 { margin-bottom: 8px; }
.chapter-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-top: 18px;
  color: var(--muted);
  font-size: 14px;
}
.chapter-meta strong { color: var(--ink); }
.content-section {
  scroll-margin-top: 96px;
  margin-top: 32px;
}
.content-section > h2 {
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}
.content-section > h2:first-child { margin-top: 0; }
.chapter-panel p, .chapter-panel li { color: #2f3b47; }
.chapter-panel ul, .chapter-panel ol { padding-left: 24px; }
.chapter-panel li + li { margin-top: 6px; }
.keyword { color: var(--blue-dark); font-weight: 700; }

.highlight, .definition, .analogy, .example-box, .exercise, .answer,
.formula, .case-study {
  margin: 16px 0;
  padding: 16px 18px;
}
.highlight { border-left: 5px solid var(--amber); background: #fff7e8; }
.definition { border-left: 5px solid var(--blue); background: #eef4fa; }
.analogy { border-left: 5px solid var(--green); background: #edf7f1; }
.example-box { border-left: 5px solid var(--violet); background: #f3f1fa; }
.exercise { border: 1px dashed #7db6d8; background: #eff8fc; }
.answer {
  display: none;
  border: 1px solid #cddbd2;
  background: #f7fbf8;
}
.answer.show { display: block; }
.btn-toggle {
  margin-top: 8px;
  background: var(--green);
  color: #fff;
}
.formula {
  background: #eef2f7;
  text-align: center;
  font-size: 1.08em;
  overflow-x: auto;
}
.diagram {
  margin: 18px 0;
  padding: 16px;
  border: 1px solid var(--line);
  background: #fafafa;
  text-align: center;
  overflow-x: auto;
}
.diagram figcaption {
  margin-top: 8px;
  color: var(--muted);
  font-size: 13px;
  font-style: italic;
}
.table-responsive {
  width: 100%;
  margin: 16px 0;
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
  font-size: 0.95em;
}
th, td {
  border: 1px solid var(--line);
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--blue);
  color: #fff;
}
tr:nth-child(even) { background: #f7faf9; }
.glossary {
  display: grid;
  grid-template-columns: minmax(160px, 0.35fr) minmax(0, 0.65fr);
  gap: 8px 16px;
}
.glossary dt { color: var(--blue-dark); font-weight: 700; }
.glossary dd { margin: 0; color: #2f3b47; }
.case-study { border-left: 5px solid var(--coral); background: #fff1ef; }

.glossary-preview { background: #eef3f8; }
.term-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.term-cloud span {
  padding: 8px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid var(--line);
  color: var(--blue-dark);
  font-weight: 700;
}
.back-to-top {
  position: fixed;
  right: 18px;
  bottom: 18px;
  z-index: 15;
  width: 46px;
  height: 46px;
  padding: 0;
  border-radius: 50%;
  opacity: 0;
  pointer-events: none;
}
.back-to-top.show { opacity: 1; pointer-events: auto; }
.footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 26px clamp(18px, 6vw, 76px);
  background: var(--ink);
  color: #fff;
}
.footer p { margin-bottom: 0; }
.footer a { color: #fff; font-weight: 700; }

@media (max-width: 1060px) {
  .hero, .course-shell, .workshop {
    grid-template-columns: minmax(0, 1fr);
  }
  .course-sidebar {
    position: static;
    max-height: none;
  }
  .workshop .section-title, .workshop .tool, .results, .histogram {
    grid-column: auto;
  }
}
@media (max-width: 820px) {
  .course-map, .guide-grid, .chapter-strip {
    grid-template-columns: minmax(0, 1fr);
  }
  .results { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .glossary { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 680px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }
  .brand { min-width: 0; }
  .nav { justify-content: flex-start; }
  .hero { min-height: auto; }
  h1 { font-size: 42px; }
  .metric-grid { flex-direction: column; }
  .results { grid-template-columns: minmax(0, 1fr); }
  .histogram-bars { gap: 6px; }
  .footer { flex-direction: column; }
}
"""


MODERN_JS = r"""const datasetInput = document.querySelector("#dataset");
const histogram = document.querySelector("#histogramBars");
const feedback = document.querySelector("#feedback");
const progress = document.querySelector("#readingProgress");
const searchInput = document.querySelector("#courseSearch");
const searchStatus = document.querySelector("#searchStatus");
const backToTop = document.querySelector(".back-to-top");

const output = {
  count: document.querySelector("#count"),
  mean: document.querySelector("#mean"),
  median: document.querySelector("#median"),
  mode: document.querySelector("#mode"),
  range: document.querySelector("#range"),
  q1: document.querySelector("#q1"),
  q3: document.querySelector("#q3"),
  stddev: document.querySelector("#stddev"),
};

const samples = {
  notes: "8, 10, 11, 12, 12, 13, 14, 15, 15, 16, 18",
  sales: "24, 31, 28, 45, 45, 52, 39, 41, 56, 47, 45, 60",
  income: "1200, 1300, 1350, 1500, 1600, 1700, 1850, 2200, 2800, 4500",
};

function parseValues(text) {
  return text
    .split(/[\s,;]+/)
    .map((value) => Number(value.replace(",", ".")))
    .filter((value) => Number.isFinite(value));
}

function formatNumber(value) {
  if (!Number.isFinite(value)) return "-";
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(".", ",");
}

function quantile(sorted, probability) {
  if (sorted.length === 0) return NaN;
  const position = (sorted.length - 1) * probability;
  const base = Math.floor(position);
  const rest = position - base;
  if (sorted[base + 1] === undefined) return sorted[base];
  return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
}

function getMode(values) {
  const frequencies = new Map();
  values.forEach((value) => frequencies.set(value, (frequencies.get(value) || 0) + 1));
  const maxFrequency = Math.max(...frequencies.values());
  if (maxFrequency === 1) return "Aucun";
  return [...frequencies.entries()]
    .filter(([, frequency]) => frequency === maxFrequency)
    .map(([value]) => formatNumber(value))
    .join(", ");
}

function renderHistogram(values) {
  histogram.innerHTML = "";
  if (values.length === 0) {
    histogram.style.gridTemplateColumns = "1fr";
    histogram.innerHTML = '<div class="empty-state">Ajoutez des donnees pour voir le graphique.</div>';
    return;
  }

  const frequencies = new Map();
  values.forEach((value) => frequencies.set(value, (frequencies.get(value) || 0) + 1));
  const entries = [...frequencies.entries()].sort((a, b) => a[0] - b[0]);
  const maxFrequency = Math.max(...entries.map(([, frequency]) => frequency));

  histogram.style.gridTemplateColumns = `repeat(${entries.length}, minmax(0, 1fr))`;
  entries.forEach(([value, frequency]) => {
    const bar = document.createElement("div");
    bar.className = "histogram-bar";
    bar.style.setProperty("--height", `${Math.max(18, (frequency / maxFrequency) * 190)}px`);
    bar.title = `${formatNumber(value)} : ${frequency}`;
    bar.textContent = formatNumber(value);
    histogram.appendChild(bar);
  });
}

function updateStats() {
  const values = parseValues(datasetInput.value).sort((a, b) => a - b);
  if (values.length === 0) {
    Object.values(output).forEach((element) => {
      element.textContent = "-";
    });
    feedback.textContent = "Entrez au moins une valeur numerique.";
    renderHistogram([]);
    return;
  }

  const total = values.reduce((sum, value) => sum + value, 0);
  const mean = total / values.length;
  const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  const stddev = Math.sqrt(variance);
  const range = values[values.length - 1] - values[0];

  output.count.textContent = values.length;
  output.mean.textContent = formatNumber(mean);
  output.median.textContent = formatNumber(quantile(values, 0.5));
  output.mode.textContent = getMode(values);
  output.range.textContent = formatNumber(range);
  output.q1.textContent = formatNumber(quantile(values, 0.25));
  output.q3.textContent = formatNumber(quantile(values, 0.75));
  output.stddev.textContent = formatNumber(stddev);

  const median = quantile(values, 0.5);
  const interpretation =
    Math.abs(mean - median) > stddev / 2
      ? "La moyenne et la mediane sont eloignees : verifiez la presence de valeurs extremes."
      : "La moyenne et la mediane sont proches : la serie semble assez equilibree.";

  feedback.textContent = interpretation;
  renderHistogram(values);
}

document.querySelector("#sampleA").addEventListener("click", () => {
  datasetInput.value = samples.notes;
  updateStats();
});
document.querySelector("#sampleB").addEventListener("click", () => {
  datasetInput.value = samples.sales;
  updateStats();
});
document.querySelector("#sampleC").addEventListener("click", () => {
  datasetInput.value = samples.income;
  updateStats();
});
document.querySelector("#clearData").addEventListener("click", () => {
  datasetInput.value = "";
  updateStats();
  datasetInput.focus();
});
datasetInput.addEventListener("input", updateStats);

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-toggle]");
  if (!button) return;
  const answer = document.getElementById(button.getAttribute("data-toggle"));
  if (!answer) return;
  const isVisible = answer.classList.toggle("show");
  button.textContent = isVisible ? "Cacher la correction" : "Voir la correction";
  button.setAttribute("aria-expanded", String(isVisible));
});

function normalize(value) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function filterCourse() {
  const query = normalize(searchInput.value.trim());
  const panels = [...document.querySelectorAll("[data-chapter-panel]")];
  if (!query) {
    panels.forEach((panel) => {
      panel.hidden = false;
      panel.querySelectorAll(".content-section").forEach((section) => {
        section.hidden = false;
      });
    });
    searchStatus.textContent = "";
    return;
  }

  let visibleChapters = 0;
  let visibleSections = 0;
  panels.forEach((panel) => {
    let chapterHasMatch = false;
    panel.querySelectorAll(".content-section").forEach((section) => {
      const match = normalize(section.textContent).includes(query);
      section.hidden = !match;
      if (match) {
        chapterHasMatch = true;
        visibleSections += 1;
      }
    });
    panel.hidden = !chapterHasMatch;
    if (chapterHasMatch) visibleChapters += 1;
  });
  searchStatus.textContent =
    visibleSections === 0
      ? "Aucun resultat trouve."
      : `${visibleSections} section(s) trouvee(s) dans ${visibleChapters} chapitre(s).`;
}

searchInput.addEventListener("input", filterCourse);

function updateProgress() {
  const scrollTop = document.documentElement.scrollTop || document.body.scrollTop;
  const maxScroll = document.documentElement.scrollHeight - document.documentElement.clientHeight;
  const percent = maxScroll > 0 ? (scrollTop / maxScroll) * 100 : 0;
  progress.style.width = `${percent}%`;
  backToTop.classList.toggle("show", scrollTop > 600);
}

window.addEventListener("scroll", updateProgress, { passive: true });
backToTop.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

const tocLinks = [...document.querySelectorAll(".toc a")];
const observer = new IntersectionObserver(
  (entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!visible) return;
    tocLinks.forEach((link) => {
      link.classList.toggle("active", link.getAttribute("href") === `#${visible.target.id}`);
    });
  },
  { rootMargin: "-20% 0px -70% 0px", threshold: [0.05, 0.2, 0.5] }
);

document.querySelectorAll(".content-section[id]").forEach((section) => observer.observe(section));

updateStats();
updateProgress();
"""


def write_outputs(target_root: Path, chapters: list[dict[str, object]], replace_index: bool) -> None:
    (target_root / "css").mkdir(parents=True, exist_ok=True)
    (target_root / "js").mkdir(parents=True, exist_ok=True)

    if replace_index:
        original_index = target_root / "index.html"
        backup = target_root / "index_classique.html"
        if original_index.exists() and not backup.exists():
            shutil.copy2(original_index, backup)
        html_path = original_index
    else:
        html_path = target_root / "index_complet.html"

    html_path.write_text(render_html(chapters), encoding="utf-8")
    (target_root / "css" / "modern.css").write_text(MODERN_CSS, encoding="utf-8")
    (target_root / "js" / "modern.js").write_text(MODERN_JS, encoding="utf-8")


def main() -> None:
    chapters = [extract_chapter(path, index) for index, path in enumerate(CHAPTER_FILES, 1)]
    write_outputs(SOURCE_ROOT, chapters, replace_index=True)
    write_outputs(WORKSPACE_ROOT, chapters, replace_index=False)
    print(f"Generated modern course with {len(chapters)} chapters")
    print(SOURCE_ROOT / "index.html")
    print(WORKSPACE_ROOT / "index_complet.html")


if __name__ == "__main__":
    main()
