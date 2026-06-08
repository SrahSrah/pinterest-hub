"""Ambient Living Lab — home/lifestyle review journal + tracked-redirect bridge.

Deploy target: the `pinterest-hub` Vercel project. Copy this over
`pinterest-hub/api/index.py`, keep requirements.txt + vercel.json, set the KV
env vars in Vercel, and push.

Routes:
  GET /            -> landing page (hero + featured reviews) — for domain claim
  GET /about       -> about / editorial mission
  GET /p/<slug>    -> full product review page (-> tracked outbound CTA)
  GET /privacy     -> privacy policy + affiliate disclosure
  GET /go/<slug>   -> look up slug in KV, log click, 302 to the affiliate dest

The redirect table lives in Vercel KV (Upstash). The local automation writes
`redirect:<slug>`; this function reads it. Review pages link to /go/<slug> so
on-site clicks are tracked the same way as social clicks.

To make a review's CTA resolve, register its slug in KV, e.g.:
    python scripts/set_redirect.py water-freedom "https://<hoplink>"
(slug must match the product's "slug" in PRODUCTS below).
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from flask import Flask, redirect, request

app = Flask(__name__)

KV_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")


# ---------------------------------------------------------------------------
# Curated catalogue. Add/edit entries here; pages render from this list.
# (Later this can be auto-populated from the affiliate DB / KV.)
# ---------------------------------------------------------------------------
PRODUCTS = [
    {
        "slug": "backyard-greenhouse",
        "name": "Backyard Greenhouse Blueprints",
        "category": "Garden",
        "rating": 4.5,
        "blurb": "A step-by-step DIY plan for a year-round backyard greenhouse — "
                 "thoughtful, approachable, and genuinely buildable.",
        "review": [
            "There's a particular kind of satisfaction in growing food a few steps "
            "from your kitchen door, and a small greenhouse is the difference "
            "between a summer hobby and a year-round habit.",
            "What we like about this guide is its restraint: it doesn't assume a "
            "contractor's toolkit or a designer's budget. The plans are clear, the "
            "material lists are honest, and the result is a structure that looks "
            "intentional in a real backyard rather than improvised.",
            "Best for the weekend builder who wants a beautiful, functional grow "
            "space without paying for a prefab kit.",
        ],
        "cta": "See the blueprints",
    },
    {
        "slug": "water-freedom",
        "name": "Water Freedom System",
        "category": "Sustainable Home",
        "rating": 4.0,
        "blurb": "A practical guide to home water resilience — sensible, clearly "
                 "explained, and aimed at everyday preparedness rather than panic.",
        "review": [
            "Water is the one utility we take entirely for granted until a storm or "
            "an outage makes us think about it. This guide approaches the topic "
            "calmly: how household water systems work, and how to build a sensible "
            "backup for your home.",
            "We appreciate that it stays grounded and instructional instead of "
            "leaning on fear. The strongest sections are the practical walkthroughs "
            "and the realistic shopping lists.",
            "Best for homeowners who want a reasonable level of self-sufficiency and "
            "peace of mind, without turning the garage into a bunker.",
        ],
        "cta": "Read the guide",
    },
    {
        "slug": "sewing-library",
        "name": "The Sewing Pattern Library",
        "category": "Craft & Home",
        "rating": 4.5,
        "blurb": "A deep, well-organized library of sewing patterns — the kind of "
                 "resource that quietly pays for itself the first month you use it.",
        "review": [
            "Mending, making, and altering are skills that feel newly relevant — "
            "part thrift, part craft, part the simple pleasure of making something "
            "with your hands.",
            "This library stands out for breadth and organization: patterns for home "
            "goods, garments, gifts and repairs, sorted so you can actually find what "
            "you need on a Sunday afternoon. The instructions are beginner-friendly "
            "without being condescending.",
            "Best for anyone setting up a craft corner who wants one reliable source "
            "instead of a hundred scattered PDFs.",
        ],
        "cta": "Browse the library",
    },
]
_BY_SLUG = {p["slug"]: p for p in PRODUCTS}


# ---------------------------------------------------------------------------
# KV helpers (redirect bridge)
# ---------------------------------------------------------------------------
def _kv(*segments, body=None):
    if not (KV_URL and KV_TOKEN):
        return None
    path = "/".join(urllib.parse.quote(s, safe="") for s in segments)
    data = body.encode("utf-8") if body is not None else b""
    req = urllib.request.Request(
        f"{KV_URL.rstrip('/')}/{path}", data=data, method="POST",
        headers={"Authorization": f"Bearer {KV_TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8")).get("result")
    except Exception:
        return None


def _append_query(url, key, value):
    parts = urllib.parse.urlsplit(url)
    q = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    q[key] = value
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))


# ---------------------------------------------------------------------------
# Page shell
# ---------------------------------------------------------------------------
_CSS = """
:root{--bg:#F7F4EE;--ink:#2b2926;--muted:#6f6a62;--line:#e7e1d6;--accent:#b4552f;--card:#fffdf9}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:Georgia,'Iowan Old Style','Palatino Linotype',serif;line-height:1.65}
a{color:inherit}
.wrap{max-width:1040px;margin:0 auto;padding:0 24px}
header.site{border-bottom:1px solid var(--line);background:rgba(247,244,238,.85);
  backdrop-filter:blur(6px);position:sticky;top:0;z-index:10}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;height:68px}
