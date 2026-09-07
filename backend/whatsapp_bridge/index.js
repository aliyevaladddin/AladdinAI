/**
 * WhatsApp bridge daemon (Baileys) — one process per messaging channel.
 *
 *   node index.js <channel_id>
 *
 * Speaks newline-delimited JSON over a per-channel unix socket:
 *   us -> daemon : {"type":"ping"} | {"type":"get-qr"}
 *                | {"type":"send-message","to":"...","text":"..."}
 *   daemon -> us : {"type":"pong"} | {"type":"qr","data":"<dataURL>"}
 *                | {"type":"status","status":"sent"} | {"type":"error","error":"..."}
 *
 * Incoming WhatsApp messages are forwarded to the backend webhook
 * (POST /api/webhooks/whatsapp_baileys/<channel_id>) with the channel's
 * webhook_secret in the X-Bridge-Secret header.
 *
 * Env:
 *   ALADDIN_BACKEND_URL   backend base URL (default http://localhost:8000)
 *   BRIDGE_WEBHOOK_SECRET channel webhook_secret sent as X-Bridge-Secret
 */
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('baileys');
const net = require('net');
const fs = require('fs');
const path = require('path');
const pino = require('pino');
const QRCode = require('qrcode');

process.on('uncaughtException', (err) => console.error('[Bridge Uncaught Exception]', err));
process.on('unhandledRejection', (reason) => console.error('[Bridge Unhandled Rejection]', reason));

const CHANNEL_ID = process.argv[2] || 'default';
const SOCKET_PATH = `/tmp/aladdin_whatsapp_${CHANNEL_ID}.sock`;
const BACKEND_URL = process.env.ALADDIN_BACKEND_URL || 'http://localhost:8000';
const WEBHOOK_SECRET = process.env.BRIDGE_WEBHOOK_SECRET || '';
const AUTH_DIR = path.join(__dirname, `whatsapp_auth_${CHANNEL_ID}`);
const RECONNECT_DELAY_MS = 3000;

let waSock = null;
let latestQr = null;
let reconnectTimer = null;

function safeWrite(socket, obj) {
    if (!socket.destroyed) socket.write(JSON.stringify(obj));
}

/** Forward one incoming WhatsApp message to the backend webhook. */
async function forwardToBackend(senderId, senderName, text) {
    try {
        const headers = { 'Content-Type': 'application/json' };
        if (WEBHOOK_SECRET) headers['X-Bridge-Secret'] = WEBHOOK_SECRET;
        const res = await fetch(`${BACKEND_URL}/api/webhooks/whatsapp_baileys/${CHANNEL_ID}`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ sender_id: senderId, sender_name: senderName, text: text ?? '' }),
        });
        if (!res.ok) console.error(`[Bridge] webhook responded ${res.status}`);
    } catch (e) {
        console.error('[Bridge] webhook error', e.message);
    }
}

/** (Re)connect to WhatsApp. Safe to call again after disconnects — the unix
 *  socket server is created only once at startup, so reconnects never touch
 *  it (this was the EADDRINUSE / ENOENT-unlink crash loop before). */
async function startWA() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    waSock = makeWASocket({
        auth: state,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
    });

    waSock.ev.on('creds.update', saveCreds);

    waSock.ev.on('messages.upsert', async (m) => {
        if (m.type !== 'notify') return;
        for (const msg of m.messages) {
            if (msg.key.fromMe) continue;
            const senderId = msg.key.remoteJid;
            // Groups are not handled yet — never auto-reply into them.
            if (senderId.endsWith('@g.us')) continue;
            const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text;
            if (!text) continue; // media/sticker messages are skipped for now
            await forwardToBackend(senderId, msg.pushName || 'WhatsApp User', text);
        }
    });

    waSock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;
        console.log(`[Bridge] Connection update: ${connection}, QR present: ${!!qr}`);
        if (qr) {
            QRCode.toDataURL(qr)
                .then((d) => { latestQr = d; })
                .catch((e) => console.error('[Bridge] QR encode failed', e.message));
        }
        if (connection === 'open') {
            latestQr = null;
        } else if (connection === 'close') {
            const code = lastDisconnect?.error?.output?.statusCode;
            if (code === DisconnectReason.loggedOut) {
                console.log('[Bridge] Logged out — not reconnecting. Remove', AUTH_DIR, 'to re-pair.');
                return;
            }
            if (!reconnectTimer) {
                reconnectTimer = setTimeout(() => {
                    reconnectTimer = null;
                    startWA().catch((e) => console.error('[Bridge] reconnect failed', e.message));
                }, RECONNECT_DELAY_MS);
            }
        }
    });
}

async function handleLine(socket, line) {
    let command;
    try {
        command = JSON.parse(line);
    } catch {
        return safeWrite(socket, { type: 'error', error: 'invalid json' });
    }

    switch (command.type) {
        case 'ping':
            return safeWrite(socket, { type: 'pong' });
        case 'get-qr':
            return safeWrite(socket, { type: 'qr', data: latestQr });
        case 'send-message': {
            if (typeof command.to !== 'string' || typeof command.text !== 'string' || !command.text) {
                return safeWrite(socket, { type: 'error', error: 'send-message requires string "to" and non-empty "text"' });
            }
            if (!waSock) return safeWrite(socket, { type: 'error', error: 'not connected to WhatsApp' });
            await waSock.sendMessage(command.to, { text: command.text });
            return safeWrite(socket, { type: 'status', status: 'sent' });
        }
        default:
            return safeWrite(socket, { type: 'error', error: `unknown command: ${command.type}` });
    }
}

function handleConnection(socket) {
    socket.on('error', (err) => console.error(`[Bridge] Socket error: ${err.message}`));

    let buffer = '';
    socket.on('data', (chunk) => {
        buffer += chunk.toString();
        let idx;
        while ((idx = buffer.indexOf('\n')) !== -1) {
            const line = buffer.slice(0, idx).trim();
            buffer = buffer.slice(idx + 1);
            if (line) {
                handleLine(socket, line).catch((e) =>
                    safeWrite(socket, { type: 'error', error: e.message })
                );
            }
        }
        if (buffer.length > 1_000_000) {
            buffer = '';
            safeWrite(socket, { type: 'error', error: 'command too long' });
        }
    });
}

// ── Startup: unix socket server once, then WhatsApp. ────────────────────────
try {
    if (fs.existsSync(SOCKET_PATH)) fs.unlinkSync(SOCKET_PATH);
} catch {
    /* another daemon may have cleaned it first — fine */
}

const server = net.createServer(handleConnection);
server.on('error', (err) => {
    console.error(`[Bridge] Server error: ${err.message}`);
    if (err.code === 'EADDRINUSE') process.exit(1); // let the manager respawn us cleanly
});
server.listen(SOCKET_PATH, () => {
    console.log(`[WhatsApp Bridge ${CHANNEL_ID}] Listening on ${SOCKET_PATH}`);
});

startWA().catch((e) => console.error('[Bridge] initial connect failed', e.message));
