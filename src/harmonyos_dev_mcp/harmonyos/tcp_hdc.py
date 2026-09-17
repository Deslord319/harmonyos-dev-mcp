"""
TCP hdc client — direct TCP protocol implementation.

Bypasses subprocess hdc calls entirely. Connects to hdc server via TCP,
implements the hdc binary protocol (handshake + command dispatch).

This is the HarmonyOS-specific replacement for subprocess.run([hdc_path, ...]).
On macOS/Windows, the original subprocess approach works fine.
"""

import base64
import socket
import struct
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Protocol constants
BANNER = b"OHOS HDC"
BANNER_SIZE = 12
UNION_SIZE = 32  # MAX_CONNECTKEY_SIZE
HANDSHAKE_SIZE = BANNER_SIZE + UNION_SIZE  # 44

# Commands that don't need a connect key (server-level commands)
NO_KEY_PREFIXES = [
    b"list targets", b"tconn", b"checkserver", b"kill",
    b"start", b"fport ls", b"fport rm", b"version",
    b"help", b"wait", b"checkdevice", b"discover",
]


def _recv_exact(sock, n, timeout=15):
    sock.settimeout(timeout)
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError(f"Connection closed, got {len(data)}/{n} bytes")
        data += chunk
    return data


def _recv_packet(sock, timeout=15):
    header = _recv_exact(sock, 4, timeout)
    plen = struct.unpack(">I", header)[0]
    if plen == 0 or plen > 0x7FFFFFFF:
        raise ValueError(f"Invalid payload length: {plen}")
    return _recv_exact(sock, plen, timeout) if plen > 0 else b""


def _send_packet(sock, data):
    sock.sendall(struct.pack(">I", len(data)) + data)


def tcp_exec(
    command: str,
    connect_key: bytes = b"any",
    host: str = "127.0.0.1",
    port: int = 8710,
    timeout: int = 30,
    break_on_newline: bool = True,
) -> tuple:
    """Execute an hdc command via TCP.

    Returns (stdout, stderr, returncode).

    When break_on_newline is False (used for large output like base64 file
    dumps), the loop waits for idle timeout or connection close instead of
    breaking on the first newline, preventing data truncation.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)
    # Minimal delay to avoid overwhelming hdc server with rapid connections
    time.sleep(0.02)
    try:
        sock.connect((host, port))
    except Exception as e:
        return "", f"Cannot connect to hdc server {host}:{port}: {e}", 1

    try:
        # Handshake: receive server hello
        hs = _recv_packet(sock, timeout)
        if len(hs) < HANDSHAKE_SIZE:
            return "", "Handshake too short", 1
        if hs[:8] != BANNER:
            return "", f"Bad banner: {hs[:8]}", 1

        # Build client handshake response
        client_hs = bytearray(hs[:HANDSHAKE_SIZE])

        # Determine connect key
        needs_key = not any(command.encode().startswith(p) for p in NO_KEY_PREFIXES)
        key = connect_key if (needs_key and connect_key) else (b"any" if needs_key else b"")

        for i in range(UNION_SIZE):
            client_hs[BANNER_SIZE + i] = 0
        for i, b in enumerate(key):
            if i < UNION_SIZE:
                client_hs[BANNER_SIZE + i] = b

        _send_packet(sock, bytes(client_hs))

        # Send command
        _send_packet(sock, command.encode("utf-8") + b"\x00")

        # Receive response
        output = b""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                payload = _recv_packet(sock, timeout=5)
                if payload:
                    output += payload
                text = output.decode("utf-8", errors="replace")
                if "[Empty]" in text or "[Fail]" in text or "[Success]" in text:
                    break
                if break_on_newline and text.endswith("\n"):
                    break
            except socket.timeout:
                if output:
                    break
                continue
            except Exception:
                break

        text = output.decode("utf-8", errors="replace")
        if "[Fail]" in text:
            return text, "", 1
        return text, "", 0
    except Exception as e:
        return "", str(e), 1
    finally:
        sock.close()


def tcp_file_send(
    local_path: str,
    remote_path: str,
    connect_key: bytes = b"any",
    host: str = "127.0.0.1",
    port: int = 8710,
    timeout: int = 120,
) -> tuple:
    """Send a file to the device via parallel base64 chunks over TCP.

    Splits file into 48KB chunks (near HarmonyOS ARG_MAX limit), sends
    them concurrently via ThreadPoolExecutor (4 workers), then merges
    and decodes on device. Each chunk writes to a separate part file
    to avoid ordering issues with parallel writes.

    Returns (stdout, stderr, returncode).
    """
    with open(local_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("ascii")

    # 48KB raw → ~64KB base64 + command overhead, safely under ARG_MAX (64KB)
    RAW_CHUNK = 49152
    B64_CHUNK = int(RAW_CHUNK * 4 / 3)
    chunks = [
        b64[i * B64_CHUNK : (i + 1) * B64_CHUNK]
        for i in range((len(b64) + B64_CHUNK - 1) // B64_CHUNK)
    ]
    total = len(chunks)

    # Clear old parts
    tcp_exec(f"shell rm -f {remote_path}.b64.*", connect_key, host, port, timeout=10)

    def _send_chunk(idx, chunk):
        part_file = f"{remote_path}.b64.{idx}"
        cmd = f"shell printf '%s' '{chunk}' > {part_file}"
        out, err, rc = tcp_exec(cmd, connect_key, host, port, timeout=15)
        return idx, rc, err

    # Send chunks in parallel (4 workers)
    workers = min(4, total)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_send_chunk, i, c): i for i, c in enumerate(chunks)
        }
        for fut in as_completed(futures):
            idx, rc, err = fut.result()
            if rc != 0:
                # Cleanup on failure
                tcp_exec(f"shell rm -f {remote_path}.b64.*", connect_key, host, port, 10)
                return "", f"chunk {idx} failed: {err}", rc

    # Merge parts in order + decode
    parts = " ".join(f"{remote_path}.b64.{i}" for i in range(total))
    tcp_exec(f"shell cat {parts} | base64 -d > {remote_path}", connect_key, host, port, timeout=30)
    tcp_exec(f"shell rm -f {remote_path}.b64.*", connect_key, host, port, timeout=10)
    out, _, _ = tcp_exec(f"shell ls -la {remote_path}", connect_key, host, port, timeout=10)
    return out, "", 0


def parse_hdc_args(args: list, hdc_server: str = None) -> dict:
    """Parse hdc command-line args (as built by HdcBase._hdc_args).

    Returns dict with: command, device_id, server, connect_key
    """
    device_id = None
    server = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == "-s" and i + 1 < len(args):
            server = args[i + 1]
            i += 2
        elif args[i] == "-t" and i + 1 < len(args):
            device_id = args[i + 1]
            i += 2
        elif args[i] == "-l":
            i += 2 if i + 1 < len(args) else 1
        else:
            remaining.append(args[i])
            i += 1

    # Determine connect key
    server_addr = hdc_server or "127.0.0.1:8710"
    if device_id and device_id == server_addr:
        connect_key = b"any"
    elif device_id:
        connect_key = device_id.encode()
    else:
        connect_key = b""  # let tcp_exec decide

    return {
        "command": " ".join(remaining),
        "device_id": device_id,
        "server": server,
        "connect_key": connect_key,
    }
