// Liquidity backup address on Azure App Service (*.azurewebsites.net).
// Forwards every request and WebSocket to the real site on Appliku. Stores nothing.
// Settings (App Service "Environment variables"):
//   TARGET        your Appliku host, e.g. liquidity.applikuapp.com
//   PROXY_SECRET  same value as LIQ_PROXY_SECRET in Appliku
'use strict';
const http = require('http');
const https = require('https');
const tls = require('tls');
const net = require('net');

const TARGET = (process.env.TARGET || '').replace(/^https?:\/\//, '').replace(/\/.*$/, '');
const SECRET = process.env.PROXY_SECRET || '';
const SECURE = (process.env.TARGET_PROTOCOL || 'https') === 'https';
const PORT = process.env.PORT || 8080;
if (!TARGET || !SECRET) {
  console.error('Set TARGET and PROXY_SECRET environment variables.');
}
const [THOST, TPORT_RAW] = TARGET.split(':');
const TPORT = Number(TPORT_RAW) || (SECURE ? 443 : 80);
const HOP = ['connection', 'keep-alive', 'proxy-connection', 'transfer-encoding', 'upgrade', 'te', 'trailer'];

function upstreamHeaders(req, keepUpgrade) {
  const h = { ...req.headers };
  if (!keepUpgrade) for (const k of HOP) delete h[k];
  delete h['x-liquidity-host'];
  delete h['x-liquidity-proxy'];
  h['x-liquidity-host'] = req.headers.host || '';
  h['x-liquidity-proxy'] = SECRET;
  h['x-forwarded-proto'] = 'https';
  h.host = TARGET;
  return h;
}

const server = http.createServer((req, res) => {
  const lib = SECURE ? https : http;
  const up = lib.request({
    host: THOST, port: TPORT, servername: THOST, method: req.method, path: req.url,
    headers: upstreamHeaders(req, false),
  }, (ur) => {
    const h = { ...ur.headers };
    for (const k of ['connection', 'keep-alive', 'transfer-encoding']) delete h[k];
    res.writeHead(ur.statusCode, ur.statusMessage, h);
    ur.pipe(res);
  });
  up.setTimeout(120000, () => up.destroy(new Error('upstream timeout')));
  up.on('error', (e) => {
    if (!res.headersSent) res.writeHead(502, { 'content-type': 'text/plain' });
    res.end('Liquidity mirror could not reach the main site: ' + e.message);
  });
  req.pipe(up);
});

server.on('upgrade', (req, sock, head) => {
  const up = SECURE
    ? tls.connect({ host: THOST, port: TPORT, servername: THOST })
    : net.connect({ host: THOST, port: TPORT });
  up.once(SECURE ? 'secureConnect' : 'connect', () => {
    let s = `${req.method} ${req.url} HTTP/1.1\r\n`;
    for (const [k, v] of Object.entries(upstreamHeaders(req, true))) {
      for (const one of [].concat(v)) s += `${k}: ${one}\r\n`;
    }
    up.write(s + '\r\n');
    if (head && head.length) up.write(head);
    up.pipe(sock);
    sock.pipe(up);
  });
  up.on('error', () => sock.destroy());
  sock.on('error', () => up.destroy());
  up.on('close', () => sock.destroy());
  sock.on('close', () => up.destroy());
});

server.keepAliveTimeout = 65000;
server.listen(PORT, () => console.log(`Liquidity mirror on :${PORT} -> ${TARGET}`));
