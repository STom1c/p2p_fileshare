from flask import Flask, request, jsonify, render_template, abort
from flask_sock import Sock
import sqlite3
import string
import random
import os
import json
import threading

app = Flask(__name__)
sock = Sock(app)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'urls.db')

# ── In-memory WebTorrent tracker state ───────────────────────────────────────
# Structure: { info_hash_str: { peer_id_str: { 'ws': ws, 'complete': bool } } }
_swarms: dict = {}
_swarm_lock = threading.Lock()
# ─────────────────────────────────────────────────────────────────────────────


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS short_urls (
            code TEXT PRIMARY KEY,
            magnet TEXT DEFAULT '',
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

    magnet     = data.get('magnet', '')
    filename   = data.get('filename', 'Unknown')
    filesize   = data.get('filesize', 0)
    file_count = data.get('file_count', 1)

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

    base_url  = request.host_url.rstrip('/')
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


# ── WebTorrent Tracker (WebSocket) ────────────────────────────────────────────
@sock.route('/tracker')
def ws_tracker(ws):
    """
    Lightweight WebTorrent tracker implementing the bittorrent-tracker
    WebSocket signaling protocol.  Relays WebRTC SDP offers/answers so
    browser peers can establish direct P2P connections.

    info_hash / peer_id arrive as 20-char Latin-1 encoded binary strings
    inside JSON.  Python decodes the UTF-8 WebSocket frame into str, so
    ord(c) recovers the original byte value for each character.
    """
    my_ih: str | None = None
    my_pid: str | None = None

    try:
        while True:
            data = ws.receive(timeout=300)   # 5-min idle timeout
            if data is None:
                break

            try:
                msg = json.loads(data)
            except Exception:
                continue

            if msg.get('action') != 'announce':
                continue

            ih  = msg.get('info_hash', '')
            pid = msg.get('peer_id',   '')

            # WebTorrent sends exactly 20-char binary strings for these fields.
            if len(ih) != 20 or len(pid) != 20:
                continue

            my_ih  = ih
            my_pid = pid

            # ── Answer: relay back to the peer that sent the original offer ──
            if msg.get('answer'):
                to_pid = msg.get('to_peer_id', '')
                if len(to_pid) == 20:
                    with _swarm_lock:
                        target = _swarms.get(ih, {}).get(to_pid)
                    if target:
                        try:
                            target['ws'].send(json.dumps({
                                'action':   'announce',
                                'answer':   msg['answer'],
                                'offer_id': msg.get('offer_id'),
                                'peer_id':  pid,
                                'info_hash': ih,
                            }))
                        except Exception:
                            pass

            # ── Announce: register peer, relay offers to existing peers ──────
            else:
                offers   = msg.get('offers', [])
                left     = msg.get('left')
                complete = (left == 0) if left is not None else False

                with _swarm_lock:
                    swarm  = _swarms.setdefault(ih, {})
                    others = [(p, d) for p, d in swarm.items() if p != pid]
                    swarm[pid] = {'ws': ws, 'complete': complete}
                    n_complete   = sum(1 for d in swarm.values() if d['complete'])
                    n_incomplete = len(swarm) - n_complete

                # Forward each offer to one other peer (outside lock)
                for i, offer in enumerate(offers[: len(others)]):
                    other_pid, other = others[i]
                    try:
                        other['ws'].send(json.dumps({
                            'action':   'announce',
                            'offer':    offer.get('offer'),
                            'offer_id': offer.get('offer_id'),
                            'peer_id':  pid,
                            'info_hash': ih,
                        }))
                    except Exception:
                        pass

                # Send announce response to this peer
                try:
                    ws.send(json.dumps({
                        'action':    'announce',
                        'info_hash': ih,
                        'complete':   n_complete,
                        'incomplete': n_incomplete,
                        'interval':   120,
                    }))
                except Exception:
                    pass

    finally:
        # Clean up on disconnect
        if my_ih and my_pid:
            with _swarm_lock:
                swarm = _swarms.get(my_ih, {})
                swarm.pop(my_pid, None)
                if not swarm:
                    _swarms.pop(my_ih, None)
# ─────────────────────────────────────────────────────────────────────────────


if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5050)
