from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from repo_visualizer.analyzer import analyze_file
from repo_visualizer.config import SmellThresholds


def compute_smells(data: dict, project_root: Path,
                   thresholds: SmellThresholds = None) -> Tuple[List[dict], Dict[str, dict]]:
    if thresholds is None:
        thresholds = SmellThresholds()

    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    node_map = {n['id']: n for n in nodes}

    ca: Dict[str, Set[str]] = defaultdict(set)
    ce: Dict[str, Set[str]] = defaultdict(set)
    same_group_edges: Dict[str, int] = defaultdict(int)
    cross_group_edges: Dict[str, int] = defaultdict(int)

    for e in edges:
        src, tgt = e['from'], e['to']
        if src not in node_map or tgt not in node_map:
            continue
        ca[tgt].add(src)
        ce[src].add(tgt)
        src_group = node_map[src].get('group', '')
        tgt_group = node_map[tgt].get('group', '')
        if src_group == tgt_group:
            same_group_edges[src] += 1
        else:
            cross_group_edges[src] += 1

    instability: Dict[str, float] = {}
    for n in nodes:
        nid = n['id']
        ca_count = len(ca.get(nid, set()))
        ce_count = len(ce.get(nid, set()))
        total = ca_count + ce_count
        instability[nid] = round(ce_count / total, 2) if total > 0 else 0.0

    member_count: Dict[str, int] = {}
    for n in nodes:
        member_count[n['id']] = len(n.get('methods', [])) + len(n.get('functions', []))

    # Cycle detection
    adj: Dict[str, List[str]] = defaultdict(list)
    for e in edges:
        if e.get('type') not in ('data',):
            adj[e['from']].append(e['to'])

    cycle_nodes: Set[str] = set()
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {n['id']: WHITE for n in nodes}

    stack = []
    for start in nodes:
        sid = start['id']
        if color.get(sid) != WHITE:
            continue
        color[sid] = GRAY
        stack.append((sid, iter(adj.get(sid, []))))
        while stack:
            u, children = stack[-1]
            try:
                v = next(children)
                if v not in color:
                    continue
                if color[v] == GRAY:
                    cycle_nodes.add(v)
                    cycle_nodes.add(u)
                elif color[v] == WHITE:
                    color[v] = GRAY
                    stack.append((v, iter(adj.get(v, []))))
            except StopIteration:
                color[u] = BLACK
                stack.pop()

    # AST metrics per node
    ast_metrics: Dict[str, Dict[str, Any]] = {}
    node_metrics: Dict[str, dict] = {}
    t = thresholds

    for n in nodes:
        fp = n.get('file_path', '')
        nid = n['id']
        if not fp or not fp.endswith('.py'):
            node_metrics[nid] = {
                'ca': len(ca.get(nid, set())),
                'ce': len(ce.get(nid, set())),
                'instability': instability.get(nid, 0),
            }
            continue

        full_path = project_root / fp
        if fp not in ast_metrics and full_path.exists():
            ast_metrics[fp] = analyze_file(full_path)

        file_data = ast_metrics.get(fp, {})
        max_cc = 0
        max_loc = 0
        max_params = 0
        node_type = n.get('type', '')
        node_label = n.get('label', nid)

        if node_type in ('class', 'dataclass', 'abc'):
            for cls in file_data.get('classes', []):
                if cls['name'] == node_label or cls['name'] == nid:
                    for m in cls.get('methods', []):
                        max_cc = max(max_cc, m['cc'])
                        max_loc = max(max_loc, m['loc'])
                        max_params = max(max_params, m['params'])
                    node_metrics[nid] = {
                        'ca': len(ca.get(nid, set())),
                        'ce': len(ce.get(nid, set())),
                        'instability': instability.get(nid, 0),
                        'max_cc': max_cc,
                        'class_loc': cls['loc'],
                        'class_methods': cls['method_count'],
                        'lcom': cls['lcom'],
                        'max_params': max_params,
                    }
                    break
            else:
                node_metrics[nid] = {
                    'ca': len(ca.get(nid, set())),
                    'ce': len(ce.get(nid, set())),
                    'instability': instability.get(nid, 0),
                }
        elif node_type == 'function':
            for fn in file_data.get('functions', []):
                if fn['name'] == node_label.rstrip('()') or fn['name'] == nid:
                    node_metrics[nid] = {
                        'ca': len(ca.get(nid, set())),
                        'ce': len(ce.get(nid, set())),
                        'instability': instability.get(nid, 0),
                        'max_cc': fn['cc'],
                        'fn_loc': fn['loc'],
                        'max_params': fn['params'],
                    }
                    break
            else:
                node_metrics[nid] = {
                    'ca': len(ca.get(nid, set())),
                    'ce': len(ce.get(nid, set())),
                    'instability': instability.get(nid, 0),
                }
        elif node_type in ('script', 'module'):
            all_fns = file_data.get('functions', [])
            for fn in all_fns:
                max_cc = max(max_cc, fn['cc'])
                max_loc = max(max_loc, fn['loc'])
                max_params = max(max_params, fn['params'])
            node_metrics[nid] = {
                'ca': len(ca.get(nid, set())),
                'ce': len(ce.get(nid, set())),
                'instability': instability.get(nid, 0),
                'max_cc': max_cc,
                'max_fn_loc': max_loc,
                'max_params': max_params,
                'total_loc': file_data.get('total_loc', 0),
            }
        else:
            node_metrics[nid] = {
                'ca': len(ca.get(nid, set())),
                'ce': len(ce.get(nid, set())),
                'instability': instability.get(nid, 0),
            }

    # Generate smells
    smells: List[dict] = []
    smell_id = 0

    for n in nodes:
        nid = n['id']
        nm = node_metrics.get(nid, {})
        ca_count = nm.get('ca', 0)
        ce_count = nm.get('ce', 0)
        inst = nm.get('instability', 0)
        mcount = member_count.get(nid, 0)
        label = n.get('label', nid)

        if mcount >= t.god_class_members and ce_count >= t.god_class_coupling:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'God Class: {label}',
                'severity': 'warning', 'nodes': [nid],
                'description': f'{label} has {mcount} methods/functions and depends on {ce_count} other modules.',
                'fix': 'Split into smaller, focused classes.',
                'metric': f'Members={mcount}, Ce={ce_count}',
            })
            smell_id += 1

        if ca_count >= t.hub_ca and ce_count >= t.hub_ce:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Hub/Bottleneck: {label}',
                'severity': 'warning', 'nodes': [nid],
                'description': f'{label} is heavily depended on (Ca={ca_count}) and depends on many others (Ce={ce_count}).',
                'fix': 'Introduce interfaces or intermediary modules.',
                'metric': f'Ca={ca_count}, Ce={ce_count}',
            })
            smell_id += 1

        if inst > t.unstable_inst and ca_count >= t.unstable_ca:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Unstable Dependency: {label}',
                'severity': 'warning', 'nodes': [nid],
                'description': f'{label} has instability={inst} but {ca_count} modules depend on it.',
                'fix': 'Stabilize the interface or invert the dependency.',
                'metric': f'Instability={inst}, Ca={ca_count}',
            })
            smell_id += 1

        if ca_count >= t.shotgun_ca:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Shotgun Surgery: {label}',
                'severity': 'info', 'nodes': [nid],
                'description': f'{label} is depended on by {ca_count} modules.',
                'fix': 'Minimize public interface. Use adapter pattern.',
                'metric': f'Ca={ca_count}',
            })
            smell_id += 1

        cge = cross_group_edges.get(nid, 0)
        sge = same_group_edges.get(nid, 0)
        if cge > sge and cge >= t.feature_envy_cross:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Feature Envy: {label}',
                'severity': 'info', 'nodes': [nid],
                'description': f'{label} has {cge} cross-group edges vs {sge} same-group.',
                'fix': 'Consider moving this module closer to the group it interacts with most.',
                'metric': f'Cross={cge}, Same={sge}',
            })
            smell_id += 1

        max_cc = nm.get('max_cc', 0)
        if max_cc >= t.high_cc:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'High Complexity: {label}',
                'severity': 'warning', 'nodes': [nid],
                'description': f'{label} has a function with cyclomatic complexity {max_cc}.',
                'fix': 'Extract conditional branches into helper functions.',
                'metric': f'CC={max_cc}',
            })
            smell_id += 1

        max_fn_loc = max(nm.get('max_fn_loc', 0), nm.get('fn_loc', 0))
        if max_fn_loc > t.long_method_loc:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Long Method: {label}',
                'severity': 'info', 'nodes': [nid],
                'description': f'{label} has a function with {max_fn_loc} lines.',
                'fix': 'Break into smaller functions.',
                'metric': f'Max LOC={max_fn_loc}',
            })
            smell_id += 1

        max_params = nm.get('max_params', 0)
        if max_params > t.long_param:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Long Parameter List: {label}',
                'severity': 'info', 'nodes': [nid],
                'description': f'{label} has a function with {max_params} parameters.',
                'fix': 'Group related parameters into a dataclass.',
                'metric': f'Params={max_params}',
            })
            smell_id += 1

        class_loc = nm.get('class_loc', 0)
        class_methods = nm.get('class_methods', 0)
        if class_loc > t.large_class_loc or class_methods > t.large_class_methods:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Large Class: {label}',
                'severity': 'info', 'nodes': [nid],
                'description': f'{label} has {class_methods} methods and {class_loc} LOC.',
                'fix': 'Extract cohesive groups of methods into separate classes.',
                'metric': f'Methods={class_methods}, LOC={class_loc}',
            })
            smell_id += 1

        lcom = nm.get('lcom', 0)
        if lcom > t.low_cohesion_lcom and mcount >= t.low_cohesion_min_members:
            smells.append({
                'id': f'smell_{smell_id}', 'title': f'Low Cohesion: {label}',
                'severity': 'info', 'nodes': [nid],
                'description': f'{label} has LCOM={lcom}. Methods may not belong together.',
                'fix': 'Split into focused classes where methods share instance state.',
                'metric': f'LCOM={lcom}',
            })
            smell_id += 1

    if cycle_nodes:
        cycle_list = sorted(cycle_nodes)
        labels = ', '.join(node_map[n].get('label', n) for n in cycle_list if n in node_map)
        smells.append({
            'id': f'smell_{smell_id}', 'title': 'Dependency Cycle Detected',
            'severity': 'warning', 'nodes': cycle_list,
            'description': f'Circular dependency involving: {labels}.',
            'fix': 'Break the cycle with dependency inversion.',
            'metric': f'Nodes in cycle: {len(cycle_list)}',
        })

    return smells, node_metrics
