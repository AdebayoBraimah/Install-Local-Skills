from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from obsidian_llamaindex_rag.constants import CONDA_ENV_NAME


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/update the obsidian-rag conda env.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest and validation after env update.")
    args = parser.parse_args()

    rag_dir = Path(__file__).resolve().parent
    config_path = rag_dir / "config.yaml"
    example_path = rag_dir / "config.example.yaml"
    if not config_path.exists():
        shutil.copy2(example_path, config_path)
        print(f"Created {config_path} from example config.")

    conda = shutil.which("conda")
    if not conda:
        print("conda was not found on PATH.", file=sys.stderr)
        return 1

    _run([conda, "env", "update", "-n", CONDA_ENV_NAME, "-f", str(rag_dir / "environment.yml"), "--prune"])

    if args.skip_tests:
        return 0

    _run([conda, "run", "-n", CONDA_ENV_NAME, "pytest", "-q", "-m", "not integration", str(rag_dir / "tests")])
    _run([conda, "run", "-n", CONDA_ENV_NAME, "python", str(rag_dir / "validate_llama_index.py")])
    return 0


def _run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    raise SystemExit(main())

