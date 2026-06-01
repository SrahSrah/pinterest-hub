from flask import Flask, redirect, render_template_string, request

app = Flask(__name__)

REDIRECTS = {
    "luxury-decor-01": "https://ambientlivinglab.com",
}

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    if path in REDIRECTS:
        return redirect(REDIRECTS[path], code=302)
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Ambient Living Lab | The Luxury Living Experiment</title>
        <style>
            body { font-family: 'Georgia', serif; padding: 80px; max-width: 600px; margin: 0 auto; color: #222; background: #fff; line-height: 1.6; }
            h1 { font-size: 36px; font-weight: normal; margin-bottom: 20px; }
            p { font-size: 18px; color: #555; }
        </style>
    </head>
    <body>
        <h1>Ambient Living Lab</h1>
        <p>Welcome to our design gallery. We curate the finest high-ticket home decor, luxury travel guides, and premium lifestyle assets from around the web.</p>
        <p><em>The Luxury Living Experiment is currently launching. Lookbooks coming soon.</em></p>
    </body>
    </html>
    """)

# Ensure this handler is explicitly exposed for the vercel.json builder
handler = app
