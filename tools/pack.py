#!/usr/bin/env python3
# builds the Chrome Web Store upload zip from an explicit allowlist.
# nothing is included unless listed here, so dev/test files never leak into the store package.
#
#   python3 tools/pack.py            -> keep manifest "key" (self-managed key, stable extension ID)
#   python3 tools/pack.py --drop-key -> strip manifest "key" (Google-managed key, store assigns a new ID)
#
# the manifest is rewritten through json so the "key" decision is explicit and the output is
# always valid json; every other field is passed through untouched.
import argparse
import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# runtime files only. each entry is a repo-relative path; directories are expanded to their
# listed suffixes. anything not here (test-harness/, native/, docs, dotfiles) never ships.
FILES = [
    "src/background.js",
    "src/content.js",
    "src/passkey-bridge.js",
    "src/passkey-guard.js",
    "src/protocol.js",
    "src/srp.js",
    "src/crypto.js",
    "src/popup.js",
    "src/popup.html",
    "src/popup.css",
    "icons/icon16.png",
    "icons/icon48.png",
    "icons/icon128.png",
    "fonts/OpenRunde-Regular.woff2",
    "fonts/OpenRunde-Medium.woff2",
    "fonts/OpenRunde-Semibold.woff2",
]


def load_manifest(drop_key):
    with open(os.path.join(ROOT, "manifest.json"), encoding="utf-8") as f:
        m = json.load(f)
    if drop_key:
        m.pop("key", None)
    return m


def main():
    ap = argparse.ArgumentParser(description="pack the extension for the Chrome Web Store")
    ap.add_argument("--drop-key", action="store_true",
                    help="remove manifest 'key' (use when the store manages the signing key)")
    ap.add_argument("-o", "--out", help="output zip path (default dist/<name>-<version>.zip)")
    args = ap.parse_args()

    manifest = load_manifest(args.drop_key)
    manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

    version = manifest["version"]
    out = args.out or os.path.join(ROOT, "dist", f"open-icloud-passwords-{version}.zip")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    missing = [p for p in FILES if not os.path.isfile(os.path.join(ROOT, p))]
    if missing:
        sys.exit("missing allowlisted files:\n  " + "\n  ".join(missing))

    if os.path.exists(out):
        os.remove(out)

    # deterministic zip: fixed timestamp + sorted entries so identical inputs hash identically
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        def add(arcname, data):
            info = zipfile.ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)

        add("manifest.json", manifest_bytes)
        for path in FILES:
            with open(os.path.join(ROOT, path), "rb") as f:
                add(path, f.read())

    total = os.path.getsize(out)
    has_key = "key" in manifest
    print(f"packed {len(FILES) + 1} files -> {os.path.relpath(out, ROOT)} ({total} bytes)")
    print(f"manifest key: {'kept (stable ID)' if has_key else 'dropped (store-managed ID)'}")


if __name__ == "__main__":
    main()
