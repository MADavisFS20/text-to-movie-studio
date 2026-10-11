"""Tiny stdlib HTTP helpers (no third-party dependencies, so it installs anywhere, including Termux)."""
import json
import urllib.error
import urllib.parse
import urllib.request
import uuid


class HttpError(RuntimeError):
    pass


def request(method, url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        body = e.read()[:500].decode("utf-8", "replace")
        raise HttpError(f"{method} {url} -> HTTP {e.code}: {body}") from e
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise HttpError(f"{method} {url} failed: {e}") from e


def post_json(url, payload, headers=None, timeout=60):
    h = {"Content-Type": "application/json", **(headers or {})}
    return json.loads(request("POST", url, json.dumps(payload).encode(), h, timeout))


def get_json(url, headers=None, timeout=60):
    return json.loads(request("GET", url, None, headers, timeout))


def multipart(fields, files):
    """fields: {name: str}; files: {name: (filename, bytes, content_type)} -> (body, content_type)."""
    boundary = uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, (fn, data, ct) in files.items():
        out.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'
                   f"Content-Type: {ct}\r\n\r\n".encode() + data + b"\r\n")
    out.append(f"--{boundary}--\r\n".encode())
    return b"".join(out), f"multipart/form-data; boundary={boundary}"


def quote(s):
    return urllib.parse.quote(s, safe="")
