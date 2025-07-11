from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
import re
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'super-strong-random-secret-key'

UPLOAD_FOLDER = 'uploads'
DATA_FILE = 'data/posts.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# Admin credentials
ADMIN_USERNAME = 'rootadmin'
ADMIN_PASSWORD_HASH = generate_password_hash('neverguess123!')

# Load posts from file or empty
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'r') as f:
        posts = json.load(f)
else:
    posts = {}

# Save posts to file
def save_posts():
    with open(DATA_FILE, 'w') as f:
        json.dump(posts, f, indent=2)

# Slugify title
def slugify(title):
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title).lower()
    slug = re.sub(r'\s+', '-', slug).strip('-')
    original_slug = slug
    count = 1
    while slug in posts:
        slug = f"{original_slug}-{count}"
        count += 1
    return slug

@app.route('/')
def home():
    return redirect('/admin')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            error = "Invalid credentials."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect('/login')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged_in'):
        return redirect('/login')

    error = None
    if request.method == 'POST':
        title = request.form.get('title')
        body = request.form.get('body', '')
        file = request.files.get('doc')

        if not title or not file:
            error = "Title and document are required."
            return render_template('admin.html', error=error, posts=posts)

        slug = slugify(title)
        filename = secure_filename(file.filename)
        saved_path = os.path.join(UPLOAD_FOLDER, slug + "_" + filename)
        file.save(saved_path)

        posts[slug] = {
            'title': title,
            'body': body,
            'filename': filename,
            'filepath': saved_path,
            'created_at': datetime.now().strftime('%d %b %Y, %I:%M %p')
        }

        save_posts()
        return redirect(url_for('view_consumer', slug=slug))

    return render_template('admin.html', error=error, posts=posts)

@app.route('/doc/<slug>')
def view_consumer(slug):
    post = posts.get(slug)
    if not post:
        return "Document not found", 404
    return render_template('consumer.html', post=post, slug=slug)

@app.route('/download/<slug>')
def download_file(slug):
    post = posts.get(slug)
    if not post:
        return "File not found", 404
    directory = os.path.dirname(post['filepath'])
    filename = os.path.basename(post['filepath'])
    return send_from_directory(directory, filename, as_attachment=True)

@app.route('/delete/<slug>', methods=['POST'])
def delete_slug(slug):
    if not session.get('admin_logged_in'):
        return redirect('/login')

    post = posts.get(slug)
    if post:
        try:
            os.remove(post['filepath'])
        except:
            pass
        posts.pop(slug)
        save_posts()
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)
