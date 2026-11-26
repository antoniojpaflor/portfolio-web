#!/usr/bin/env python3
"""
Genera y actualiza automáticamente `assets/manifest.json` a partir de todos los
archivos de imagen, vídeo y PDF encontrados en la carpeta `assets/`.

Uso:
    python update_manifest.py
    python update_manifest.py --watch
    python update_manifest.py --assets-dir assets --output assets/manifest.json
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp", ".svg"}
VIDEO_EXTS = {".mp4", ".webm", ".ogg", ".ogv", ".mov", ".m4v"}
PDF_EXTS = {".pdf"}

# Nodos válidos del portfolio: si colocas archivos en `assets/<node_id>/...`
# se asociarán automáticamente a ese nodo además de aparecer en el fondo.
VALID_NODE_IDS = {
    "freestyle-pica",
    "prover9-mace4",
    "gesture-glove",
    "rotombot",
    "etsiit-ugr",
    "big-school",
    "practicas-ugr",
    "curriculum",
    "contacto",
}


def detect_kind(path: Path) -> str | None:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in PDF_EXTS:
        return "pdf"
    return None


def scan_assets(assets_dir: Path, project_root: Path) -> list[dict]:
    entries: list[dict] = []
    if not assets_dir.exists():
        assets_dir.mkdir(parents=True, exist_ok=True)
        return entries

    for file_path in sorted(assets_dir.rglob("*"), key=lambda p: p.as_posix().lower()):
        if not file_path.is_file():
            continue
        # Ignorar archivos ocultos y el propio manifest.json
        if any(part.startswith(".") for part in file_path.relative_to(assets_dir).parts):
            continue
        if file_path.name.lower() == "manifest.json":
            continue

        kind = detect_kind(file_path)
        if not kind:
            continue

        rel_from_root = file_path.relative_to(project_root).as_posix()
        rel_from_assets = file_path.relative_to(assets_dir)

        entry: dict = {
            "name": file_path.name,
            "path": rel_from_root,
            "kind": kind,
        }

        # Si el archivo está dentro de una subcarpeta con el ID de un nodo, enlazarlo
        if len(rel_from_assets.parts) > 1:
            candidate_node = rel_from_assets.parts[0].lower()
            if candidate_node in VALID_NODE_IDS:
                entry["nodeId"] = candidate_node

        # Si el nombre contiene "_confidencial" o está en una subcarpeta "restringido"
        lower_parts = [p.lower() for p in rel_from_assets.parts]
        if "restringido" in lower_parts or "confidencial" in file_path.stem.lower():
            entry["confidential"] = True

        entries.append(entry)

    return entries


def write_manifest(assets_dir: Path, output_path: Path, project_root: Path) -> tuple[bool, list[dict]]:
    entries = scan_assets(assets_dir, project_root)
    serialized = json.dumps(entries, indent=2, ensure_ascii=False) + "\n"

    previous = output_path.read_text(encoding="utf-8") if output_path.exists() else None
    if previous == serialized:
        return False, entries

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8")
    return True, entries


def print_summary(entries: list[dict], output_path: Path, changed: bool) -> None:
    imgs = sum(1 for e in entries if e["kind"] == "image")
    vids = sum(1 for e in entries if e["kind"] == "video")
    pdfs = sum(1 for e in entries if e["kind"] == "pdf")
    status = "ACTUALIZADO" if changed else "SIN CAMBIOS"
    print(f"[{status}] {output_path.as_posix()} -> {len(entries)} archivos ({imgs} imgs, {vids} vídeos, {pdfs} PDFs)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza assets/manifest.json automáticamente.")
    parser.add_argument("--assets-dir", default="assets", help="Carpeta raíz de medios (por defecto: assets)")
    parser.add_argument("--output", default=None, help="Ruta del manifest de salida (por defecto: <assets-dir>/manifest.json)")
    parser.add_argument("--watch", action="store_true", help="Vigila cambios continuamente cada 2 segundos")
    parser.add_argument("--interval", type=float, default=2.0, help="Intervalo en segundos para --watch (por defecto: 2.0)")
    args = parser.parse_args()

    project_root = Path.cwd().resolve()
    assets_dir = (project_root / args.assets_dir).resolve()
    output_path = (project_root / args.output).resolve() if args.output else (assets_dir / "manifest.json")

    changed, entries = write_manifest(assets_dir, output_path, project_root)
    print_summary(entries, output_path.relative_to(project_root) if output_path.is_relative_to(project_root) else output_path, changed)

    if args.watch:
        print(f"Vigilando '{assets_dir}' cada {args.interval}s... Pulsa Ctrl+C para salir.")
        try:
            while True:
                time.sleep(args.interval)
                changed, entries = write_manifest(assets_dir, output_path, project_root)
                if changed:
                    rel_out = output_path.relative_to(project_root) if output_path.is_relative_to(project_root) else output_path
                    print_summary(entries, rel_out, changed=True)
        except KeyboardInterrupt:
            print("\nVigilancia detenida.")


if __name__ == "__main__":
    main()
