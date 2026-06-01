from flask import Flask, redirect, render_template_string, request

app = Flask(__name__)

# This dictionary acts as your transparent router. 
# Your automated script will update this dynamically later.
REDIRECTS = {
    "luxury-decor-01": "https://ambientlivinglab.com",
}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # 1. Privacy Policy Router (Required for Pinterest Developer Approval)
    if path == "privacy":
        return render_template_string("""
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
            <p>Welcome to Ambient Living Lab ("we", "our", "us"). We respect your privacy and are committed to protecting any data we process through our workflows.</p>
            
            <h2>1. Information We Collect</h2>
            <p>This website functions strictly as a curation and content directory. We do not require user account registrations, nor do we intentionally collect, track, or harvest personally identifiable information (PII) from casual visitors browsing this domain.</p>
            
            <h2>2. Pinterest API Integration</h2>
            <p>Our internal management software interacts with the Pinterest API v5 to curate public digital design inspiration and monitor organic engagement metrics. We access and process data strictly in accordance with Pinterest Developer Guidelines. We do not store, share, process, or sell user account details, credentials, or access tokens to any third-party marketing entities.</p>
            
            <h2>3. Contact Us</h2>
            <p>For questions regarding this operational compliance policy, you may contact our engineering and operations team directly via our registered domain administrative channels.</p>
        </body>
        </html>
        """)

    # 2. Clear tracking/routing logic for active campaign pins
    if path in REDIRECTS:
        # In the future, your automated script can log 'path' and request.remote_addr to SQLite/Postgres here
        return redirect(REDIRECTS[path], code=302)
    
    # 3. Innocent, clean homepage for Pinterest to verify and "Claim"
    return render_template_string("""
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
    """)

# CRUCIAL FOR VERCEL NATIVE ROUTING:
handler = app
