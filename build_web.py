"""Gera `jogo/build/web` com a entrada assíncrona correta do pygbag."""

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parent
GAME_DIR = ROOT / "jogo"
BUILD_DIR = GAME_DIR / "build"
WEB_BUILD_DIR = BUILD_DIR / "web"
WEB_CACHE_DIR = BUILD_DIR / "web-cache"


def _ignore_source(_directory, names):
    ignored = {"build", "__pycache__"}
    return [name for name in names if name in ignored or name.endswith(".pyc")]


def _replace_generated_build(source):
    destination = WEB_BUILD_DIR.resolve()
    expected_parent = BUILD_DIR.resolve()
    if destination.parent != expected_parent or destination.name != "web":
        raise RuntimeError(f"destino de build inesperado: {destination}")
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def main():
    try:
        import pygbag
    except ImportError as error:
        raise SystemExit(
            "pygbag não está instalado. Execute: "
            ".venv/Scripts/python.exe -m pip install pygbag"
        ) from error

    with TemporaryDirectory(prefix="echoes-web-build-") as directory:
        staging = Path(directory) / "jogo"
        shutil.copytree(GAME_DIR, staging, ignore=_ignore_source)
        # O runtime do pygbag sempre procura assets/main.py. A troca ocorre
        # só na cópia temporária; jogo/main.py permanece sendo o desktop.
        shutil.copy2(staging / "main_web.py", staging / "main.py")
        cdn = f"https://pygame-web.github.io/cdn/{pygbag.VERSION}/"
        template = WEB_CACHE_DIR / (
            hashlib.md5(f"{cdn}default.tmpl".encode()).hexdigest() + ".tmpl"
        )
        icon = WEB_CACHE_DIR / (
            hashlib.md5(f"{cdn}favicon.png".encode()).hexdigest() + ".png"
        )
        command = [
            sys.executable,
            "-X",
            "utf8",
            "-B",
            "-m",
            "pygbag",
            "--build",
            "--no_opt",
        ]
        if template.is_file():
            command.extend(("--template", str(template)))
        if icon.is_file():
            command.extend(("--icon", str(icon)))
        command.append("main.py")
        subprocess.run(command, cwd=staging, check=True)
        generated = staging / "build" / "web"
        if not (generated / "index.html").is_file():
            raise RuntimeError("o pygbag não gerou build/web/index.html")
        _replace_generated_build(generated)

    print(f"Build web concluído em: {WEB_BUILD_DIR}")


if __name__ == "__main__":
    main()
