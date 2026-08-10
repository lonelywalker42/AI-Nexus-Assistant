"""Generate the Tauri updater manifest from signed NSIS updater artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from urllib.parse import quote


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_RELEASE_DIR = PROJECT_DIR / "release"
GITHUB_REPO = "lonelywalker42/AI-Nexus-Assistant"


def github_asset_name(filename: str) -> str:
    """Return a stable GitHub Release asset name without server-side rewriting."""
    return filename.replace(" ", "-")


def get_version() -> str:
    return (PROJECT_DIR / "VERSION").read_text(encoding="utf-8").strip()


def find_signed_updater(release_dir: Path, version: str) -> tuple[Path, Path]:
    """Return the sole current-version NSIS installer and its v2 signature."""
    installers = sorted(release_dir.glob(f"*_{version}_*-setup.exe"))
    if len(installers) != 1:
        raise RuntimeError(
            f"Expected one NSIS updater installer for {version}, found {len(installers)}"
        )

    installer = installers[0]
    signature = Path(f"{installer}.sig")
    if not signature.is_file() or not signature.read_text(encoding="utf-8").strip():
        raise RuntimeError(f"Updater signature is missing or empty: {signature}")
    return installer, signature


def generate_latest_json(
    release_dir: Path = DEFAULT_RELEASE_DIR,
    version: str | None = None,
) -> Path:
    """Create latest.json using the signature emitted by the Tauri bundler."""
    version = version or get_version()
    installer, signature_path = find_signed_updater(release_dir, version)
    signature = signature_path.read_text(encoding="utf-8").strip()
    asset_name = quote(github_asset_name(installer.name))

    manifest = {
        "version": version,
        "notes": f"AI Nexus Assistant v{version}",
        "pub_date": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platforms": {
            "windows-x86_64": {
                "signature": signature,
                "url": (
                    f"https://github.com/{GITHUB_REPO}/releases/download/"
                    f"v{version}/{asset_name}"
                ),
            }
        },
    }

    output = release_dir / "latest.json"
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default=get_version())
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE_DIR)
    args = parser.parse_args()
    output = generate_latest_json(args.release_dir.resolve(), args.version)
    print(f"Generated updater manifest: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
