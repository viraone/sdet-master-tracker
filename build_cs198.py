from pathlib import Path
import html
import re

MAIN_SOURCE = Path('/Users/viradeth/.codex/attachments/2f0143b7-89a1-4f6e-8a1f-3c2e6d9b913b/pasted-text.txt')
ACT0_SOURCE = Path('/Users/viradeth/.codex/attachments/f827216e-9efc-4429-8a21-417e3ecdc757/pasted-text.txt')
OUT = Path('cs198-analogy.html')

# Act I's territory (VS Code / conftest.py / venv onboarding) is told in full,
# richer detail by ACT0_SOURCE, which replaces it in the final article.
SKIP_CHAPTERS = {'🎬 ACT I: THE BLUEPRINT INCEPTION IN VS CODE'}

ROLE_PREFIXES = (
    ('🏬 The Mall Metaphor:', 'mall', 'Mall metaphor'),
    ('⚙️ The Silicon Reality:', 'silicon', 'Silicon reality'),
    ('💡 THE WHY:', 'why', 'Why it matters'),
)

LANG_NAMES = {'python': 'Python', 'json': 'JSON', 'http': 'HTTP', 'text': 'System map'}


def esc(value):
    return html.escape(value, quote=False)


def is_chapter(line):
    return bool(re.match(r'^(?:🗺️|🏛️|🎬|🛡️|📋)\s', line))


def is_h3(line):
    return bool(re.match(r'^\d+\.\s+', line))


def match_role(line):
    for prefix, css, label in ROLE_PREFIXES:
        if line.startswith(prefix):
            return css, label, line[len(prefix):].strip()
    return None


