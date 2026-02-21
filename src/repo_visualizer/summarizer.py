import ast
from pathlib import Path

from repo_visualizer.config import VisualizerConfig


def get_heuristic_description(name: str, source: str, node_type: str) -> str:
    try:
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                doc = ast.get_docstring(node)
                if doc:
                    return doc.strip().split(chr(10))[0][:120]
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                doc = ast.get_docstring(node)
                if doc:
                    return doc.strip().split(chr(10))[0][:120]
    except Exception:
        pass

    try:
        tree = ast.parse(source)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == name:
                methods = [n for n in node.body
                           if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                bases = [ast.unparse(b) for b in node.bases] if node.bases else []
                desc = f"Class with {len(methods)} methods"
                if bases:
                    desc += f", extends {chr(44).join(bases)}"
                return desc
    except Exception:
        pass
    return f"{node_type.title()} {name}"


def add_heuristic_descriptions(data: dict, config: VisualizerConfig) -> dict:
    root = config.project_root.resolve()
    for node in data.get("nodes", []):
        if node.get("description"):
            continue
        fp = node.get("file_path", "")
        if not fp:
            continue
        full_path = root / fp
        if not full_path.exists():
            continue
        try:
            source = full_path.read_text(encoding="utf-8")
        except Exception:
            continue
        node["description"] = get_heuristic_description(
            node.get("label", node["id"]), source, node.get("type", "module")
        )
    return data
