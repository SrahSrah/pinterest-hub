"""Ambient Living Lab — landing + transparent tracked-redirect bridge (Vercel).

Deploy target: the `pinterest-hub` Vercel project. Copy this file over
`pinterest-hub/api/index.py`, keep the existing requirements.txt and
vercel.json, set the KV env vars in Vercel, and push.

Routes:
  GET /                -> landing page (used for Pinterest domain verification)
  GET /privacy         -> privacy policy (required for API approval)
  GET /go/<slug>       -> look up slug in Vercel KV, log the click, 302 to the
                          real affiliate destination (transparent, not cloaked)

The redirect table lives in Vercel KV (Upstash Redis). The local automation
writes `redirect:<slug>` -> {"url": ..., "sub_id": ...}; this function reads it.
Clicks are counted (`clicks:<slug>`) and pushed to a `clicks:log` list that the
local `sync-clicks` command drains into SQLite for analytics. KV access is
best-effort: a KV hiccup never blocks the redirect.
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from flask import Flask, redirect, render_template_string, request

app = Flask(__name__)

# Vercel KV sets KV_REST_API_*; the Upstash marketplace integration sets
# UPSTASH_REDIS_REST_*. Accept either so it works however you provisioned it.
KV_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")


def _kv(*segments, body=None):
    """Call the Upstash REST API. POST for everything (Upstash accepts it);
    pass ``body`` for the value of set/lpush. Returns the ``result`` or None."""
    if not (KV_URL and KV_TOKEN):
        return None
    path = "/".join(urllib.parse.quote(s, safe="") for s in segments)
    data = body.encode("utf-8") if body is not None else b""
    req = urllib.request.Request(
        f"{KV_URL.rstrip('/')}/{path}",
        data=data, method="POST",
        headers={"Authorization": f"Bearer {KV_TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8")).get("result")
    except Exception:
        return None  # best-effort: never break the redirect on a KV error


def _append_query(url, key, value):
    parts = urllib.parse.urlsplit(url)
    q = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    q[key] = value
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    if path == "privacy":
        return render_template_string(_PRIVACY_HTML)

    # Transparent tracked redirect: /go/<slug>
    # Fully guarded: a missing key, malformed value, or KV outage must never
    # 500 — it falls through to the landing page instead.
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
                    # Log the click (best-effort).
                    _kv("incr", f"clicks:{slug}")
                    _kv("lpush", "clicks:log", body=json.dumps({
                        "slug": slug,
                        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "ref": request.referrer,
                        "ua": request.headers.get("User-Agent"),
                    }))
                    return redirect(dest, code=302)
        except Exception:
            pass  # malformed data / KV error -> fall through to landing
        # Unknown/expired/unresolvable slug — fall through to the landing page.

    return render_template_string(_HOME_HTML)


# CRUCIAL FOR VERCEL NATIVE ROUTING:
handler = app


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
_PRIVACY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - Ambient Living Lab</title>
    <style>
        body { font-family: 'Georgia', serif; padding: 60px 20px; max-width: 700px; margin: 0 auto; color: #222; background: #fff; line-height: 1.6; }
        h1 { font-size: 28px; margin-bottom: 20px; color: #111; font-weight: normal; }
        h2 { font-size: 20px; margin-top: 30px; color: #333; font-weight: normal; }
        p { font-size: 16px; color: #444; }
    </style>
</head>
<body>
    <h1>Privacy Policy</h1>
    <p>Last Updated: June 2026</p>
    <p>Welcome to Ambient Living Lab ("we", "our", "us"). We respect your privacy and are committed to protecting any data we process.</p>

    <h2>1. Information We Collect</h2>
    <p>This website functions as a curation and content directory. We do not require user account registration. When you click an outbound link, we log non-identifying request metadata (timestamp, referring page, and user-agent string) to measure aggregate engagement. We do not build advertising profiles or sell data.</p>

    <h2>2. Affiliate Disclosure</h2>
    <p>Some outbound links are affiliate links: if you purchase through them, we may earn a commission at no additional cost to you. Affiliate destinations are shown transparently and are never hidden or cloaked.</p>

    <h2>3. Platform API Integration</h2>
    <p>Our management software interacts with social platform APIs (e.g. Pinterest API v5) to publish our own content and monitor our own organic engagement metrics, in accordance with each platform's developer guidelines. We do not store, share, or sell other users' account details, credentials, or access tokens.</p>

    <h2>4. Contact Us</h2>
    <p>For questions regarding this policy, contact us via our registered domain administrative channels.</p>
</body>
</html>
"""

_HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ambient Living Lab | The Luxury Living Experiment</title>
    <style>
        body { font-family: 'Georgia', serif; padding: 80px 20px; max-width: 600px; margin: 0 auto; color: #222; background: #fff; line-height: 1.6; }
        h1 { font-size: 36px; font-weight: normal; margin-bottom: 20px; color: #111; }
        p { font-size: 18px; color: #555; margin-bottom: 20px; }
        footer { margin-top: 60px; border-top: 1px solid #eee; padding-top: 20px; font-size: 14px; }
        footer a { color: #888; text-decoration: none; }
        footer a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Ambient Living Lab</h1>
    <p>Welcome to our design gallery. We curate the finest high-ticket home decor, luxury travel guides, and premium lifestyle assets from around the web.</p>
    <p><em>The Luxury Living Experiment is currently launching. Lookbooks coming soon.</em></p>
    <footer>
        <a href="/privacy">Privacy Policy</a>
    </footer>
</body>
</html>
"""
