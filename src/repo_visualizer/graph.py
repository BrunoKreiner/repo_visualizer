import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from repo_visualizer.analyzer import (
    analyze_file, extract_imports, detect_entry_point,
    resolve_import_to_file, get_stdlib_modules,
)
from repo_visualizer.config import VisualizerConfig, GROUP_PALETTE

PANEL_DIR_NAMES = {
    'config', 'configs', 'configuration', 'settings',
    'data', 'fixtures', 'static', 'assets', 'templates', 'resources',
}
TEST_DIR_NAMES = {'tests', 'test', 'testing', 'spec', 'specs'}
UTIL_DIR_NAMES = {'utils', 'utilities', 'helpers', 'common', 'shared', 'lib'}


def build_architecture_data(config: VisualizerConfig, py_files: List[Path]) -> dict:
    project_root = config.project_root.resolve()

    file_analyses: Dict[str, dict] = {}
    file_imports: Dict[str, list] = {}
    entry_points: Set[str] = set()

    for fp in py_files:
        rel = str(fp.relative_to(project_root)).replace('\\', '/')
        analysis = analyze_file(fp)
        if analysis:
            file_analyses[rel] = analysis
        file_imports[rel] = extract_imports(fp)
        if detect_entry_point(fp):
            entry_points.add(rel)

    groups = _create_groups(py_files, project_root)
    group_ids = {g['id'] for g in groups}
    nodes = _create_nodes(file_analyses, py_files, project_root, group_ids, config)

    if len(nodes) > config.max_nodes:
        nodes = nodes[:config.max_nodes]

    edges = _create_edges(file_imports, nodes, project_root)
    tier_map = _assign_tiers(nodes, edges, entry_points)
    for node in nodes:
        node['tier'] = tier_map.get(node['id'], 0)

    max_tier = max((n['tier'] for n in nodes), default=0)
    tier_labels = []
    for i in range(max_tier + 1):
        if i == 0:
            tier_labels.append({'label': f'Tier {i} -- Entry Points'})
        else:
            tier_labels.append({'label': f'Tier {i}'})

    return {
        'nodes': nodes,
        'edges': edges,
        'groups': groups,
        'tiers': tier_labels,
    }


def _create_groups(py_files: List[Path], project_root: Path) -> list:
    root = project_root.resolve()
    top_dirs: Set[str] = set()
    has_root_files = False

    for fp in py_files:
        rel = fp.relative_to(root)
        parts = rel.parts
        if len(parts) == 1:
            has_root_files = True
        elif len(parts) > 1:
            top_dirs.add(parts[0])

    groups = []
    color_idx = 0

    if has_root_files:
        groups.append({
            'id': '_root',
            'label': 'Root',
            'color': GROUP_PALETTE[color_idx % len(GROUP_PALETTE)],
            'panel': False,
        })
        color_idx += 1

    for d in sorted(top_dirs):
        dl = d.lower()
        is_panel = dl in PANEL_DIR_NAMES or dl in UTIL_DIR_NAMES
        groups.append({
            'id': d,
            'label': d.replace('_', ' ').title(),
            'color': GROUP_PALETTE[color_idx % len(GROUP_PALETTE)],
            'panel': is_panel,
        })
        color_idx += 1

    return groups


def _create_nodes(file_analyses: Dict[str, dict], py_files: List[Path],
                  project_root: Path, group_ids: Set[str],
                  config: VisualizerConfig) -> list:
    root = project_root.resolve()
    nodes = []
    node_id_set: Set[str] = set()

    for fp in py_files:
        rel = str(fp.relative_to(root)).replace('\\', '/')
        analysis = file_analyses.get(rel)
        if not analysis:
            continue

        path_parts = Path(rel).parts
        group_id = path_parts[0] if len(path_parts) > 1 and path_parts[0] in group_ids else '_root'

        classes = analysis.get('classes', [])
        functions = analysis.get('functions', [])

        if classes:
            for cls in classes:
                node_id = cls['name']
                orig = node_id
                suffix = 1
                while node_id in node_id_set:
                    node_id = f"{orig}_{suffix}"
                    suffix += 1
                node_id_set.add(node_id)

                methods = [{'name': m['name'], 'sig': m.get('sig', '')}
                           for m in cls.get('methods', [])]
                fields = cls.get('fields', [])

                nodes.append({
                    'id': node_id,
                    'label': cls['name'],
                    'type': cls.get('type', 'class'),
                    'group': group_id,
                    'file_path': rel,
                    'description': '',
                    'methods': methods,
                    'fields': fields,
                    'tier': 0,
                })

        if functions and not classes:
            module_name = Path(rel).stem
            node_id = module_name
            orig = node_id
            suffix = 1
            while node_id in node_id_set:
                node_id = f"{orig}_{suffix}"
                suffix += 1
            node_id_set.add(node_id)

            fn_list = [{'name': f['name'], 'sig': f.get('sig', '')}
                       for f in functions]

            is_entry = detect_entry_point(root / rel)
            node_type = 'script' if is_entry else 'module'

            nodes.append({
                'id': node_id,
                'label': module_name,
                'type': node_type,
                'group': group_id,
                'file_path': rel,
                'description': '',
                'functions': fn_list,
                'tier': 0,
            })

    return nodes


