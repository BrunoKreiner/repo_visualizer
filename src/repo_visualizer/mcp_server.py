"""MCP server for repo-visualizer."""
import json
import sys
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("MCP support requires the mcp package. Install with: pip install repo-visualizer[mcp]", file=sys.stderr)
    sys.exit(1)

from repo_visualizer.config import VisualizerConfig
from repo_visualizer.graph import build_architecture_data
from repo_visualizer.scanner import scan_python_files
from repo_visualizer.smells import compute_smells
from repo_visualizer.summarizer import add_heuristic_descriptions

mcp = FastMCP("repo-visualizer")


def _build_config(path: str, max_nodes: int = 100, title: str = "",
                  output: str = "", exclude_dirs: str = "") -> VisualizerConfig:
    root = Path(path).resolve()
    config = VisualizerConfig(
        project_root=root,
        output_path=Path(output) if output else root / "architecture_diagram.html",
        title=title,
        max_nodes=max_nodes,
    )
    if exclude_dirs:
        for d in exclude_dirs.split(","):
            config.excluded_dirs.add(d.strip())
    return config


@mcp.tool()
def analyze_project(path: str, max_nodes: int = 100) -> str:
    """Analyze a Python project and return an architecture summary.

    Scans Python files, builds the dependency graph, detects code smells,
    and returns a structured text summary optimized for LLM consumption.

    Args:
        path: Absolute path to the project root directory.
        max_nodes: Maximum nodes to include (default 100).
    """
    config = _build_config(path, max_nodes)
    root = config.project_root
    py_files = scan_python_files(config)
    data = build_architecture_data(config, py_files)
    data = add_heuristic_descriptions(data, config)
    smells, _ = compute_smells(data, root, config.smell_thresholds)
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    groups = data.get("groups", [])
    imps: dict[str, list[str]] = {}
    imp_by: dict[str, list[str]] = {}
    for e in edges:
        imps.setdefault(e["from"], []).append(e["to"])
        imp_by.setdefault(e["to"], []).append(e["from"])
    entries = [n for n in nodes if not imp_by.get(n["id"])]
    chains: list[list[str]] = []
    for en in entries:
        best = [en["id"]]
        queue = [[en["id"]]]
        while queue:
            cur = queue.pop(0)
            if len(cur) > 5:
                continue
            last = cur[-1]
            nexts = imps.get(last, [])
            for nx in nexts:
                if nx not in cur:
                    np = cur + [nx]
                    if len(np) > len(best):
                        best = np
                    if len(np) < 5:
                        queue.append(np)
            if not nexts and len(cur) > len(best):
                best = cur
        if len(best) >= 3:
            chains.append(best)
    chains.sort(key=len, reverse=True)
    warnings = [s for s in smells if s.get("severity") == "warning"]
    out = []
    out.append(f"# Architecture Summary: {root.name}")
    out.append(f"**{len(nodes)} nodes, {len(edges)} edges, {len(groups)} groups, {len(py_files)} Python files**")
    out.append("")
    if entries:
        out.append("## Entry Points")
        for n in entries[:10]:
            desc = (n.get("description") or "")[:80]
            out.append(f"- **{n['id']}** [{n.get('type', 'module')}] `{n.get('file_path', '')}`")
            if desc:
                out.append(f"  {desc}")
        out.append("")
    if chains:
        out.append("## Key Dependency Chains")
        seen: set[str] = set()
        for c in chains[:5]:
            key = " -> ".join(c)
            if key not in seen:
                seen.add(key)
                out.append(f"- {key}")
        out.append("")
    tier_counts: dict[int, int] = {}
    for n in nodes:
        t = n.get("tier", 0)
        tier_counts[t] = tier_counts.get(t, 0) + 1
    if tier_counts:
        out.append("## Tier Distribution")
        for t in sorted(tier_counts):
            out.append(f"- Tier {t}: {tier_counts[t]} nodes")
        out.append("")
    if warnings:
        out.append(f"## Architectural Warnings ({len(warnings)})")
        for w in warnings[:15]:
            out.append(f"- {w.get('title', '')} ({w.get('metric', '')})")
        out.append("")
    out.append("## All Nodes")
    for n in nodes:
        nid = n["id"]
        imp = ", ".join(imps.get(nid, [])) or "none"
        iby = ", ".join(imp_by.get(nid, [])) or "none"
        out.append(f"- **{nid}** [{n.get('type', 'module')}] `{n.get('file_path', '')}` tier={n.get('tier', '?')}")
        out.append(f"  imports: {imp} | imported_by: {iby}")
    return chr(10).join(out)


@mcp.tool()
def generate_diagram(path: str, output: str = "architecture_diagram.html",
                     title: str = "", max_nodes: int = 100,
                     exclude_dirs: str = "") -> str:
    """Generate an interactive HTML architecture diagram for a Python project.

    Creates a self-contained HTML file with an interactive visualization
    of the project architecture including dependency graph, tier layout,
    code smells, and embedded source code.

    Args:
        path: Absolute path to the project root directory.
        output: Output HTML file path (default: architecture_diagram.html).
        title: Diagram title (default: directory name).
        max_nodes: Maximum nodes to include (default 100).
        exclude_dirs: Comma-separated directory names to exclude.
    """
    from repo_visualizer.cli import generate as cli_generate
    config = _build_config(path, max_nodes, title, output, exclude_dirs)
    config.verbose = False
    cli_generate(config)
    return f"Diagram generated: {config.output_path.resolve()}"


@mcp.tool()
def get_architecture_json(path: str, max_nodes: int = 100) -> str:
    """Return raw architecture data as JSON for a Python project.

    Scans the project and returns the full architecture data structure
    including nodes, edges, groups, and tiers.

    Args:
        path: Absolute path to the project root directory.
        max_nodes: Maximum nodes to include (default 100).
    """
    config = _build_config(path, max_nodes)
    py_files = scan_python_files(config)
    data = build_architecture_data(config, py_files)
    data = add_heuristic_descriptions(data, config)
    return json.dumps(data, indent=2)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
