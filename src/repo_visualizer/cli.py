import argparse
import json
import sys
from pathlib import Path

from repo_visualizer import __version__
from repo_visualizer.analyzer import build_code_map
from repo_visualizer.config import VisualizerConfig
from repo_visualizer.graph import build_architecture_data
from repo_visualizer.renderer import render_html, _count_tree_files
from repo_visualizer.scanner import scan_python_files, scan_notebook_files, read_gitignore_text, scan_directory_tree, read_source_files
from repo_visualizer.smells import compute_smells
from repo_visualizer.summarizer import add_heuristic_descriptions


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="repo-visualizer",
        description="Generate interactive architecture diagrams for Python repositories",
    )
    parser.add_argument("path", nargs="?", default=".",
                        help="Repository root (default: .)")
    parser.add_argument("-o", "--output", default="architecture_diagram.html",
                        help="Output HTML file path")
    parser.add_argument("--title", default="",
                        help="Diagram title (default: directory name)")
    parser.add_argument("--exclude-dirs", default="",
                        help="Extra dirs to exclude (comma-separated)")
    parser.add_argument("--no-smells", action="store_true",
                        help="Disable smell detection")
    parser.add_argument("--no-source", action="store_true",
                        help="Do not embed source code (smaller output)")
    parser.add_argument("--max-nodes", type=int, default=100,
                        help="Maximum nodes (default: 100)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of HTML")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    parser.add_argument("--version", action="version",
                        version="%(prog)s " + __version__)

    args = parser.parse_args()

    config = VisualizerConfig(
        project_root=Path(args.path).resolve(),
        output_path=Path(args.output),
        title=args.title,
        detect_smells=not args.no_smells,
        embed_source=not args.no_source,
        max_nodes=args.max_nodes,
        verbose=args.verbose,
        output_json=args.json,
    )

    if args.exclude_dirs:
        for d in args.exclude_dirs.split(","):
            config.excluded_dirs.add(d.strip())

    generate(config)


def generate(config: VisualizerConfig) -> None:
    root = config.project_root.resolve()
    if not root.is_dir():
        print("Error: not a directory: " + str(root), file=sys.stderr)
        sys.exit(1)

    if config.verbose:
        print("Scanning " + str(root) + "...")

    py_files = scan_python_files(config)
    nb_files = scan_notebook_files(config)
    if config.verbose:
        print("  Found " + str(len(py_files)) + " Python files, " + str(len(nb_files)) + " notebooks")

    data = build_architecture_data(config, py_files + nb_files)
    data = add_heuristic_descriptions(data, config)

    if config.output_json:
        out = config.output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print("Generated JSON: " + str(out))
        return

    smells, node_metrics = [], {}
    if config.detect_smells:
        smells, node_metrics = compute_smells(data, root, config.smell_thresholds)

    file_tree = scan_directory_tree(config, data)
    source_files = (read_source_files(config, data.get("nodes", []))
                    if config.embed_source else {})
    code_map = build_code_map(root, data)

    readme_text = ""
    for rname in ("README.md", "readme.md", "README.rst", "README.txt"):
        rpath = root / rname
        if rpath.exists():
            try:
                readme_text = rpath.read_text(encoding="utf-8", errors="replace")[:2000]
            except Exception:
                pass
            break

    gitignore_text = read_gitignore_text(root)

    if config.verbose:
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        groups = data.get("groups", [])
        w = sum(1 for s in smells if s.get("severity") == "warning")
        i_count = sum(1 for s in smells if s.get("severity") == "info")
        print("  " + str(len(nodes)) + " nodes, " + str(len(edges)) + " edges, " + str(len(groups)) + " groups")
        print("  " + str(len(smells)) + " smells (" + str(w) + " warnings, " + str(i_count) + " info)")
        print("  Embedded " + str(len(source_files)) + " source files")
        print("  Code map: " + str(len(code_map)) + " files")
        tree_count = sum(1 for _ in _count_tree_files(file_tree))
        print("  File tree: " + str(tree_count) + " files")

    html = render_html(data, smells, node_metrics, file_tree,
                       source_files, code_map, config, readme_text, gitignore_text)

    out = config.output_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("Generated: " + str(out))
    print("Open in browser: file:///" + str(out.absolute()))


if __name__ == "__main__":
    main()
