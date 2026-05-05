import subprocess
import sys


def test_run_evaluation_help_imports_from_repo_root():
    result = subprocess.run(
        [sys.executable, "scripts/run_evaluation.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--dataset" in result.stdout
    assert "--provider" in result.stdout
