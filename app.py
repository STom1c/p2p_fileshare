from flask import Flask, request, jsonify, render_template, abort
import sqlite3
import string
import random
import os
import threading

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'urls.db')

# In-memory signaling store: { code: { 'offer': dict|None, 'answer': dict|None } }
_signals: dict = {}
_signals_lock = threading.Lock()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS short_urls (
            code       TEXT PRIMARY KEY,
            filename   TEXT DEFAULT '',
            filesize   INTEGER DEFAULT 0,
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

    filename   = data.get('filename', 'Unknown')
    filesize   = data.get('filesize', 0)
    file_count = data.get('file_count', 1)

    conn = get_db()
    try:
        code = generate_code()
        while conn.execute('SELECT 1 FROM short_urls WHERE code = ?', (code,)).fetchone():
            code = generate_code()
        conn.execute(
            'INSERT INTO short_urls (code, filename, filesize, file_count) VALUES (?, ?, ?, ?)',
            (code, filename, filesize, file_count)
        )
        conn.commit()
    finally:
        conn.close()

    with _signals_lock:
        _signals[code] = {'offer': None, 'answer': None}

    base_url  = request.host_url.rstrip('/')
    short_url = f"{base_url}/s/{code}"
    return jsonify({'short_url': short_url, 'code': code})


@app.route('/s/<code>')
def receive_page(code):
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT filename, filesize, file_count FROM short_urls WHERE code = ?',
            (code,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        abort(404)

    return render_template(
        'receive.html',
        filename=row['filename'],
        filesize=row['filesize'],
        file_count=row['file_count'],
        code=code
    )


@app.route('/api/signal/<code>/offer', methods=['GET', 'POST'])
def signal_offer(code):
    if request.method == 'POST':
        data = request.get_json()
        with _signals_lock:
            if code not in _signals:
                _signals[code] = {'offer': None, 'answer': None}
            _signals[code]['offer'] = data.get('sdp')
        return jsonify({'ok': True})
    # GET
    with _signals_lock:
        sig = _signals.get(code)
    return jsonify({'sdp': sig['offer'] if sig else None})


@app.route('/api/signal/<code>/answer', methods=['GET', 'POST'])
def signal_answer(code):
    if request.method == 'POST':
        data = request.get_json()
        with _signals_lock:
            if code not in _signals:
                _signals[code] = {'offer': None, 'answer': None}
            _signals[code]['answer'] = data.get('sdp')
        return jsonify({'ok': True})
    # GET
    with _signals_lock:
        sig = _signals.get(code)
    return jsonify({'sdp': sig['answer'] if sig else None})


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5050)
