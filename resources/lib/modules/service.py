# -*- coding: utf-8 -*-

# AliveGR Addon
# Author Twilight0
# SPDX-License-Identifier: GPL-3.0-only

import base64
import collections
import http.server
import json
import queue
import re
import socketserver
import threading
import sys
import urllib.parse
import time
import xbmc
import xbmcaddon
import xbmcvfs

sys.path.append(xbmcvfs.translatePath('special://home/addons/script.module.websocket/lib'))
sys.path.append(xbmcvfs.translatePath('special://home/addons/script.module.netclient/resources/lib'))

try:
    import websocket
    from useragents import get_ua
    import netclient
except ImportError:
    websocket = None
    get_ua = None
    netclient = None


__addon_id__ = 'plugin.video.alivegr'

PROXY_PORT = int(xbmcaddon.Addon('plugin.video.alivegr').getSetting('proxy_port')) or 50199
g_proxy_server = None
g_stream_manager = None


class StreamManager:

    def __init__(self, ws_url, origin=None):

        self.ws_url = ws_url
        self.origin = origin
        self.ws = None
        self.audio_ids = set()
        self.video_ids = set()

        self.video_init_tag = None
        self.audio_init_tag = None
        self.media_buffer = collections.deque(maxlen=150)
        self.clients = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.init_ready = threading.Event()
        self.first_ts = None

        self.last_active_time = time.time()

        self.thread = threading.Thread(target=self._ws_reader, daemon=True)
        self.ping_thread = None
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.ws:
            try:
                self.ws.close()
            except:
                pass

    def write_flv_tag(self, tag_type, timestamp_ms, payload):
        """Wraps raw payload into a standard FLV Tag."""
        tag = bytearray()
        tag.append(tag_type)
        tag.extend(len(payload).to_bytes(3, 'big'))
        tag.extend((timestamp_ms & 0xFFFFFF).to_bytes(3, 'big'))
        tag.append((timestamp_ms >> 24) & 0xFF)
        tag.extend(b'\x00\x00\x00')  # StreamID
        tag.extend(payload)
        tag.extend((11 + len(payload)).to_bytes(4, 'big'))  # PreviousTagSize
        return tag

    def _pinger(self):

        while not self.stop_event.wait(5.0):
            try:
                if self.ws and self.ws.connected:
                    self.ws.send(json.dumps({"type": "ping"}))
            except Exception:
                break

    def _ws_reader(self):
        xbmc.log(f'AliveGR Proxy: Connecting MoQ WSS... {self.ws_url}', xbmc.LOGDEBUG)
        headers = {
            'User-Agent': get_ua(),
            'Origin': self.origin
        }

        try:

            self.ws = websocket.create_connection(self.ws_url, header=headers, timeout=15)
            xbmc.log('AliveGR Proxy: MoQ connected. Awaiting handshakes...', xbmc.LOGDEBUG)

            self.ping_thread = threading.Thread(target=self._pinger, daemon=True)
            self.ping_thread.start()

            while not self.stop_event.is_set():

                if len(self.clients) > 0:
                    self.last_active_time = time.time()
                elif time.time() - self.last_active_time > 10.0:
                    xbmc.log('AliveGR Proxy: No Kodi clients active for 10s. Auto-closing stream.', xbmc.LOGDEBUG)
                    self.stop()
                    break
                # -----------------------

                msg = self.ws.recv()
                if not msg: continue

                # 1. Parse JSON Control Plane
                if isinstance(msg, str):
                    try:
                        data = json.loads(msg)
                        msg_type = data.get('type')

                        if msg_type in ('ping', 'pong'):
                            continue

                        if msg_type == 'renditions':
                            for r in data.get('renditions', []):
                                codec = r.get('codec', '')
                                if codec in ('aac', 'mp3', 'opus'):
                                    self.audio_ids.add(r['id'])
                                elif codec in ('h264', 'h265', 'av1'):
                                    self.video_ids.add(r['id'])
                            xbmc.log(
                                f'AliveGR Proxy: Mapped Video IDs {self.video_ids}, Audio IDs {self.audio_ids}',
                                xbmc.LOGDEBUG
                            )
                    except:
                        pass
                    continue

                # 2. Parse Binary Media Plane (MoQ)
                elif isinstance(msg, bytes):
                    if len(msg) < 17: continue

                    offset = int.from_bytes(msg[1:3], 'big')
                    flags = msg[3]
                    rend_id = msg[4]
                    timestamp = int.from_bytes(msg[5:13], 'big')
                    timescale = int.from_bytes(msg[13:17], 'big')
                    if timescale == 0: timescale = 1000

                    if self.first_ts is None:
                        self.first_ts = timestamp
                    ts_ms = max(0, int((timestamp - self.first_ts) * 1000 / timescale))

                    comp_time = 0
                    if flags & 16 and len(msg) >= 19:
                        comp_time = int.from_bytes(msg[17:19], 'big', signed=True)
                    comp_time_ms = int(comp_time * 1000 / timescale)

                    payload = msg[offset:]
                    is_init = bool(flags & 2)
                    is_sync = bool(flags & 1)

                    tag = None

                    # 3A. Trans-mux H.264 to FLV Video Tag
                    if rend_id in self.video_ids:
                        payload_wrap = bytearray()
                        if is_init:
                            payload_wrap.extend(b'\x17\x00\x00\x00\x00')
                        else:
                            payload_wrap.append(0x17 if is_sync else 0x27)
                            payload_wrap.append(0x01)
                            payload_wrap.extend((comp_time_ms & 0xFFFFFF).to_bytes(3, 'big'))

                        payload_wrap.extend(payload)
                        tag = self.write_flv_tag(9, ts_ms, payload_wrap)

                        if is_init:
                            if not self.video_init_tag:
                                xbmc.log('AliveGR Proxy: Captured H.264 INIT.', xbmc.LOGDEBUG)
                            self.video_init_tag = tag

                    # 3B. Trans-mux AAC to FLV Audio Tag
                    elif rend_id in self.audio_ids:
                        payload_wrap = bytearray()
                        payload_wrap.append(0xAF)
                        payload_wrap.append(0x00 if is_init else 0x01)
                        payload_wrap.extend(payload)
                        tag = self.write_flv_tag(8, ts_ms, payload_wrap)

                        if is_init:
                            if not self.audio_init_tag:
                                xbmc.log('AliveGR Proxy: Captured AAC INIT.', xbmc.LOGDEBUG)
                            self.audio_init_tag = tag

                    # 4. Broadcast Tag to Kodi
                    if tag:
                        if is_init:
                            if self.video_init_tag:
                                self.init_ready.set()
                        else:
                            with self.lock:
                                self.media_buffer.append(tag)
                                for client_q in list(self.clients):
                                    try:
                                        client_q.put_nowait(tag)
                                    except queue.Full:
                                        pass

        except Exception as e:
            if not self.stop_event.is_set():
                xbmc.log(f'AliveGR Proxy: WSS Loop Error: {e}', xbmc.LOGDEBUG)
        finally:
            self.init_ready.set()
            xbmc.log('AliveGR Proxy: WSS Background Thread Closed', xbmc.LOGDEBUG)


