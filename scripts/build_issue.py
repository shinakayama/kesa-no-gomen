"""Build an issue HTML from a content JSON and template.html.

Usage: python3 scripts/build_issue.py issues/data/YYYYMMDD.json
Writes issues/kesa-no-gomen_YYYYMMDD.html and records the headlines in issues/headlines.json.

Content JSON (text fields may contain inline HTML such as <br>, <b>, &amp;):
{
  "date": "2026-09-25",
  "lead": {"kicker": "一面トップ ／ 国際・AI", "head": "...", "sub": ["1行目", "2行目"],
           "lede": "...", "body": ["段落", ...], "sources": [SOURCE, ...]},
  "quotes": [{"name": "日経平均株価", "note": "（25日終値）", "value": "66,364.20", "unit": "円",
              "diff": "＋850.21", "dir": "up|dn|flat"}, ...],
  "rail_note": "相場欄の注記",
  "weather": {"meta": "東京・25日", "icon": "🌦️", "cond": "曇時々雨", "hi": "26℃", "lo": "21℃",
              "pop": "80%", "note": "<b>きょう25日</b>　...", "sources": [SOURCE, ...]},
  "sections": [{"name": "技術面", "meta": "開発基盤・クラウド", "layout": "grid|two",
                "stories": [{"sode": "袖見出し", "head": "見出し", "paras": ["段落", ...],
                             "figure": {"title": "...", "rows": [["左", "右"], ...], "cap": "..."},
                             "figure_after": 1, "sources": [SOURCE, ...]}]}],
  "yoroku": ["段落", ...],
  "extra_sources": [SOURCE, ...],
  "notice": "おことわり本文"
}
SOURCE = {"label": "記事末尾に出す短い名前", "url": "...", "title": "本日の出典に出す題（省略時は label）"}
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRST_ISSUE = date(2026, 9, 9)
WEEKDAYS = "月火水木金土日"


def esc_url(url: str) -> str:
    return re.sub(r"&(?!amp;)", "&amp;", url)


def src_links(sources):
    return "／".join(f'<a href="{esc_url(s["url"])}">{s["label"]}</a>' for s in sources)


def page_label(name, meta=None):
    meta_html = f'<span class="meta">{meta}</span>' if meta else ""
    return (f'<div class="page-label"><span class="mark"></span><h2>{name}</h2>'
            f'<span class="fill"></span>{meta_html}</div>')


def figure(fig):
    rows = "\n".join(f"              <tr><th>{a}</th><td>{b}</td></tr>" for a, b in fig["rows"])
    return f"""        <div class="figure-box">
          <h4>{fig["title"]}</h4>
          <table>
            <tbody>
{rows}
            </tbody>
          </table>
          <p class="cap">{fig["cap"]}</p>
        </div>"""


def story(st):
    paras = [f"        <p>{p}</p>" for p in st["paras"]]
    if st.get("figure"):
        paras.insert(st.get("figure_after", len(paras)), figure(st["figure"]))
    body = "\n".join(paras)
    return f"""      <article class="story">
        <p class="sode">{st["sode"]}</p>
        <h3>{st["head"]}</h3>
{body}
        <p class="src">出典：{src_links(st["sources"])}</p>
      </article>"""


def section(sec):
    grid = "grid two" if sec.get("layout") == "two" else "grid"
    stories = "\n".join(story(st) for st in sec["stories"])
    return f"""  <!-- ── {sec["name"]} ── -->
  <section class="section">
    {page_label(sec["name"], sec.get("meta"))}
    <div class="{grid}">
{stories}
    </div>
  </section>
