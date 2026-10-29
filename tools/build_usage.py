"""Build docs/usage.html (the user guide, published on GitHub Pages) from
docs/USAGE.md.

    python3 tools/build_usage.py          # write docs/usage.html
    python3 tools/build_usage.py --check  # fail if docs/usage.html is stale

A small Markdown subset, no dependencies: headings (#, ##, ###, ####),
paragraphs, "- " lists (indented two spaces for a nested list), "1. "
lists, "> " notes, "| a | b |" tables, **bold**, *italic*, `code` and
[links](url). ``{version}`` is replaced by metadata.txt's version.
tests/unit/test_usage_docs.py keeps the guide in step with the Publish
window (every option documented) and the HTML in step with the Markdown.
"""

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "docs", "USAGE.md")
TARGET = os.path.join(ROOT, "docs", "usage.html")


def version() -> str:
    with open(os.path.join(ROOT, "metadata.txt"), encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("version="):
                return line.split("=", 1)[1].strip()
    return ""


def slug(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def inline(text: str) -> str:
    """Inline markup of one line (escaped first)."""
    codes = []

    def keep(match):
        codes.append("<code>" + html.escape(match.group(1)) + "</code>")
        return f"\x00{len(codes) - 1}\x00"
    text = re.sub(r"`([^`]+)`", keep, text)
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub("\x00(\\d+)\x00", lambda m: codes[int(m.group(1))], text)


def convert(markdown: str):
    """(body html, [(level, id, title)])."""
    out, toc, para, lists = [], [], [], []
    used = {}
    lines = markdown.replace("{version}", version()).splitlines()

    def flush_para():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    def close_lists(depth=0):
        while len(lists) > depth:
            out.append("</li></" + lists.pop() + ">")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        item = re.match(r"^( *)(-|\d+\.)\s+(.*)$", line)
        if not stripped:
            flush_para()
            close_lists()
        elif heading:
            flush_para()
            close_lists()
            level, title = len(heading.group(1)), inline(heading.group(2))
            anchor = slug(title) or "section"
            used[anchor] = used.get(anchor, 0) + 1
            if used[anchor] > 1:
                anchor += f"-{used[anchor]}"
            if level in (2, 3):
                toc.append((level, anchor, title))
            out.append(f'<h{level} id="{anchor}">{title}</h{level}>')
        elif item:
            flush_para()
            depth = len(item.group(1)) // 2 + 1
            kind = "ul" if item.group(2) == "-" else "ol"
            if depth > len(lists):
                while depth > len(lists):
                    out.append(f"<{kind}><li>")
                    lists.append(kind)
            else:
                close_lists(depth)
                out.append("</li><li>")
            out.append(inline(item.group(3)))
        elif stripped.startswith(">"):
            flush_para()
            close_lists()
            note = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                note.append(lines[i].strip()[1:].strip())
                i += 1
            out.append('<div class="note">' + inline(" ".join(note)) + "</div>")
            continue
        elif stripped.startswith("|"):
            flush_para()
            close_lists()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            head, body = rows[0], rows[1:]
            out.append('<div class="table"><table><thead><tr>' + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r)
                                                         + "</tr>" for r in body) + "</tbody></table></div>")
            continue
        elif lists and line.startswith("  "):
            out.append(" " + inline(stripped))  # continuation of a list item
        else:
            close_lists()
            para.append(stripped)
        i += 1
    flush_para()
    close_lists()
    return "\n".join(out), toc


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QWebMap user guide</title>
<meta name="description" content="How to use QWebMap, the QGIS plugin that publishes a QGIS project as a web map: every option of the Publish window, with pitfalls and errors.">
<link rel="icon" type="image/png" href="icons/icon.png">
<style>
:root { --bg: #fbfcf8; --fg: #1d2418; --muted: #5d6957; --line: #dde3d6; --panel: #f1f4ec; --accent: #4f8f33;
  --code: #eef2e8; --note: #fff8e1; --note-line: #e0b84d; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --bg: #151a13; --fg: #e3e9dc; --muted: #9aa692; --line: #2d3628;
  --panel: #1c2319; --accent: #8cc56b; --code: #242c20; --note: #2b2617; --note-line: #8a7030; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg); font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
a { color: var(--accent); }
header { position: sticky; top: 0; z-index: 4; display: flex; gap: 16px; align-items: center; padding: 10px 20px;
  background: var(--panel); border-bottom: 1px solid var(--line); }
header img { width: 30px; height: 30px; }
header .name { font-weight: 700; }
header .ver { color: var(--muted); font-size: 13px; }
header input { margin-left: auto; width: min(320px, 45vw); padding: 6px 10px; border: 1px solid var(--line);
  border-radius: 6px; background: var(--bg); color: var(--fg); font: inherit; }
.layout { display: grid; grid-template-columns: 250px minmax(0, 1fr); max-width: 1200px; margin: 0 auto; }
nav { position: sticky; top: 52px; align-self: start; max-height: calc(100vh - 52px); overflow: auto; padding: 18px 12px 40px 20px;
  font-size: 13.5px; border-right: 1px solid var(--line); }
nav a { display: block; padding: 2px 0; color: var(--fg); text-decoration: none; }
nav a.sub { padding-left: 14px; color: var(--muted); }
nav a:hover { color: var(--accent); }
main { padding: 8px 36px 80px; min-width: 0; }
main > * { max-width: 820px; }
h1 { font-size: 28px; margin: 24px 0 4px; }
h2, h3, h4 { scroll-margin-top: var(--header-h, 70px); }
h2 { font-size: 22px; margin: 40px 0 8px; padding-top: 8px; border-top: 1px solid var(--line); }
h3 { font-size: 17px; margin: 24px 0 6px; }
h4 { font-size: 15px; margin: 18px 0 4px; }
ul, ol { padding-left: 22px; }
li { margin: 3px 0; }
code { background: var(--code); padding: 1px 5px; border-radius: 4px; font-size: 13.5px; }
.note { border-left: 4px solid var(--note-line); background: var(--note); padding: 8px 12px; margin: 12px 0; border-radius: 4px; }
.table { overflow-x: auto; }
table { border-collapse: collapse; margin: 10px 0; font-size: 14px; }
th, td { border: 1px solid var(--line); padding: 5px 9px; text-align: left; vertical-align: top; }
th { background: var(--panel); }
.hidden { display: none !important; }
mark { background: #f6e27a; color: #1d2418; }
#toc-button { display: none; padding: 6px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg);
  color: var(--fg); font: inherit; cursor: pointer; }
@media (max-width: 860px) {
  .layout { grid-template-columns: 1fr; }
  header { flex-wrap: wrap; gap: 8px 12px; }
  header input { order: 3; width: 100%; margin-left: 0; }
  #toc-button { display: block; margin-left: auto; }
  nav { display: none; position: fixed; z-index: 3; left: 0; right: 0; bottom: 0; top: var(--header-h, 100px);
    max-height: none; background: var(--panel); border-right: 0; border-top: 1px solid var(--line); padding: 12px 20px 40px;
    font-size: 15px; }
  nav a { padding: 6px 0; }
  nav.open { display: block; }
  main { padding: 8px 16px 60px; }
}
</style>
</head>
<body>
<header>
  <img src="icons/icon.png" alt="">
  <div><div class="name">QWebMap user guide</div><div class="ver">version {version} · <a href="https://github.com/danzig666/QWebMap">GitHub</a> · <a href="https://danzig666.github.io/QWebMap/">demo map</a></div></div>
  <button id="toc-button" type="button" aria-expanded="false" aria-controls="toc">Contents</button>
  <input id="find" type="search" placeholder="Find an option…" aria-label="Find an option">
</header>
<div class="layout">
<nav id="toc">{toc}</nav>
<main>
{body}
</main>
</div>
<script>
// Phones: the contents open from the header's Contents button, below the header.
const toc = document.getElementById("toc"), button = document.getElementById("toc-button");
const header = document.querySelector("header");
const measure = () => document.documentElement.style.setProperty("--header-h", header.getBoundingClientRect().height + 8 + "px");
measure();
addEventListener("resize", measure);
const setOpen = (open) => {
  document.documentElement.style.setProperty("--header-h", header.getBoundingClientRect().height + "px");
  toc.classList.toggle("open", open);
  button.setAttribute("aria-expanded", String(open));
  button.textContent = open ? "Close" : "Contents";
};
button.addEventListener("click", () => setOpen(!toc.classList.contains("open")));
toc.addEventListener("click", (e) => { if (e.target.closest("a")) setOpen(false); });
// "Find an option": show only the list items, rows and paragraphs that contain the text.
const find = document.getElementById("find");
const items = [...document.querySelectorAll("main li, main tr, main p, main .note")].filter((e) => !e.closest("li li"));
find.addEventListener("input", () => {
  const q = find.value.trim().toLowerCase();
  for (const e of items) e.classList.toggle("hidden", Boolean(q) && !e.textContent.toLowerCase().includes(q)
    && !(e.tagName === "TR" && e.parentElement.tagName === "THEAD"));
});
</script>
</body>
</html>
"""


def build() -> str:
    with open(SOURCE, encoding="utf-8") as handle:
        body, toc = convert(handle.read())
    sub = ' class="sub"'
    links = "\n".join(f'<a href="#{anchor}"{sub if level == 3 else ""}>{title}</a>'
                      for level, anchor, title in toc)
    return PAGE.replace("{version}", html.escape(version())).replace("{toc}", links).replace("{body}", body)


def main() -> int:
    page = build()
    if "--check" in sys.argv:
        current = open(TARGET, encoding="utf-8").read() if os.path.exists(TARGET) else ""
        if current != page:
            print("docs/usage.html is out of date: run python3 tools/build_usage.py")
            return 1
        return 0
    with open(TARGET, "w", encoding="utf-8") as handle:
        handle.write(page)
    print(TARGET)
    return 0


if __name__ == "__main__":
    sys.exit(main())
