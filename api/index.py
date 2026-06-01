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
    # 1. Clear tracking/routing logic
    if path in REDIRECTS:
        # In the future, your script will log 'path' and request.remote_addr to SQLite here
        return redirect(REDIRECTS[path], code=302)
    
    # 2. Innocent, clean homepage for Pinterest to verify and "Claim"
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Curated Lifestyle & Living</title>
        <style>
            body { font-family: 'Georgia', serif; padding: 80px; max-width: 600px; margin: 0 auto; color: #222; background: #fff; line-height: 1.6; }
            h1 { font-size: 36px; font-weight: normal; margin-bottom: 20px; }
            p { font-size: 18px; color: #555; }
        </style>
    </head>
    <body>
        <h1>Curated Lifestyle & Living</h1>
        <p>Welcome to our design gallery. We curate the finest high-ticket home decor, luxury travel guides, and premium lifestyle assets from around the web.</p>
    </body>
    </html>
    """)