"""


def quote_row(q):
    cls = {"up": "d up", "dn": "d dn"}.get(q.get("dir"), "d")
    unit = f' <span class="unit">{q["unit"]}</span>' if q.get("unit") else ""
    return (f'        <div class="q"><span class="n">{q["name"]}<br><span class="unit">{q["note"]}</span></span>'
            f'<span class="vv"><span class="v">{q["value"]}{unit}</span><span class="{cls}">{q["diff"]}</span></span></div>')


def all_sources(c):
    seen, out = set(), []
    groups = [c["lead"]["sources"]]
    groups += [st["sources"] for sec in c["sections"] for st in sec["stories"]]
    groups += [c.get("extra_sources", []), c["weather"]["sources"]]
    for group in groups:
        for s in group:
            if s["url"] not in seen:
                seen.add(s["url"])
                out.append(s)
    return out


def build(c) -> str:
    d = date.fromisoformat(c["date"])
    number = (d - FIRST_ISSUE).days + 1
    lead, wx = c["lead"], c["weather"]

    template = (ROOT / "template.html").read_text(encoding="utf-8")
    head = template[: template.index("</style>") + len("</style>")]

    sub = "<br>".join(lead["sub"])
    lead_body = "\n".join(f"        <p>{p}</p>" for p in lead["body"])
    quotes = "\n".join(quote_row(q) for q in c["quotes"])
    sections = "\n".join(section(s) for s in c["sections"])
    yoroku = "\n".join(f"      <p>{p}</p>" for p in c["yoroku"])
    source_items = "\n".join(
        f'        <li><a href="{esc_url(s["url"])}">{s.get("title") or s["label"]}</a></li>'
        for s in all_sources(c))

    return f"""{head}

<div class="sheet">

  <header class="masthead">
    <div class="title-lockup">
      <h1 class="nameplate">けさの五面<span class="dot">・</span></h1>
    </div>
    <p class="colophon">
      <b>{d.year}年（令和{d.year - 2018}年）{d.month}月{d.day}日 {WEEKDAYS[d.weekday()]}曜日</b><br>
      第{number}号（{c.get("edition", "第4版")}）／朝刊／6面立て<br>
      編集 Claude Code ／ 出典はウェブ検索
    </p>
  </header>
  <div class="hairline"></div>

  <!-- ── 一面トップ ── -->
  <div class="top">
    <div class="lead">
      <p class="kicker">{lead["kicker"]}</p>
      <h2 class="lead-head">{lead["head"]}</h2>
      <p class="lead-sub">{sub}</p>
      <p class="lede">
        {lead["lede"]}
      </p>
      <div class="two-col">
{lead_body}
      </div>
      <p class="src">出典：{src_links(lead["sources"])}</p>
    </div>

    <aside class="rail">
      {page_label("相場・指標")}
      <div class="quotes">
{quotes}
      </div>
      <p class="rail-note">{c["rail_note"]}</p>

      <div class="wx">
        {page_label("天気", wx["meta"])}
        <div class="wx-today">
          <span class="wx-icon" aria-hidden="true">{wx["icon"]}</span>
          <span class="wx-cond">{wx["cond"]}</span>
          <span class="wx-temps"><span class="hi">{wx["hi"]}</span><span class="sep">／</span><span class="lo">{wx["lo"]}</span></span>
          <span class="wx-pop">降水確率<br><b>{wx["pop"]}</b></span>
        </div>
        <p class="rail-note">{wx["note"]}</p>
        <p class="src" style="margin-top:8px;">出典：{src_links(wx["sources"])}</p>
      </div>
    </aside>
  </div>

  <!-- ══ 段組み紙面 ══ -->
  <div class="broadsheet">

{sections}
  <!-- ── コラム ── -->
  <div class="column">
    <div class="yoroku">
      <h3>余録</h3>
{yoroku}
      <p class="sign">──けさの五面</p>
    </div>
    <div class="sources">
      {page_label("本日の出典")}
      <ol>
{source_items}
      </ol>
      <div class="notice">
        <b>おことわり</b><br>
        {c["notice"]}
      </div>
    </div>
  </div>

  </div><!-- /broadsheet -->

</div>
"""


def record_headlines(c):
    path = ROOT / "issues" / "headlines.json"
    index = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    strip = lambda s: re.sub(r"<[^>]+>", "", s)
    entry = {"一面": strip(c["lead"]["head"])}
    for sec in c["sections"]:
        entry[sec["name"]] = [strip(st["head"]) for st in sec["stories"]]
    index[c["date"].replace("-", "")] = entry
    path.write_text(json.dumps(dict(sorted(index.items())), ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")


def main(src: str) -> None:
    c = json.loads(Path(src).read_text(encoding="utf-8"))
    ymd = c["date"].replace("-", "")
    out = ROOT / "issues" / f"kesa-no-gomen_{ymd}.html"
    out.write_text(build(c), encoding="utf-8")
    record_headlines(c)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
