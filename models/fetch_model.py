"""Development-only download from the ONNX project's official repository."""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parent
REPO = "https://api.github.com/repos/onnx/models/commits/main"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "local-ko-model-setup"}), timeout=90) as response:
        return response.read()


def main():
    revision = json.loads(get(REPO))["sha"]
    base = f"https://raw.githubusercontent.com/onnx/models/{revision}"
    files = {
        "mobilenetv2-12.onnx": f"https://media.githubusercontent.com/media/onnx/models/{revision}/validated/vision/classification/mobilenet/model/mobilenetv2-12.onnx",
        "synset.txt": base + "/validated/vision/classification/synset.txt",
        "MODEL-README.md": base + "/validated/vision/classification/mobilenet/README.md",
        "LICENSE": base + "/LICENSE",
    }
    manifest = {"model": "MobileNet V2 ONNX opset12", "repository": "https://github.com/onnx/models", "revision": revision, "license": "Apache-2.0", "files": {}}
    for name, url in files.items():
        content = get(url)
        if name.endswith(".onnx") and len(content) < 1_000_000:
            raise RuntimeError("Model download was not the binary model")
        (ROOT / name).write_bytes(content)
        manifest["files"][name] = {"source": url, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"revision": revision, "model_bytes": manifest["files"]["mobilenetv2-12.onnx"]["bytes"]}))


if __name__ == "__main__":
    main()
