from __future__ import annotations

import os
import shutil
import subprocess
import re
from pathlib import Path
from typing import Callable


def review_page_numbers(document: dict) -> list[int]:
    return [int(page["page"]) for page in document.get("pages", []) if page.get("review_required")]


def _powerpoint_export(source: Path, export_dir: Path) -> None:
    source_ps = str(source.resolve()).replace("'", "''")
    export_ps = str(export_dir.resolve()).replace("'", "''")
    script = (
        "$ppt = New-Object -ComObject PowerPoint.Application; "
        f"$presentation = $ppt.Presentations.Open('{source_ps}', $true, $true, $false); "
        f"$presentation.Export('{export_ps}', 'PNG'); "
        "$presentation.Close(); $ppt.Quit()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        timeout=120,
        text=True,
    )


def _libreoffice_export(source: Path, export_dir: Path) -> None:
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise OSError("LibreOffice is not installed or not available on PATH.")
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise OSError("pdftoppm is not installed or not available on PATH.")
    export_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            binary,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(export_dir.resolve()),
            str(source.resolve()),
        ],
        check=True,
        capture_output=True,
        timeout=180,
        text=True,
    )
    pdf_path = export_dir / f"{source.stem}.pdf"
    if not pdf_path.exists():
        pdf_candidates = list(export_dir.glob("*.pdf"))
        if not pdf_candidates:
            raise OSError("LibreOffice did not produce a PDF file for Slides rendering.")
        pdf_path = pdf_candidates[0]
    subprocess.run(
        [pdftoppm, "-png", str(pdf_path.resolve()), str((export_dir / "Slide").resolve())],
        check=True,
        capture_output=True,
        timeout=180,
        text=True,
    )


def system_exporter(source: Path, export_dir: Path) -> None:
    if os.name == "nt":
        try:
            _powerpoint_export(source, export_dir)
            return
        except Exception:
            if not (shutil.which("soffice") or shutil.which("libreoffice")):
                raise
    _libreoffice_export(source, export_dir)


def export_review_pages(
    source: Path,
    page_numbers: list[int],
    output_dir: Path,
    exporter: Callable[[Path, Path], None] = system_exporter,
) -> dict:
    if not page_numbers:
        return {"images": {}, "warning": ""}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_pages_dir = output_dir / "_all"
    try:
        if all_pages_dir.exists():
            shutil.rmtree(all_pages_dir)
        exporter(Path(source), all_pages_dir)
        images = {}
        exported_by_page = {}
        for path in all_pages_dir.iterdir():
            if not path.is_file() or path.suffix.lower() != ".png":
                continue
            match = re.search(r"(\d+)$", path.stem)
            if match:
                exported_by_page[int(match.group(1))] = path
        for page in page_numbers:
            source_image = exported_by_page.get(page)
            if source_image:
                target = output_dir / f"page-{page}.png"
                shutil.copyfile(source_image, target)
                images[page] = target
        return {"images": images, "warning": "" if len(images) == len(page_numbers) else "Some Slides pages could not be rendered."}
    except Exception as error:
        return {"images": {}, "warning": str(error)}
    finally:
        if all_pages_dir.exists():
            shutil.rmtree(all_pages_dir, ignore_errors=True)
