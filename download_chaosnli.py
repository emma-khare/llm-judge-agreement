"""Fetch ChaosNLI and verify it, so human_ceiling.py can run.

ChaosNLI (Nie et al., 2020) is released under CC BY-NC 4.0, so the data is not
committed to this repository -- only this downloader is. It pins an exact
Hugging Face revision and checks every file's SHA-256 against the values in the
ChaosNLI repository, so a silently changed or truncated download fails loudly
instead of producing wrong statistics.

Run:  python3 download_chaosnli.py
Then: python3 human_ceiling.py
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

REVISION = "eb7cc18dbfa0f161d93a2b22c7856ca0faafcf2b"
BASE_URL = f"https://huggingface.co/datasets/earino/chaosnli/resolve/{REVISION}/raw/"

CHECKSUMS = {
    "README.txt": "b02af8460b221a1a1a629da0d528a87e820a7d76f2772599360608e51de50f1b",
    "chaosNLI_snli.jsonl": "99f9015ddda7d85f66a087452bc30d53974314fe27e7d589e2f41ad44bd509c1",
    "chaosNLI_mnli_m.jsonl": "8eb49b589488e7b1a9ec95fb8a864bd50f0509b4f808eed0aed3f8167617664d",
    "chaosNLI_alphanli.jsonl": "f55817ecc11a02ba3030cd7d2c567d23843456809020723abad53f4fde024c9e",
}

TARGET = Path(__file__).parent / "data" / "chaosnli"


def fetch(filename, checksum):
    destination = TARGET / filename
    if destination.is_file():
        if hashlib.sha256(destination.read_bytes()).hexdigest() == checksum:
            print(f"  ok      {filename} (already present, checksum matches)")
            return
        print(f"  stale   {filename} (checksum mismatch, re-downloading)")
    with urllib.request.urlopen(BASE_URL + filename, timeout=90) as response:
        content = response.read()
    actual = hashlib.sha256(content).hexdigest()
    if actual != checksum:
        raise SystemExit(f"checksum mismatch for {filename}\n  expected {checksum}\n  got      {actual}")
    destination.write_bytes(content)
    print(f"  fetched {filename} ({len(content):,} bytes)")


def main():
    print(f"ChaosNLI -> {TARGET}")
    TARGET.mkdir(parents=True, exist_ok=True)
    for filename, checksum in CHECKSUMS.items():
        try:
            fetch(filename, checksum)
        except OSError as exc:
            print(f"  FAILED  {filename}: {exc}", file=sys.stderr)
            raise SystemExit(1)
    print("\nDone. Next: python3 human_ceiling.py")


if __name__ == "__main__":
    main()
