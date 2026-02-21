from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from repo_visualizer.config import VisualizerConfig


def scan_python_files(config: VisualizerConfig) -> List[Path]:
    root = config.project_root.resolve()
    py_files: List[Path] = []
    _scan_dir(root, root, py_files, config)
    return py_files


def _scan_dir(directory: Path, root: Path, result: List[Path],
              config: VisualizerConfig, depth: int = 0) -> None:
    if depth > 50:
        return
    # Skip symbolic links that point outside the root (prevent traversal)
    try:
        resolved = directory.resolve()
        resolved.relative_to(root.resolve())
    except ValueError:
        return
    try:
        entries = sorted(directory.iterdir(),
                         key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return
    for entry in entries:
        name = entry.name
        if name.startswith('.') and name not in ('.env.example',):
            continue
        if entry.is_dir():
            if name in config.excluded_dirs:
                continue
            if any(name.startswith(p) for p in config.excluded_prefixes):
                continue
            _scan_dir(entry, root, result, config, depth + 1)
        elif entry.is_file() and entry.suffix == '.py':
            result.append(entry)


def scan_directory_tree(config: VisualizerConfig, data: dict) -> dict:
    root = config.project_root.resolve()
    file_to_nodes: Dict[str, List[str]] = defaultdict(list)
    for n in data.get('nodes', []):
        fp = n.get('file_path', '')
        if fp:
            file_to_nodes[fp].append(n['id'])

    def _walk(directory: Path, rel_prefix: str, depth: int = 0) -> dict:
        children = []
        if depth > 50:
            return {"name": directory.name, "type": "dir", "children": []}
        try:
            entries = sorted(directory.iterdir(),
                             key=lambda e: (not e.is_dir(), e.name.lower()))
        except PermissionError:
            return {"name": directory.name, "type": "dir", "children": []}
        for entry in entries:
            name = entry.name
            if name.startswith('.') and name not in ('.env.example',):
                continue
            rel_path = f"{rel_prefix}/{name}" if rel_prefix else name
            if entry.is_dir():
                if name in config.excluded_dirs:
                    continue
                if any(name.startswith(p) for p in config.excluded_prefixes):
                    continue
                child = _walk(entry, rel_path, depth + 1)
                if child['children']:
                    children.append(child)
            elif entry.is_file():
                suffix = entry.suffix.lower()
                if suffix in config.file_extensions:
                    node_ids = file_to_nodes.get(rel_path, [])
                    children.append({
                        "name": name,
                        "type": "file",
                        "path": rel_path,
                        "referenced": len(node_ids) > 0,
                        "nodeIds": node_ids,
                    })
        return {"name": directory.name if rel_prefix else ".",
                "type": "dir", "children": children}

    return _walk(root, "")


def read_source_files(config: VisualizerConfig, nodes: list) -> Dict[str, str]:
    root = config.project_root.resolve()
    max_size = config.max_file_size_kb * 1024
    seen: Set[str] = set()
    result: Dict[str, str] = {}
    for n in nodes:
        fp = n.get('file_path', '')
        if not fp or fp in seen:
            continue
        seen.add(fp)
        full = root / fp
        if not full.exists():
            continue
        try:
            size = full.stat().st_size
            if size > max_size:
                continue
            result[fp] = full.read_text(encoding='utf-8')
        except Exception:
            pass
    return result
