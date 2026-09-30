import subprocess
from pathlib import Path

if __name__ == "__main__":
    frontend = Path(__file__).parent / "src" / "frontend.py"
    subprocess.run(
        ["uv", "run", "streamlit", "run", str(frontend)],
        check=True,
        cwd=Path(__file__).parent,
    )
