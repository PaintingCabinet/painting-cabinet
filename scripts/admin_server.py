import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PLAQUES = DATA / "plaques.json"
STYLE = DATA / "label-style.json"
WORKS = DATA / "works.json"
REJECTED = DATA / "rejected.json"

def read_json(path, fallback):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return fallback

def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return self._send_json({"ok": False, "error": "bad json"}, 400)

        if self.path == "/api/plaque":
            work_id = data.get("id", "").strip()
            text = data.get("text", "")
            if not work_id:
                return self._send_json({"ok": False, "error": "missing id"}, 400)
            store = read_json(PLAQUES, {"plaques": {}})
            store.setdefault("plaques", {})[work_id] = text
            write_json(PLAQUES, store)
            return self._send_json({"ok": True})

        if self.path == "/api/label-style":
            write_json(STYLE, data)
            return self._send_json({"ok": True})

        if self.path == "/api/remove-work":
            wiki = (data.get("wiki") or "").strip()
            qid = (data.get("id") or "").strip()
            if not wiki and not qid:
                return self._send_json({"ok": False, "error": "missing id"}, 400)

            catalog = read_json(WORKS, {"works": []})
            kept = []
            removed = None
            for work in catalog.get("works", []):
                work_qid = (work.get("wiki") or "").rsplit("/", 1)[-1]
                if work.get("wiki") == wiki or work_qid == qid:
                    removed = work
                    continue
                kept.append(work)
            catalog["works"] = kept
            write_json(WORKS, catalog)

            rejected = read_json(REJECTED, {"rejected": []})
            ids = rejected.setdefault("rejected", [])
            mark = wiki or ("http://www.wikidata.org/entity/" + qid)
            if mark not in ids:
                ids.append(mark)
            if qid and qid not in ids:
                ids.append(qid)
            write_json(REJECTED, rejected)

            plaques = read_json(PLAQUES, {"plaques": {}})
            if qid and qid in plaques.get("plaques", {}):
                del plaques["plaques"][qid]
                write_json(PLAQUES, plaques)

            return self._send_json({"ok": True, "removed": bool(removed)})

        self._send_json({"ok": False, "error": "unknown path"}, 404)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Admin server: http://127.0.0.1:8000/site/viewer.html?admin=1")
    print("Stop with Ctrl+C")
    server.serve_forever()