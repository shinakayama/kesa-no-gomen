"""Convert an issue HTML into an email-safe HTML (inlined CSS, no CSS variables).

Usage: python3 scripts/email_html.py issues/kesa-no-gomen_YYYYMMDD.html out.html
Requires: pip install premailer
"""
import re
import sys

from premailer import transform

# Mail clients (Gmail in particular) ignore CSS variables, grid and multi-column,
# and drop a whole <style> block that contains selectors they dislike.
EMAIL_OVERRIDES = """
.sheet{max-width:680px;margin:0 auto;}
.top,.grid,.grid.two,.column,.broadsheet{display:block;columns:auto;}
.two-col,.quotes,.lede,.rail-note{columns:auto;}
.rail{border-left:0;padding-left:0;margin-top:22px;padding-top:16px;border-top:1px solid #000000;}
article.story{border-left:0;padding-left:0;padding-top:16px;border-top:1px solid #D8D6CA;}
.column{margin-top:28px;}
.sources{margin-top:24px;}
"""


def strip_block(css: str, header_pattern: str) -> str:
    """Remove every at-rule/selector block whose header matches, honouring nested braces."""
    out, pos = [], 0
    for m in re.finditer(header_pattern, css):
        if m.start() < pos:
            continue
        brace = css.find("{", m.end() - 1)
        depth, i = 0, brace
        while i < len(css):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append(css[pos:m.start()])
        pos = i + 1
    out.append(css[pos:])
    return "".join(out)


def main(src: str, dst: str) -> None:
    html = open(src, encoding="utf-8").read()
    style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)

    root = re.search(r":root\{(.*?)\}", style, re.S).group(1)
    tokens = dict(re.findall(r"--([\w-]+):\s*([^;]+);", root))

    css = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
    for header in (r"@media[^{]*\{", r"@page[^{]*\{", r"@keyframes[^{]*\{", r":root[^{]*\{"):
        css = strip_block(css, header)
    css += EMAIL_OVERRIDES

    def resolve(m):
        return tokens[m.group(1)].strip()

    for _ in range(3):
        css = re.sub(r"var\(--([\w-]+)\)", resolve, css)

    body = html[html.index("</style>") + len("</style>"):]
    doc = (
        '<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8">'
        f"<style>{css}</style></head>"
        f'<body style="margin:0;padding:12px;background:{tokens["paper"].strip()};">{body}</body></html>'
    )
    inlined = transform(doc, keep_style_tags=False, remove_classes=True,
                        disable_validation=True, cssutils_logging_level="CRITICAL")
    inlined = re.sub(r"<style>.*?</style>", "", inlined, flags=re.S)
    # clamp() is unsupported in most mail clients; use the upper bound.
    inlined = re.sub(r"clamp\([^,]+,[^,]+,\s*([^)]+)\)", r"\1", inlined)
    for stack, short in (
        # premailer wraps these attributes in single quotes, so the stacks must use double quotes.
        ('"Shippori Mincho B1", "Noto Serif JP", "Hiragino Mincho ProN", serif', '"Hiragino Mincho ProN",serif'),
        ('"Noto Serif JP", "Hiragino Mincho ProN", "Yu Mincho", serif', '"Hiragino Mincho ProN","Yu Mincho",serif'),
        ('"Noto Sans JP", "Hiragino Kaku Gothic ProN", "Yu Gothic", system-ui, sans-serif', '"Hiragino Sans","Yu Gothic",sans-serif'),
    ):
        inlined = inlined.replace(stack, short)
    useless = (r"(?:page-)?break-(?:inside|after|before)|text-underline-offset|text-decoration-thickness"
               r"|text-wrap|grid-template-columns|column-gap|column-rule|columns|font-variant-numeric"
               r"|-webkit-font-smoothing|box-shadow|min-width")
    inlined = re.sub(rf"\s*(?:{useless}):[^;\"']*;?", "", inlined)
    inlined = re.sub(r"<!--.*?-->", "", inlined, flags=re.S)
    inlined = re.sub(r">\s+<", "><", inlined)
    inlined = re.sub(r"[ \t]*\n[ \t]*", "\n", inlined)
    inlined = re.sub(r"(</(?:p|div|article|li|h3)>)", r"\1\n", inlined)
    open(dst, "w", encoding="utf-8").write(inlined)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