.brand{font-size:20px;letter-spacing:.3px;text-decoration:none}
.brand b{font-weight:600}
nav a{margin-left:24px;text-decoration:none;color:var(--muted);font-size:15px}
nav a:hover{color:var(--accent)}
.hero{padding:84px 0 56px;border-bottom:1px solid var(--line)}
.hero h1{font-size:46px;line-height:1.12;font-weight:600;margin:0 0 18px;max-width:14ch}
.hero p{font-size:20px;color:var(--muted);max-width:60ch;margin:0}
.kicker{text-transform:uppercase;letter-spacing:.18em;font-size:12px;color:var(--accent);
  font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0 0 18px}
section{padding:56px 0}
h2.section{font-size:14px;text-transform:uppercase;letter-spacing:.16em;color:var(--muted);
  font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0 0 28px;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:22px}
.card{display:block;text-decoration:none;background:var(--card);border:1px solid var(--line);
  border-radius:14px;padding:26px;transition:transform .15s ease,box-shadow .15s ease}
.card:hover{transform:translateY(-3px);box-shadow:0 12px 30px rgba(80,60,40,.10)}
.cat{font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:11px;text-transform:uppercase;
  letter-spacing:.14em;color:var(--accent)}
.card h3{font-size:23px;margin:10px 0 8px;font-weight:600}
.stars{color:var(--accent);font-size:15px;margin-bottom:10px}
.rate{color:var(--muted);font-size:13px;font-family:-apple-system,Segoe UI,sans-serif}
.card p{color:var(--muted);font-size:16px;margin:0 0 16px}
.more{font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px;color:var(--accent)}
article.review{max-width:680px;margin:0 auto}
article.review .cat{font-size:12px}
article.review h1{font-size:38px;font-weight:600;margin:10px 0 6px}
article.review p{font-size:19px;color:#3c3934}
.cta{display:inline-block;margin:14px 0 8px;background:var(--accent);color:#fff;
  text-decoration:none;padding:14px 26px;border-radius:40px;font-family:-apple-system,Segoe UI,sans-serif;
  font-size:16px}
.cta:hover{filter:brightness(1.05)}
.disc{font-size:14px;color:var(--muted);border-top:1px solid var(--line);padding-top:16px;margin-top:28px}
.prose p{font-size:18px;color:#3c3934;max-width:68ch}
footer.site{border-top:1px solid var(--line);margin-top:40px;padding:40px 0;color:var(--muted);font-size:14px}
footer.site a{color:var(--muted)}
footer.site .row{display:flex;justify-content:space-between;flex-wrap:wrap;gap:16px}
"""

_NAV = ('<header class="site"><div class="wrap">'
        '<a class="brand" href="/">Ambient Living <b>Lab</b></a>'
        '<nav><a href="/">Reviews</a><a href="/about">About</a>'
        '<a href="/privacy">Privacy</a></nav></div></header>')

_FOOTER = ('<footer class="site"><div class="wrap"><div class="row">'
           '<div>© 2026 Ambient Living Lab — a home &amp; lifestyle review journal.</div>'
           '<div><a href="/privacy">Privacy &amp; Disclosure</a></div></div>'
           '<p style="margin-top:16px;max-width:70ch">Ambient Living Lab is reader-supported. '
           'Some links are affiliate links — if you buy through them we may earn a commission '
           'at no extra cost to you. We only feature things we would genuinely recommend.</p>'
           '</div></footer>')


def _page(title, body):
    return ("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
            "<meta name=\"description\" content=\"Ambient Living Lab — honest reviews and "
            "curation for a more beautiful, functional home and life.\">"
            f"<title>{title}</title><style>{_CSS}</style></head><body>"
            f"{_NAV}{body}{_FOOTER}</body></html>")


def _stars(rating):
    full = int(rating)
    half = 1 if rating - full >= 0.5 else 0
    return "★" * full + ("⯨" if half else "") + "☆" * (5 - full - half)


def _card(p):
    return (f'<a class="card" href="/p/{p["slug"]}">'
            f'<span class="cat">{p["category"]}</span>'
            f'<h3>{p["name"]}</h3>'
            f'<div class="stars">{_stars(p["rating"])} <span class="rate">{p["rating"]:.1f}</span></div>'
            f'<p>{p["blurb"]}</p>'
            f'<span class="more">Read the full review →</span></a>')


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def _home():
    cards = "".join(_card(p) for p in PRODUCTS)
    body = (
        '<div class="hero"><div class="wrap">'
        '<p class="kicker">Home · Lifestyle · Living</p>'
        '<h1>The good stuff, honestly reviewed.</h1>'
        '<p>Ambient Living Lab is a small review journal for a more beautiful, '
        'functional home and life. We test, read, and dig into products across home, '
        'garden, kitchen, craft and wellbeing — and write up only the ones worth your time.</p>'
        '</div></div>'
        '<section><div class="wrap">'
        '<h2 class="section">Featured Reviews</h2>'
        f'<div class="grid">{cards}</div>'
        '</div></section>')
    return _page("Ambient Living Lab — Home & Lifestyle Reviews", body)


def _about():
    body = (
        '<section><div class="wrap prose" style="max-width:720px">'
        '<p class="kicker">About</p>'
        '<h1 style="font-size:40px;font-weight:600;margin:0 0 20px">Why we made this</h1>'
        '<p>Ambient Living Lab started from a simple frustration: it is genuinely hard to '
        'find honest, unhurried opinions about the things we bring into our homes. Most '
        '"reviews" online are thin, breathless, or quietly identical to one another.</p>'
        '<p>So we keep a journal instead. We pick a handful of products across home, garden, '
        'kitchen, craft and wellbeing, spend real time with them, and write up what we found — '
        'what they are, who they are for, and where they fall short.</p>'
        '<p>We are reader-supported. When a review links out to a product, that link is often '
        'an affiliate link, which means we may earn a small commission if you buy. It never '
        'changes our opinion or costs you anything extra, and we only feature things we would '
        'recommend to a friend.</p>'
        '<p style="margin-top:28px"><a class="cta" href="/">Browse the reviews</a></p>'
        '</div></section>')
    return _page("About — Ambient Living Lab", body)


def _review(p):
    paras = "".join(f"<p>{para}</p>" for para in p["review"])
    body = (
        '<section><div class="wrap"><article class="review">'
        f'<span class="cat">{p["category"]}</span>'
        f'<h1>{p["name"]}</h1>'
        f'<div class="stars" style="font-size:18px;margin:6px 0 22px">{_stars(p["rating"])} '
        f'<span class="rate">{p["rating"]:.1f} / 5</span></div>'
        f'{paras}'
        f'<a class="cta" href="/go/{p["slug"]}" rel="sponsored nofollow noopener" '
        f'target="_blank">{p["cta"]} →</a>'
        '<p class="disc">This review contains an affiliate link. If you purchase through it, '
        'Ambient Living Lab may earn a commission at no additional cost to you.</p>'
        '<p style="margin-top:20px"><a class="more" href="/">← All reviews</a></p>'
        '</article></div></section>')
    return _page(f'{p["name"]} — Review · Ambient Living Lab', body)


_PRIVACY_BODY = (
    '<section><div class="wrap prose" style="max-width:720px">'
    '<p class="kicker">Legal</p>'
    '<h1 style="font-size:36px;font-weight:600;margin:0 0 6px">Privacy Policy &amp; Disclosure</h1>'
    '<p style="color:#6f6a62">Last updated: June 2026</p>'
    '<h2 style="font-size:22px;font-weight:600">Information we collect</h2>'
    '<p>Ambient Living Lab is a content and review site. We do not require accounts. When you '
    'click an outbound link we log non-identifying request metadata (timestamp, referring page, '
    'user-agent) to measure aggregate engagement. We do not build advertising profiles or sell data.</p>'
    '<h2 style="font-size:22px;font-weight:600">Affiliate disclosure</h2>'
    '<p>Some outbound links are affiliate links: if you purchase through them, we may earn a '
    'commission at no additional cost to you. Affiliate destinations are shown transparently and '
    'are never hidden or cloaked.</p>'
    '<h2 style="font-size:22px;font-weight:600">Platform API integration</h2>'
    '<p>Our management software interacts with social platform APIs (e.g. Pinterest API v5) to '
    'publish our own content and monitor our own organic engagement metrics, in accordance with '
    'each platform\'s developer guidelines. We do not store, share, or sell other users\' account '
    'details, credentials, or access tokens.</p>'
    '<h2 style="font-size:22px;font-weight:600">Contact</h2>'
    '<p>For questions about this policy, contact us via our registered domain administrative channels.</p>'
    '</div></section>')


# ---------------------------------------------------------------------------
# Router (single catch-all, per vercel.json)
# ---------------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    if path == "":
        return _home()
    if path == "about":
        return _about()
    if path == "privacy":
        return _page("Privacy & Disclosure — Ambient Living Lab", _PRIVACY_BODY)
    if path.startswith("p/"):
        p = _BY_SLUG.get(path[2:])
        return _review(p) if p else (_home(), 404)
    if path.startswith("go/"):
        slug = path[len("go/"):]
        try:
            raw = _kv("get", f"redirect:{slug}")
            if raw:
                data = json.loads(raw)
                dest = data.get("url") if isinstance(data, dict) else None
                if dest:
                    if data.get("sub_id"):
                        dest = _append_query(dest, "subid", data["sub_id"])
                    _kv("incr", f"clicks:{slug}")
                    _kv("lpush", "clicks:log", body=json.dumps({
                        "slug": slug,
                        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "ref": request.referrer,
                        "ua": request.headers.get("User-Agent"),
                    }))
                    return redirect(dest, code=302)
        except Exception:
            pass
        # Slug not in KV yet — send them to the on-site review if we have one.
        if slug in _BY_SLUG:
            return _review(_BY_SLUG[slug])
        return redirect("/", code=302)
    # Unknown path -> soft 404 to the landing page.
    return (_home(), 404)


# CRUCIAL FOR VERCEL NATIVE ROUTING:
handler = app
