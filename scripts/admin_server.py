import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/plaque":
                plaques_path = ROOT / "data" / "plaques.json"
                data = {"plaques": {}}
                if plaques_path.exists():
                    data = json.loads(plaques_path.read_text(encoding="utf-8"))
                    data.setdefault("plaques", {})
                work_id = body.get("id")
                if not work_id:
                    self._send(400, {"ok": False, "error": "Missing id"})
                    return
                data["plaques"][work_id] = body.get("text") or ""
                plaques_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                self._send(200, {"ok": True})
                return

            if path == "/api/label-style":
                style_path = ROOT / "data" / "label-style.json"
                style_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
                self._send(200, {"ok": True})
                return

            if path == "/api/set-genre":
                wiki = body.get("wiki") or ""
                genre = body.get("genre") or "other"
                works_path = ROOT / "data" / "works.json"
                data = json.loads(works_path.read_text(encoding="utf-8"))
                found = False
                for work in data.get("works", []):
                    if work.get("wiki") == wiki:
                        work["genre"] = genre
                        found = True
                        break
                if not found:
                    self._send(404, {"ok": False, "error": "Work not found"})
                    return
                works_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                self._send(200, {"ok": True})
                return

            if path == "/api/remove-work":
                wiki = body.get("wiki") or ""
                qid = body.get("id") or wiki.rsplit("/", 1)[-1]
                works_path = ROOT / "data" / "works.json"
                rejected_path = ROOT / "data" / "rejected.json"
                plaques_path = ROOT / "data" / "plaques.json"
                data = json.loads(works_path.read_text(encoding="utf-8"))
                data["works"] = [w for w in data.get("works", []) if w.get("wiki") != wiki]
                works_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                rejected = {"rejected": []}
                if rejected_path.exists():
                    rejected = json.loads(rejected_path.read_text(encoding="utf-8"))
                    rejected.setdefault("rejected", [])
                if wiki not in rejected["rejected"]:
                    rejected["rejected"].append(wiki)
                if qid not in rejected["rejected"]:
                    rejected["rejected"].append(qid)
                rejected_path.write_text(json.dumps(rejected, indent=2), encoding="utf-8")
                if plaques_path.exists():
                    plaques = json.loads(plaques_path.read_text(encoding="utf-8"))
                    plaques.get("plaques", {}).pop(qid, None)
                    plaques_path.write_text(json.dumps(plaques, indent=2), encoding="utf-8")
                self._send(200, {"ok": True})
                return

            self._send(404, {"ok": False, "error": "Unknown API"})
        except Exception as error:
            self._send(500, {"ok": False, "error": str(error)})

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Admin server: http://127.0.0.1:8000/site/viewer.html?admin=1")
    print("Stop with Ctrl+C")
    server.serve_forever()