/**
 * Self-hosted WebTorrent Tracker (bittorrent-tracker)
 *
 * Operates as a WebSocket signaling server so that browser-based
 * WebTorrent peers can discover each other via WebRTC offer/answer
 * relay.  Deployed as a separate Render web service.
 */

import { Server } from 'bittorrent-tracker'

const PORT = parseInt(process.env.PORT, 10) || 8000

const server = new Server({
    http: true,      // HTTP tracker (also serves health-check)
    udp: false,      // not needed for browser peers
    ws: true,        // ← WebSocket tracker (WebTorrent signaling)
    stats: true,     // expose /stats endpoint
    trustProxy: true // behind Render's reverse-proxy
})

server.on('error', err => {
    console.error('[tracker] fatal error:', err.message)
    process.exit(1)
})

server.on('warning', err => {
    console.warn('[tracker] warning:', err.message)
})

server.on('listening', () => {
    console.log(`[tracker] WebTorrent tracker listening`)
    console.log(`[tracker]   HTTP : http://0.0.0.0:${PORT}`)
    console.log(`[tracker]   WS   : ws://0.0.0.0:${PORT}`)
    console.log(`[tracker] Use wss://<your-domain> in the browser`)
})

server.listen(PORT, '0.0.0.0')
