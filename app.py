from flask import Flask, request, jsonify, render_template, abort
import sqlite3
import string
import random
import os

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'urls.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS short_urls (
            code TEXT PRIMARY KEY,
            magnet TEXT NOT NULL,
            filename TEXT DEFAULT '',
            filesize INTEGER DEFAULT 0,
            file_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def generate_code(length=7):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choices(chars, k=length))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request'}), 400

    magnet = data.get('magnet', '').strip()
    filename = data.get('filename', 'Unknown')
    filesize = data.get('filesize', 0)
    file_count = data.get('file_count', 1)

    if not magnet:
        return jsonify({'error': 'No magnet link provided'}), 400

    conn = get_db()
    try:
        code = generate_code()
        while conn.execute('SELECT 1 FROM short_urls WHERE code = ?', (code,)).fetchone():
            code = generate_code()

        conn.execute(
            'INSERT INTO short_urls (code, magnet, filename, filesize, file_count) VALUES (?, ?, ?, ?, ?)',
            (code, magnet, filename, filesize, file_count)
        )
        conn.commit()
    finally:
        conn.close()

    base_url = request.host_url.rstrip('/')
    short_url = f"{base_url}/s/{code}"
    return jsonify({'short_url': short_url, 'code': code})


@app.route('/s/<code>')
def receive_page(code):
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT magnet, filename, filesize, file_count FROM short_urls WHERE code = ?',
            (code,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        abort(404)

    return render_template(
        'receive.html',
        magnet=row['magnet'],
        filename=row['filename'],
        filesize=row['filesize'],
        file_count=row['file_count'],
        code=code
    )


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5050)