class ProxyRequestHandler(http.server.BaseHTTPRequestHandler):

    def do_HEAD(self):

        self.send_response(200)
        self.send_header('Content-Type', 'video/x-flv')
        self.end_headers()

    def do_GET(self):

        global g_stream_manager

        if '.m3u8' in self.path:
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                vid_b64 = query['stream'][0]
                vid_url_with_headers = base64.urlsafe_b64decode(vid_b64).decode('utf-8')

                # Parse URL and headers
                parts = vid_url_with_headers.split('|', 1)
                url = parts[0]
                headers = {}
                if len(parts) > 1 and parts[1]:
                    header_pairs = parts[1].split('&')
                    for pair in header_pairs:
                        if '=' in pair:
                            key, value = pair.split('=', 1)
                            headers[key] = urllib.parse.unquote(value)

                # Use netclient to fetch
                net = netclient.Net()
                response = net.http_GET(url, headers=headers)
                content = response.content
                if isinstance(content, str):
                    content = content.encode('utf-8')

                self.send_response(200)
                self.send_header('Content-Type', 'application/vnd.apple.mpegurl')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            except Exception as e:

                xbmc.log(f'AliveGR Proxy: M3U8 proxy error: {e}', xbmc.LOGDEBUG)
                self.send_error(500, f"M3U8 proxy error: {e}")

            return

        elif '?ws=' in self.path:
            try:
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                ws_url = base64.urlsafe_b64decode(query['ws'][0]).decode('utf-8')
                origin = query['origin'][0]

                if not g_stream_manager or g_stream_manager.ws_url != ws_url or g_stream_manager.stop_event.is_set():
                    if g_stream_manager:
                        g_stream_manager.stop()
                    xbmc.log('AliveGR Proxy: Booting Stream Manager...', xbmc.LOGDEBUG)
                    g_stream_manager = StreamManager(ws_url, origin)
            except Exception as e:
                self.send_error(400, f"Invalid WSS parameter: {e}")
                return

        if not g_stream_manager:
            self.send_error(404, "Stream not initialized")
            return

        # Use one captured manager for the rest of the request, so a concurrent
        # swap or None-out of the global cannot split lock, registration and
        # cleanup across different StreamManager instances.
        manager = g_stream_manager

        # Satisfy ResolveURL Probe
        self.send_response(200)
        self.send_header('Content-Type', 'video/x-flv')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if not manager.init_ready.wait(timeout=15):
            xbmc.log('AliveGR Proxy: Timeout waiting for MoQ Media.', xbmc.LOGDEBUG)
            return

        try:
            # 1. Write the mandatory FLV File Header
            self.wfile.write(b'FLV\x01\x05\x00\x00\x00\x09\x00\x00\x00\x00')

            # 2. Write the cached Video/Audio Sequence Headers
            if manager.video_init_tag:
                self.wfile.write(manager.video_init_tag)
            if manager.audio_init_tag:
                self.wfile.write(manager.audio_init_tag)
        except (ConnectionResetError, BrokenPipeError):
            xbmc.log('AliveGR Proxy: ResolveURL probe check finished.', xbmc.LOGDEBUG)
            return
        except Exception as e:
            return

        # Register the client and snapshot the buffer atomically against the
        # reader's append+fanout, so no tag is lost between snapshot and queue.
        client_q = queue.Queue(maxsize=300)
        with manager.lock:
            manager.clients.append(client_q)
            snapshot = list(manager.media_buffer)

        try:
            # 3. Write rolling buffer, then mux live
            for tag in snapshot:
                self.wfile.write(tag)

            xbmc.log('AliveGR Proxy: FLV muxing live to Kodi player...', xbmc.LOGDEBUG)

            while True:
                tag = client_q.get(timeout=15)
                self.wfile.write(tag)
        except:
            pass
        finally:
            with manager.lock:
                try:
                    manager.clients.remove(client_q)
                except ValueError:
                    pass

    def log_message(self, format, *args):
        return