def load_lines(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith('Model '):
        lines = lines[1:]
    return lines


# ---------------------------------------------------------------------------
# MAIN_SOURCE parser: unchanged from the original script's behavior (inline
# "🏬 The Mall Metaphor: text" labels, one line per insight, no persistence
# across code blocks). Only addition: chapters in SKIP_CHAPTERS are dropped.
# ---------------------------------------------------------------------------

def parse_main_chapters(lines):
    chapters = []  # list of {'slug', 'title', 'body': [html strings]}
    current = None
    skipping = False
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line == 'code' and i + 1 < len(lines):
            lang = lines[i + 1].strip().lower()
            i += 2
            block = []
            while i < len(lines):
                candidate = lines[i].rstrip()
                stripped = candidate.strip()
                if stripped == 'code' or is_chapter(stripped) or is_h3(stripped):
                    break
                block.append(candidate)
                i += 1
            while block and not block[-1].strip():
                block.pop()
            if not skipping and current is not None:
                language = LANG_NAMES.get(lang, lang.title())
                current['body'].append(
                    f'<figure class="code-panel"><figcaption>{language}</figcaption>'
                    f'<pre><code>{esc(chr(10).join(block))}</code></pre></figure>'
                )
            continue

        if is_chapter(line):
            skipping = line in SKIP_CHAPTERS
            if skipping:
                current = None
                i += 1
                continue
            slug = re.sub(r'[^a-z0-9]+', '-', line.lower()).strip('-')
            current = {'slug': slug, 'title': line, 'body': []}
            chapters.append(current)
            i += 1
            continue

        if skipping or current is None:
            i += 1
            continue

        if is_h3(line):
            current['body'].append(f'<h3>{esc(line)}</h3>')
            i += 1
            continue

        role = match_role(line)
        if role:
            css, label, text = role
            current['body'].append(f'<div class="insight {css}"><span>{label}</span><p>{esc(text)}</p></div>')
            i += 1
            continue

        if '\t' in lines[i]:
            rows = []
            while i < len(lines):
                if '\t' not in lines[i]:
                    if rows and lines[i].strip() in {'→', 'AST', 'Bytecode'}:
                        rows[-1][-1] += ' ' + lines[i].strip()
                        i += 1
                        continue
                    break
                cells = lines[i].split('\t')
                if rows and not (cells[0].isdigit() or cells[0] == 'Stage'):
                    rows[-1][-1] += ' ' + cells[0].strip()
                    if len(cells) > 1:
                        rows[-1].extend(cells[1:])
                else:
                    rows.append(cells)
                i += 1
            table = ['<div class="matrix"><table>']
            for rix, row in enumerate(rows):
                tag = 'th' if rix == 0 else 'td'
                table.append('<tr>' + ''.join(f'<{tag}>{esc(cell)}</{tag}>' for cell in row) + '</tr>')
            table.append('</table></div>')
            current['body'].append('\n'.join(table))
            continue

        current['body'].append(f'<p>{esc(line)}</p>')
        i += 1

    return chapters


# ---------------------------------------------------------------------------
# ACT0_SOURCE parser: handles the "label alone on its own line, narrative
# spread over the following lines, code blocks free to interrupt" format.
# A role (mall/silicon/why) only ever applies to the contiguous run of plain
# lines between two markers (label / code / heading) - it never survives a
# code block or heading on its own; the source must re-declare the label
# explicitly to reopen an insight box. This mirrors how the existing,
# hand-written sections in this file already behave.
# ---------------------------------------------------------------------------

def is_act0_h3(line):
    return bool(is_h3(line) or line.startswith('Step ') or line.startswith('📋'))


def parse_act0_chapter(lines):
    heading_i = next(i for i, l in enumerate(lines) if is_chapter(l.strip()))
    intro = [l.strip() for l in lines[:heading_i] if l.strip()]
    title = lines[heading_i].strip()
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    body = [f'<p>{esc(p)}</p>' for p in intro]

    buf = []
    role = None

    def flush():
        nonlocal buf, role
        if buf:
            content = '<br>'.join(esc(b) for b in buf)
            if role:
                css, label = role
                body.append(f'<div class="insight {css}"><span>{label}</span><p>{content}</p></div>')
            else:
                body.append(f'<p>{content}</p>')
            buf = []
        role = None

    lines = lines[heading_i + 1:]
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        if not line:
            i += 1
            continue

        if line == 'code' and i + 1 < len(lines):
            flush()
            lang = lines[i + 1].strip()
            i += 2
            block = []
            while i < len(lines):
                candidate = lines[i].rstrip()
                stripped = candidate.strip()
                if stripped == 'code' or is_chapter(stripped) or is_act0_h3(stripped) or match_role(stripped):
                    break
                block.append(candidate)
                i += 1
            while block and not block[-1].strip():
                block.pop()
            body.append(
                f'<figure class="code-panel"><figcaption>{esc(lang)}</figcaption>'
                f'<pre><code>{esc(chr(10).join(block))}</code></pre></figure>'
            )
            continue

        if line.startswith('📋'):
            flush()
            body.append(f'<h3>{esc(line)}</h3>')
            i += 1
            continue

        if '\t' in raw:
            flush()
            rows = []
            while i < len(lines) and '\t' in lines[i]:
                rows.append(lines[i].split('\t'))
                i += 1
            table = ['<div class="matrix"><table>']
            for rix, row in enumerate(rows):
                tag = 'th' if rix == 0 else 'td'
                table.append('<tr>' + ''.join(f'<{tag}>{esc(cell)}</{tag}>' for cell in row) + '</tr>')
            table.append('</table></div>')
            body.append('\n'.join(table))
            continue

        if is_act0_h3(line):
            flush()
            body.append(f'<h3>{esc(line)}</h3>')
            i += 1
            continue

        matched = match_role(line)
        if matched:
            flush()
            css, label, text = matched
            role = (css, label)
            if text:
                buf.append(text)
            i += 1
            continue

        buf.append(line)
        i += 1

    flush()
    return {'slug': slug, 'title': title, 'body': body}


def render_chapters(chapters):
    toc = []
    body = []
    for n, chapter in enumerate(chapters, start=1):
        toc.append((chapter['slug'], chapter['title']))
        chapter_title = '' if n == 1 else f'<h2>{esc(chapter["title"])}</h2>'
        body.append(f'<section id="{chapter["slug"]}" class="chapter"><div class="chapter-kicker">Chapter {n:02d}</div>{chapter_title}')
        body.extend(chapter['body'])
        body.append('</section>')
    return toc, body


def main():
    main_lines = load_lines(MAIN_SOURCE)
    title = main_lines.pop(0).strip()
    subtitle = main_lines.pop(0).strip()

    main_chapters = parse_main_chapters(main_lines)
    act0_chapter = parse_act0_chapter(load_lines(ACT0_SOURCE))

    prologue_idx = next(i for i, c in enumerate(main_chapters) if c['title'].startswith('🏛️'))
    final_chapters = main_chapters[:prologue_idx + 1] + [act0_chapter] + main_chapters[prologue_idx + 1:]

    toc, body = render_chapters(final_chapters)

    toc_html = ''.join(f'<a href="#{slug}"><span>{n:02d}</span>{esc(label)}</a>' for n, (slug, label) in enumerate(toc, 1))
    article_html = '\n'.join(body)

    page = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="CS 198 advanced mobile test infrastructure and systems architecture">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ --ink:#e8edf6; --muted:#95a1b5; --panel:#111827; --line:#283449; --blue:#65a7ff; --cyan:#56d5d0; --gold:#f5c86b; --purple:#b89cff; }}
    * {{ box-sizing:border-box }}
    html {{ scroll-behavior:smooth }}
    body {{ margin:0; color:var(--ink); background:#07101d; font:16px/1.72 ui-serif,Georgia,Cambria,"Times New Roman",Times,serif; }}
    body:before {{ content:""; position:fixed; inset:0; z-index:-1; background:radial-gradient(circle at 78% 4%,rgba(53,111,187,.22),transparent 33rem),radial-gradient(circle at 5% 50%,rgba(64,184,174,.1),transparent 28rem); }}
    .hero {{ min-height:72vh; display:grid; place-items:center; border-bottom:1px solid var(--line); padding:7rem 1.5rem; overflow:hidden; position:relative; }}
    .hero:after {{ content:"M5 MAX  /  XNU  /  W3C  /  TCP-IP  /  APPIUM"; position:absolute; bottom:1.5rem; color:#516079; font:700 .66rem/1 ui-monospace,monospace; letter-spacing:.22em; }}
    .hero-inner {{ width:min(1040px,100%); }}
    .eyebrow,.chapter-kicker {{ color:var(--cyan); text-transform:uppercase; letter-spacing:.18em; font:800 .72rem/1.4 ui-monospace,monospace; }}
    h1 {{ max-width:980px; margin:.7rem 0 1.2rem; font-size:clamp(2.7rem,7vw,6.8rem); line-height:.93; letter-spacing:-.065em; }}
    .subtitle {{ color:var(--muted); max-width:760px; font-size:clamp(1.05rem,2vw,1.35rem); }}
    .shell {{ width:min(1440px,100%); margin:auto; display:grid; grid-template-columns:300px minmax(0,860px); gap:5rem; padding:5rem 2rem 9rem; justify-content:center; }}
    nav {{ position:sticky; top:2rem; align-self:start; max-height:calc(100vh - 4rem); overflow:auto; padding-right:1rem; }}
    nav h2 {{ font-size:.72rem; color:#708098; text-transform:uppercase; letter-spacing:.18em; margin:0 0 1rem; }}
    nav a {{ display:grid; grid-template-columns:2rem 1fr; gap:.5rem; color:#9ba8bb; text-decoration:none; font-size:.78rem; line-height:1.35; padding:.62rem 0; border-bottom:1px solid rgba(255,255,255,.055); }}
    nav a:hover {{ color:white }} nav a span {{ color:#4f6788; font-family:ui-monospace,monospace; }}
    article {{ min-width:0 }}
    .chapter {{ padding:0; scroll-margin-top:2rem; }}
    article > .chapter:first-child {{ padding-top:0; }}
    .chapter > :last-child {{ margin-bottom:0; }}
    .chapter + .chapter {{ border-top:1px solid var(--line); padding-top:.75rem; }}
    h2 {{ color:var(--ink); font-size:clamp(1.8rem,4vw,3.2rem); line-height:1.07; letter-spacing:-.04em; margin:.25rem 0 .75rem; }}
    h3 {{ margin:2.7rem 0 1rem; font-size:1.25rem; line-height:1.3; color:#fff; }}
    p {{ color:#c3cbd8; margin:.9rem 0; }}
    code,pre {{ font-family:"SFMono-Regular",Consolas,"Liberation Mono",monospace; }}
    .code-panel {{ margin:2rem 0; background:#060b13; border:1px solid #26334a; border-radius:16px; overflow:hidden; box-shadow:0 18px 50px rgba(0,0,0,.22); }}
    .chapter h2 + .code-panel {{ margin-top:0; }}
    .chapter-kicker + .code-panel {{ margin-top:.25rem; }}
    .code-panel figcaption {{ padding:.65rem 1rem; border-bottom:1px solid #26334a; color:#6f819d; text-transform:uppercase; letter-spacing:.14em; font:700 .65rem/1 ui-monospace,monospace; }}
    pre {{ margin:0; padding:1.4rem; overflow:auto; color:#afd4ff; font-size:.78rem; line-height:1.45; }}
    .insight {{ margin:1rem 0; padding:1.1rem 1.25rem; border:1px solid var(--line); border-left-width:4px; border-radius:0 12px 12px 0; background:rgba(17,24,39,.72); }}
    .insight span {{ display:block; margin-bottom:.3rem; text-transform:uppercase; letter-spacing:.13em; font:800 .65rem/1.2 ui-monospace,monospace; }}
    .insight p {{ margin:0; color:#d2d9e5; white-space:pre-wrap; overflow-wrap:anywhere; }}
    .mall {{ border-left-color:var(--gold) }} .mall span {{ color:var(--gold) }}
    .silicon {{ border-left-color:var(--blue) }} .silicon span {{ color:var(--blue) }}
    .why {{ border-left-color:var(--purple) }} .why span {{ color:var(--purple) }}
    .matrix {{ overflow:auto; margin-top:2rem; border:1px solid var(--line); border-radius:14px; }}
    table {{ border-collapse:collapse; min-width:980px; font-size:.82rem; line-height:1.5; }}
    th,td {{ padding:.9rem; text-align:left; vertical-align:top; border:1px solid var(--line); }}
    th {{ color:#fff; background:#172236; }} td {{ color:#b9c3d2; }}
    .top {{ position:fixed; right:1.25rem; bottom:1.25rem; width:44px; height:44px; display:grid; place-items:center; border:1px solid #33445f; border-radius:50%; color:white; background:#111c2d; text-decoration:none; box-shadow:0 8px 30px #0008; }}
    @media(max-width:980px) {{ .shell {{ display:block; padding:3rem 1.2rem 7rem }} nav {{ position:relative; top:auto; max-height:none; margin-bottom:4rem; padding:1.2rem; border:1px solid var(--line); border-radius:14px; }} }}
    @media(max-width:600px) {{ .hero {{ min-height:64vh; padding:5rem 1.2rem }} h1 {{ font-size:2.65rem }} pre {{ font-size:.68rem }} .chapter+.chapter {{ padding-top:.75rem }} }}
  </style>
</head>
<body id="top">
  <header class="hero"><div class="hero-inner"><div class="eyebrow">Advanced systems lecture · Module 01</div><h1>{html.escape(title)}</h1><p class="subtitle">{html.escape(subtitle)}</p></div></header>
  <div class="shell">
    <nav aria-label="Course chapters"><h2>Course map</h2>{toc_html}</nav>
    <article>{article_html}</article>
  </div>
  <a class="top" href="#top" aria-label="Back to top">↑</a>
</body>
</html>'''

    OUT.write_text(page, encoding='utf-8')
    print(f'Wrote {OUT} ({len(page):,} bytes, {len(toc)} chapters)')


if __name__ == '__main__':
    main()
