# repo-visualizer

Generate interactive architecture diagrams for Python repositories.

## Quick Reference

- **Language**: Python 3.10+
- **Build**: `pip install -e ".[dev]"`
- **Test**: `pytest`
- **Lint**: `ruff check src/`
- **Format**: `ruff format src/`
- **Run**: `repo-visualizer <path> -o output.html`

## Project Structure

```
src/repo_visualizer/
  cli.py        - CLI entry point (argparse)
  config.py     - VisualizerConfig dataclass + constants
  scanner.py    - File scanning and directory traversal
  analyzer.py   - AST-based code analysis, build_code_map
  graph.py      - Dependency graph building
  smells.py     - Architectural smell detection (12 types)
  summarizer.py - Heuristic description generation
  renderer.py   - HTML rendering from template.html
  template.html - Interactive HTML/JS visualization template
```

## Code Style

- Max line length: 120 chars (ruff)
- Target: Python 3.10
- Use type hints on function signatures
- Prefer pathlib.Path over os.path
- No f-strings in print statements (project convention uses string concatenation)

## Testing

- Framework: pytest
- Test directory: `tests/`
- Run specific test: `pytest tests/test_<module>.py -v`
- Coverage: `pytest --cov=repo_visualizer`

## Before Committing

- Run `ruff check src/` and fix any issues
- Run `ruff format --check src/` to verify formatting
- Run `pytest` to verify tests pass
