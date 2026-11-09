"""Record local-model execution on generated seed images, not model accuracy."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def save_report(report):
    directory = ROOT / "artifacts"
    directory.mkdir(exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (directory / f"model-verification-{stamp}.json").write_text(content, encoding="utf-8")
    (directory / "model-verification.json").write_text(content, encoding="utf-8")


def main():
    with urllib.request.urlopen("http://127.0.0.1:8081/api/bootstrap", timeout=10) as response:
        public_model = json.load(response)["model"]
    code = r'''
import hashlib,json,time
from pathlib import Path
import onnxruntime as ort
from app.images import LocalClassifier
started=time.perf_counter()
classifier=LocalClassifier(Path('/app/models'))
result={'model_ready':classifier.session is not None,'model_version':classifier.version,
        'runtime_version':ort.__version__,'load_seconds':round(time.perf_counter()-started,4),
        'providers':classifier.session.get_providers() if classifier.session is not None else [],
        'model_sha256':hashlib.sha256(Path('/app/models/mobilenetv2-12.onnx').read_bytes()).hexdigest(),
        'images':[]}
if classifier.session is not None:
    for name in ('coast','coffee','table','woodland'):
        started=time.perf_counter()
        try:
            tags=classifier.classify(Path('/app/seed-assets')/(name+'.png'))
            result['images'].append({'fixture':name,'executed':True,'tags':tags,'seconds':round(time.perf_counter()-started,4)})
        except Exception as exc:
            result['images'].append({'fixture':name,'executed':False,'error_type':type(exc).__name__})
print(json.dumps(result,ensure_ascii=False))
'''
    command = ["docker", "compose", "-p", "kou-community", "-f", str(ROOT / "compose.yaml"),
               "exec", "-T", "app", "python", "-c", code]
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    report = json.loads(process.stdout)
    report.update({"checked_at": datetime.now(timezone.utc).isoformat(), "bootstrap_model": public_model,
                   "scope": "execution smoke test on four generated local seed images; no labeled accuracy benchmark or user-preference inference",
                   "runtime_warning_present": bool(process.stderr.strip())})
    report["passed"] = public_model["status"] == "ready" and report["model_ready"] and len(report["images"]) == 4 and all(item["executed"] for item in report["images"])
    save_report(report)
    print(json.dumps(report, ensure_ascii=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        report = {"checked_at": datetime.now(timezone.utc).isoformat(), "passed": False,
                  "error_type": type(exc).__name__, "scope": "model execution check did not complete"}
        save_report(report)
        print(json.dumps(report))
        raise SystemExit(1)
