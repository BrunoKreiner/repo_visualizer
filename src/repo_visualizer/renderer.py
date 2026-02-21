import json
from pathlib import Path

from repo_visualizer.config import VisualizerConfig

_PLACEHOLDERS = [
    "__ARCHITECTURE_DATA__",
    "__COMPUTED_SMELLS__",
    "__NODE_METRICS__",
    "__FILE_TREE__",
    "__SOURCE_FILES__",
    "__CODE_MAP__",
    "__DIAGRAM_TITLE__",
]


def _safe_json_for_html(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=False)
    # Escape ALL </ sequences to prevent HTML parser from closing <script> tag.
    # <\/ in JS string literals is equivalent to </ but safe in HTML context.
    raw = raw.replace(chr(60) + chr(47), chr(60) + chr(92) + chr(47))
    for ph in _PLACEHOLDERS:
        raw = raw.replace(ph, ph[:2] + chr(8203) + ph[2:])
    return raw


def render_html(data: dict, smells: list, node_metrics: dict,
                file_tree: dict, source_files: dict, code_map: dict,
                config: VisualizerConfig) -> str:
    template_path = Path(__file__).parent / "template.html"
    template = template_path.read_text(encoding="utf-8")
    title = config.title or config.project_root.resolve().name
    html = template.replace("__ARCHITECTURE_DATA__", _safe_json_for_html(data))
    html = html.replace("__COMPUTED_SMELLS__", _safe_json_for_html(smells))
    html = html.replace("__NODE_METRICS__", _safe_json_for_html(node_metrics))
    html = html.replace("__FILE_TREE__", _safe_json_for_html(file_tree))
    html = html.replace("__SOURCE_FILES__", _safe_json_for_html(source_files))
    html = html.replace("__CODE_MAP__", _safe_json_for_html(code_map))
    html = html.replace("__DIAGRAM_TITLE__", _escape_html(title))
    return html


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _count_tree_files(node: dict):
    if node.get("type") == "file":
        yield node
    for child in node.get("children", []):
        yield from _count_tree_files(child)
