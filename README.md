# repo-visualizer

Generate interactive architecture diagrams for any Python repository with a single command.

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)

## Install

```bash
pip install repo-visualizer
```

## Usage

```bash
# Generate diagram for current directory
repo-visualizer .

# Specify output and title
repo-visualizer /path/to/project -o diagram.html --title "My Project"

# With LLM-generated descriptions
repo-visualizer . --llm openai          # requires OPENAI_API_KEY
repo-visualizer . --llm claude           # requires ANTHROPIC_API_KEY
repo-visualizer . --llm claude-code      # uses Claude Code CLI

# Output raw JSON (for custom processing)
repo-visualizer . --json -o data.json

# Verbose mode
repo-visualizer . -v
```

## What You Get

An interactive single-file HTML diagram with:

- **Node cards** for every class, module, and script -- with methods, fields, and type signatures
- **Dependency edges** auto-detected from import analysis
- **Tiered layout** via topological sort (entry points at top)
- **Directory-based grouping** with color coding
- **File explorer** with source code viewer and syntax highlighting
- **Code map** with clickable cross-references between classes
- **Architectural smell detection** (see below)

## Smell Detection

repo-visualizer detects 12 architectural smells:

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
repo-visualizer [PATH] [OPTIONS]

  PATH                   Repository root (default: .)
  -o, --output PATH      Output HTML file (default: architecture_diagram.html)
  --title TEXT            Diagram title (default: directory name)
  --exclude-dirs DIRS    Extra dirs to exclude (comma-separated)
  --llm PROVIDER         none|openai|claude|gemini|claude-code (default: none)
  --llm-model MODEL      Specific model name
  --no-smells            Disable smell detection
  --no-source            Don't embed source code (smaller output)
  --max-nodes N          Maximum nodes to render (default: 100)
  --json                 Output raw JSON instead of HTML
  -v, --verbose          Show progress
  --version              Show version
```

## LLM Descriptions

By default, node descriptions use docstrings or structural heuristics. For richer summaries:

```bash
# Via API (install optional deps)
pip install repo-visualizer[openai]    # or [claude] or [gemini]
repo-visualizer . --llm openai

# Via Claude Code CLI (no extra deps)
repo-visualizer . --llm claude-code
```

Descriptions are cached to `.repo-visualizer-cache/` to avoid repeated API calls.

## License

MIT