def _create_edges(file_imports: Dict[str, list], nodes: list,
                  project_root: Path) -> list:
    root = project_root.resolve()
    stdlib = get_stdlib_modules()

    file_to_node_ids: Dict[str, List[str]] = defaultdict(list)
    for n in nodes:
        fp = n.get('file_path', '')
        if fp:
            file_to_node_ids[fp].append(n['id'])

    # Build module-name to file-path index for fuzzy resolution
    # e.g. "repo_visualizer.analyzer" -> "src/repo_visualizer/analyzer.py"
    all_py_files = list(file_to_node_ids.keys())
    module_to_file: Dict[str, str] = {}
    for fp in all_py_files:
        if not fp.endswith('.py'):
            continue
        # Convert file path to possible module paths
        # e.g. "src/repo_visualizer/analyzer.py" -> ["src.repo_visualizer.analyzer", "repo_visualizer.analyzer", "analyzer"]
        stem = fp[:-3].replace('/', '.')  # remove .py
        parts = stem.split('.')
        for i in range(len(parts)):
            candidate = '.'.join(parts[i:])
            if candidate and candidate not in module_to_file:
                module_to_file[candidate] = fp

    edges = []
    seen_edges: Set[Tuple[str, str]] = set()
    edge_id = 0

    for source_file, imports in file_imports.items():
        source_node_ids = file_to_node_ids.get(source_file, [])
        if not source_node_ids:
            continue

        for imp in imports:
            top_module = imp.module.split('.')[0] if imp.module else ''
            if top_module in stdlib:
                continue

            target_rel = None

            # Strategy 1: Direct file resolution
            if imp.level == 0 and imp.module:
                target_file = resolve_import_to_file(imp.module, root)
                if target_file is not None:
                    try:
                        target_rel = str(target_file.relative_to(root)).replace('\\', '/')
                    except ValueError:
                        pass

            # Strategy 2: Fuzzy module name matching
            if target_rel is None and imp.module:
                target_rel = module_to_file.get(imp.module)
                # Also try with __init__ stripped
                if target_rel is None:
                    parts = imp.module.split('.')
                    init_path = '/'.join(parts) + '/__init__.py'
                    if init_path in file_to_node_ids:
                        target_rel = init_path

            # Strategy 3: For "from X import Y", Y might be a module
            if target_rel is None and imp.is_from and imp.names:
                for name in imp.names:
                    full = f"{imp.module}.{name}" if imp.module else name
                    target_rel = module_to_file.get(full)
                    if target_rel:
                        break

            if target_rel is None:
                continue

            target_node_ids = file_to_node_ids.get(target_rel, [])

            for src_id in source_node_ids:
                for tgt_id in target_node_ids:
                    if src_id == tgt_id:
                        continue
                    pair = (src_id, tgt_id)
                    if pair in seen_edges:
                        continue
                    seen_edges.add(pair)
                    edges.append({
                        'id': f'e{edge_id}',
                        'from': src_id,
                        'to': tgt_id,
                        'type': 'dependency',
                    })
                    edge_id += 1

    return edges


def _assign_tiers(nodes: list, edges: list,
                  entry_points: Set[str]) -> Dict[str, int]:
    file_to_ids: Dict[str, List[str]] = defaultdict(list)
    for n in nodes:
        fp = n.get('file_path', '')
        if fp:
            file_to_ids[fp].append(n['id'])

    adj: Dict[str, Set[str]] = defaultdict(set)
    node_ids = {n['id'] for n in nodes}
    for e in edges:
        if e['from'] in node_ids and e['to'] in node_ids:
            adj[e['from']].add(e['to'])

    entry_node_ids: Set[str] = set()
    for ep in entry_points:
        entry_node_ids.update(file_to_ids.get(ep, []))

    has_incoming = set()
    for e in edges:
        has_incoming.add(e['to'])
    for n in nodes:
        if n['id'] not in has_incoming:
            entry_node_ids.add(n['id'])

    tier_map: Dict[str, int] = {}
    queue = deque()
    for nid in entry_node_ids:
        tier_map[nid] = 0
        queue.append(nid)

    while queue:
        current = queue.popleft()
        current_tier = tier_map[current]
        for neighbor in adj.get(current, set()):
            new_tier = current_tier + 1
            if neighbor not in tier_map or tier_map[neighbor] < new_tier:
                tier_map[neighbor] = min(new_tier, 7)
                queue.append(neighbor)

    for n in nodes:
        if n['id'] not in tier_map:
            tier_map[n['id']] = 0

    return tier_map
