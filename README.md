# repo-visualizer

Generate interactive architecture diagrams for any Python repository with a single command.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)

## Install

```bash
pip install --upgrade git+https://github.com/BrunoKreiner/repo_visualizer.git
```

## Usage

```bash
# Generate diagram for current directory
repo_visualizer .

# Specify output and title
repo_visualizer /path/to/project -o diagram.html --title "My Project"

# Output raw JSON (for custom processing)
repo_visualizer . --json -o data.json

# Verbose mode
repo_visualizer . -v
```

> Both `repo_visualizer` and `python -m repo_visualizer` work. On some systems `repo-visualizer` (with a hyphen) also works.

Then open the generated HTML file in your browser.

## What You Get

An interactive single-file HTML diagram with:

- **Node cards** for every class, module, and script with methods, fields, and type signatures
- **Dependency edges** auto-detected from import analysis
- **Tiered layout** via topological sort (entry points at top)
- **Directory-based grouping** with color coding
- **File explorer** with source code viewer and syntax highlighting
- **Code map** with clickable cross-references between functions and classes
- **Architectural smell detection** for common code quality issues
- **AI Layout** -- copy a prompt to any LLM to refine tier and panel placement
- **Task tracking** -- add tasks linked to specific nodes, with priorities and export

## Interactive Features

| Feature | How |
|---------|-----|
| **Select a node** | Click any card |
| **Expand details** | Click the arrow button at the bottom of a card |
| **View source code** | Click the `</>` button on a card, or press `C` |
| **Search nodes** | Type in the search bar |
| **Zoom** | `Ctrl+Scroll` or use the +/- buttons |
| **Context menu** | Right-click any card for analysis prompts |
| **Add a task** | Press `N` with a node selected, or right-click > Add task |
| **AI Layout** | Click "AI Layout" to get a prompt for LLM-powered diagram reorganization |

## Smell Detection

repo-visualizer detects architectural smells:

| Smell | Severity | What It Detects |
|-------|----------|-----------------|
| **God Class** | warning | Classes with 8+ members AND 4+ outgoing dependencies |
| **Hub/Bottleneck** | warning | Nodes with high incoming AND outgoing coupling (Ca>=4, Ce>=4) |
| **Unstable Dependency** | warning | Highly unstable modules (I>0.8) that many others depend on |
| **Dependency Cycle** | warning | Circular import chains between modules |
| **High Complexity** | warning | Functions with cyclomatic complexity >= 15 |
| **Shotgun Surgery** | info | Modules depended on by 5+ others (changes ripple widely) |
| **Feature Envy** | info | Modules with more cross-group than same-group dependencies |
| **Long Method** | info | Functions exceeding 80 lines |
| **Long Parameter List** | info | Functions with 7+ parameters |
| **Large Class** | info | Classes with 300+ LOC or 12+ methods |
| **Low Cohesion** | info | Classes where methods share little instance state (LCOM > 0.7) |

All thresholds are configurable. Smells appear as an interactive overlay in the diagram.

## CLI Options

```
repo_visualizer [PATH] [OPTIONS]

  PATH                   Repository root (default: .)
  -o, --output PATH      Output HTML file (default: architecture_diagram.html)
  --title TEXT            Diagram title (default: directory name)
  --exclude-dirs DIRS    Extra dirs to exclude (comma-separated)
  --no-smells            Disable smell detection
  --no-source            Don't embed source code (smaller output)
  --max-nodes N          Maximum nodes to render (default: 100)
  --json                 Output raw JSON instead of HTML
  -v, --verbose          Show progress
  --version              Show version
```

## MCP Server

repo_visualizer also ships as an MCP tool for use with Claude Code and other MCP-compatible assistants:

```bash
pip install --upgrade "git+https://github.com/BrunoKreiner/repo_visualizer.git#egg=repo-visualizer[mcp]"
repo_visualizer-mcp
```

## License

MIT
