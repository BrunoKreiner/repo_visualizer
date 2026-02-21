from dataclasses import dataclass, field
from pathlib import Path
from typing import Set, Tuple


DEFAULT_EXCLUDED_DIRS: Set[str] = {
    "venv", ".venv", ".git", "__pycache__", ".pytest_cache", "node_modules",
    ".mypy_cache", ".idea", ".vscode", ".tox", ".nox", "dist", "build",
    ".eggs", "htmlcov", ".coverage", ".ruff_cache", "egg-info",
    ".cache", ".hypothesis",
}

DEFAULT_EXCLUDED_PREFIXES: Tuple[str, ...] = ()

DEFAULT_FILE_EXTENSIONS: Set[str] = {
    ".py", ".json", ".csv", ".md", ".txt", ".yaml", ".yml",
    ".toml", ".cfg", ".ini", ".sh", ".bat", ".rst",
}

GROUP_PALETTE = [
    "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899",
    "#EF4444", "#06B6D4", "#14B8A6", "#6366F1", "#D946EF",
    "#84CC16", "#78716C",
]


@dataclass
class SmellThresholds:
    god_class_members: int = 8
    god_class_coupling: int = 4
    hub_ca: int = 4
    hub_ce: int = 4
    unstable_inst: float = 0.8
    unstable_ca: int = 3
    shotgun_ca: int = 5
    feature_envy_cross: int = 3
    high_cc: int = 15
    long_method_loc: int = 80
    long_param: int = 7
    large_class_loc: int = 300
    large_class_methods: int = 12
    low_cohesion_lcom: float = 0.7
    low_cohesion_min_members: int = 3


@dataclass
class VisualizerConfig:
    project_root: Path = field(default_factory=lambda: Path("."))
    output_path: Path = field(default_factory=lambda: Path("architecture_diagram.html"))
    title: str = ""
    excluded_dirs: Set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDED_DIRS))
    excluded_prefixes: Tuple[str, ...] = DEFAULT_EXCLUDED_PREFIXES
    file_extensions: Set[str] = field(default_factory=lambda: set(DEFAULT_FILE_EXTENSIONS))
    max_file_size_kb: int = 200
    smell_thresholds: SmellThresholds = field(default_factory=SmellThresholds)
    embed_source: bool = True
    detect_smells: bool = True
    max_nodes: int = 100
    verbose: bool = False
    output_json: bool = False
