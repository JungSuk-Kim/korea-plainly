#!/usr/bin/env python3
"""A "Try it" section on the home page with our interactive pages (games, checklist, calculator, quiz). Idempotent.

Written as a managed block (<!-- kp-home-tools --> ... <!-- /kp-home-tools -->) right after the
arrival-checklist banner. A tool is shown only once its page exists.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START, END = "<!-- kp-home-tools -->", "<!-- /kp-home-tools -->"
TOOLS = [
    ("learn-hangul.html", "가", "Learn to read Hangul", "Every letter with its sound, a sign-reading quiz and a memory game."),
    ("which-korean-city-quiz.html", "?", "Which city suits you?", "Five quick questions, and Kkachi picks your Korean city."),
    ("korea-trip-cost-calculator.html", "₩", "Trip cost calculator", "Days, travel style and trains in; a budget in won out."),
    ("korea-packing-list.html", "✓", "Packing checklist", "Pick your season and tick things off. Saved and printable."),
]
STYLE = ("<style>.kp-tools{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:30px}"
         ".kp-tools a{display:flex;flex-direction:column;gap:8px;padding:22px 20px;background:#fffdf8;border:1px solid var(--line);"
         "color:inherit;text-decoration:none;transition:transform .15s,border-color .15s}"
         ".kp-tools a:hover{transform:translateY(-3px);border-color:#c9413a}"
         ".kp-tools i{font-style:normal;display:flex;align-items:center;justify-content:center;width:52px;height:52px;border-radius:50%;"
         "background:#17243c;color:#fff;font-size:24px;font-weight:700}"
         ".kp-tools b{font-size:19px;letter-spacing:-.02em;line-height:1.25}.kp-tools small{font-size:14px;line-height:1.5;color:var(--muted)}"
         ".kp-tools span{margin-top:auto;font-size:13px;font-weight:700;color:#c9413a}"
         ".kp-tools-head{display:flex;align-items:flex-end;gap:16px}.kp-tools-head img{width:70px;height:auto;margin:0}"
         "@media(max-width:900px){.kp-tools{grid-template-columns:repeat(2,1fr)}}"
         "@media(max-width:520px){.kp-tools{grid-template-columns:1fr}.kp-tools a{flex-direction:row;flex-wrap:wrap;align-items:center}"
         ".kp-tools small{flex-basis:100%}}</style>")


def block(nl):
    cards = "".join(f'<a href="{href}"><i aria-hidden="true">{icon}</i><b>{html.escape(t)}</b><small>{html.escape(d)}</small>'
                    f'<span>Try it →</span></a>' for href, icon, t, d in TOOLS if (ROOT / href).exists())
    if not cards:
        return ""
    inner = (STYLE + '<section class="wrap section" id="tools"><div class="heading"><div class="kp-tools-head">'
             '<img src="kkachi.png" alt="Kkachi the magpie" width="70" height="76" loading="lazy"><div>'
             '<p class="kicker"><i></i> TRY IT</p><h2>Play, plan<br><em>and pack.</em></h2></div></div></div>'
             f'<div class="kp-tools">{cards}</div></section>')
    return START + nl + inner + nl + END


def main():
    p = ROOT / "index.html"
    s = p.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in s else "\n"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END) + r"\r?\n?", "", s, flags=re.S)
    b = block(nl)
    m = re.search(r'<section class="wrap kp-arrive".*?</section>\r?\n?', new, re.S)
    if b and m:
        new = new[:m.end()] + b + nl + new[m.end():]
    if new != s:
        p.write_bytes(new.encode("utf-8"))
    print(f"home_tools: {'updated' if new != s else 'unchanged'}")


if __name__ == "__main__":
    main()
