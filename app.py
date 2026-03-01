from flask import Flask, request, jsonify, render_template, abort
from flask_sock import Sock
import sqlite3, string, random, os, threading, json

app  = Flask(__name__)
sock = Sock(app)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'urls.db')

# Relay sessions: { code: { sender_ws, receiver_ws, receiver_ready, done } }
_relay: dict = {}
_relay_lock  = threading.Lock()


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
        while conn.execute('SELECT 1 FROM short_urls WHERE code=?', (code,)).fetchone():
            code = generate_code()
        conn.execute(
            'INSERT INTO short_urls (code,filename,filesize,file_count) VALUES (?,?,?,?)',
            (code, filename, filesize, file_count)
        )
        conn.commit()
    finally:
        conn.close()

    with _relay_lock:
        _relay[code] = {
            'sender_ws':      None,
            'receiver_ws':    None,
            'receiver_ready': threading.Event(),
            'done':           threading.Event(),
        }

    short_url = request.host_url.rstrip('/') + f'/s/{code}'
    return jsonify({'short_url': short_url, 'code': code})


@app.route('/s/<code>')
def receive_page(code):
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT filename,filesize,file_count FROM short_urls WHERE code=?', (code,)
        ).fetchone()
    finally:
        conn.close()

    if not row:
        abort(404)

    return render_template('receive.html',
        filename=row['filename'], filesize=row['filesize'],
        file_count=row['file_count'], code=code)


# ── WebSocket relay ───────────────────────────────────────
@sock.route('/ws/<code>')
def ws_relay(ws, code):
    """
    Both sender and receiver connect here.
    First message must be JSON: {"role": "sender"} or {"role": "receiver"}.

    Sender thread:  waits for receiver, then relays all messages to receiver_ws.
    Receiver thread: registers itself, then holds the socket open while the
                     sender thread writes into it from the other thread.
    """
    try:
        raw = ws.receive(timeout=60)
    except Exception:
        return
    if not raw:
        return

    try:
        role = json.loads(raw).get('role')
    except Exception:
        return

    if role not in ('sender', 'receiver'):
        return

    # Lazily create relay entry (receiver may arrive before sender)
    with _relay_lock:
        if code not in _relay:
            _relay[code] = {
                'sender_ws':      None,
                'receiver_ws':    None,
                'receiver_ready': threading.Event(),
                'done':           threading.Event(),
            }
        entry = _relay[code]

    try:
        if role == 'sender':
            entry['sender_ws'] = ws

            # Wait up to 10 min for receiver to open the link
            if not entry['receiver_ready'].wait(timeout=600):
                ws.send(json.dumps({'type': 'error', 'msg': '等待接收方逾時，請重新整理頁面重試。'}))
                return

            # Tell sender to start streaming
            ws.send(json.dumps({'type': 'go'}))

            # Relay every frame (text or binary) to the receiver
            while True:
                try:
                    frame = ws.receive(timeout=600)
                except Exception:
                    break
                if frame is None:
                    break
                try:
                    entry['receiver_ws'].send(frame)
                except Exception:
                    break

            entry['done'].set()  # unblock receiver thread so it can exit cleanly

        elif role == 'receiver':
            entry['receiver_ws'] = ws
            entry['receiver_ready'].set()   # unblock sender thread

            # Hold the WebSocket open; the sender thread writes into it directly.
            # We just wait until the transfer is done (or times out / errors).
            entry['done'].wait(timeout=3600)

    finally:
        with _relay_lock:
            _relay.pop(code, None)


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5050)
