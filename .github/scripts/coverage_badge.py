"""Print a shields.io-style SVG coverage badge for the given percentage."""

import sys

COLORS = [(90, "#4c1"), (75, "#97ca00"), (60, "#dfb317"), (40, "#fe7d37")]


def badge(percent: int) -> str:
    color = next((c for limit, c in COLORS if percent >= limit), "#e05d44")
    value = f"{percent}%"
    lw, vw = 61, 8 + 7 * len(value)
    w = lw + vw
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="20" role="img" aria-label="coverage: {value}">
<title>coverage: {value}</title>
<linearGradient id="s" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
<clipPath id="r"><rect width="{w}" height="20" rx="3" fill="#fff"/></clipPath>
<g clip-path="url(#r)"><rect width="{lw}" height="20" fill="#555"/><rect x="{lw}" width="{vw}" height="20" fill="{color}"/><rect width="{w}" height="20" fill="url(#s)"/></g>
<g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">
<text x="{lw / 2}" y="15" fill="#010101" fill-opacity=".3">coverage</text><text x="{lw / 2}" y="14">coverage</text>
<text x="{lw + vw / 2}" y="15" fill="#010101" fill-opacity=".3">{value}</text><text x="{lw + vw / 2}" y="14">{value}</text>
</g>
</svg>
"""


if __name__ == "__main__":
    sys.stdout.write(badge(round(float(sys.argv[1]))))