class ThreadedHttpServer(socketserver.ThreadingMixIn, http.server.HTTPServer):

    allow_reuse_address = True
    daemon_threads = True


def start_server():

    global g_proxy_server

    if not g_proxy_server:

        try:

            g_proxy_server = ThreadedHttpServer(('', PROXY_PORT), ProxyRequestHandler)
            threading.Thread(target=g_proxy_server.serve_forever, daemon=True).start()

            xbmc.log(f'AliveGR Proxy: Listening on {PROXY_PORT}', xbmc.LOGDEBUG)

        except Exception as e:

            pass


def stop_server():

    global g_proxy_server, g_stream_manager

    if g_stream_manager:

        g_stream_manager.stop()
        g_stream_manager = None

    if g_proxy_server:

        threading.Thread(target=g_proxy_server.shutdown, daemon=True).start()
        g_proxy_server = None


class AliveGRService(xbmc.Monitor):

    def __init__(self):

        super(AliveGRService, self).__init__()
        self.addon = xbmcaddon.Addon(__addon_id__)
        self.auto_start = self.addon.getSetting('auto_start') == 'true'
        self.snapshot = self._settings_snapshot()

        start_server()

        if self.auto_start:
            self.launch_logic()

    def _settings_snapshot(self):

        try:
            addon = xbmcaddon.Addon(__addon_id__)
            settings_xml = xbmcvfs.translatePath(addon.getAddonInfo('path')) + '/resources/settings.xml'
            with open(settings_xml, encoding='utf-8') as f:
                ids = re.findall(r'<setting id="([^"]+)"', f.read())
            return {i: addon.getSetting(i) for i in ids}
        except Exception:
            return {}

    def onSettingsChanged(self):

        new_val = xbmcaddon.Addon(__addon_id__).getSetting('auto_start') == 'true'

        if new_val and not self.auto_start:

            self.launch_logic()

        self.auto_start = new_val

        # Refresh the container only when a setting other than bookkeeping
        # values actually changed, so programmatic writes (last_check, debug
        # reset) do not trigger spurious directory rebuilds.
        old_snapshot = self.snapshot
        new_snapshot = self._settings_snapshot()
        self.snapshot = new_snapshot

        if old_snapshot and new_snapshot:
            changed = {k for k in new_snapshot if new_snapshot[k] != old_snapshot.get(k)}
            refresh_needed = bool(changed - {'last_check', 'debug'})
        else:
            refresh_needed = True

        if refresh_needed and __addon_id__ in xbmc.getInfoLabel('Container.PluginName'):
            xbmc.executebuiltin('Container.Refresh')

    def onNotification(self, sender, method, data):

        global g_stream_manager

        # Player.OnStop fires for both user stops and natural playback end
        # (natural end carries data {"end": true}); there is no Player.OnEnded.
        if method == 'Player.OnStop' and g_stream_manager:

            xbmc.log('AliveGR Proxy: Playback stopped, killing MoQ socket.', xbmc.LOGDEBUG)
            g_stream_manager.stop()
            g_stream_manager = None

    def launch_logic(self):

        for _ in range(60):

            if xbmc.getCondVisibility('Window.IsActive(home)') or self.abortRequested():
                break
            if self.waitForAbort(0.2):
                return

        if not self.abortRequested():
            xbmc.executebuiltin(f'RunAddon({__addon_id__})')


if __name__ == '__main__':

    monitor = AliveGRService()

    while not monitor.abortRequested():

        if monitor.waitForAbort(5):
            break

    stop_server()