import ast
import sys
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple


class ImportInfo(NamedTuple):
    module: str
    names: list
    is_from: bool
    level: int


def _cyclomatic_complexity(node: ast.AST) -> int:
    cc = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                              ast.With, ast.Assert, ast.comprehension)):
            cc += 1
        elif isinstance(child, ast.BoolOp):
            cc += len(child.values) - 1
    return cc


def _count_lines(node: ast.AST) -> int:
    if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
        return node.end_lineno - node.lineno + 1
    return 0


def _param_count(func_node: ast.AST) -> int:
    if not isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    args = func_node.args
    count = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
    if args.vararg:
        count += 1
    if args.kwarg:
        count += 1
    for a in args.args[:1]:
        if a.arg in ('self', 'cls'):
            count -= 1
    return count


def _compute_lcom(class_node: ast.ClassDef) -> float:
    methods = [n for n in class_node.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name != '__init__']
    if len(methods) < 2:
        return 0.0
    method_attrs: List[Set[str]] = []
    for m in methods:
        attrs = set()
        for node in ast.walk(m):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == 'self':
                    attrs.add(node.attr)
        method_attrs.append(attrs)
    pairs_total = 0
    pairs_disjoint = 0
    for i in range(len(method_attrs)):
        for j in range(i + 1, len(method_attrs)):
            pairs_total += 1
            if not method_attrs[i] & method_attrs[j]:
                pairs_disjoint += 1
    return pairs_disjoint / pairs_total if pairs_total > 0 else 0.0


def reconstruct_signature(func_node) -> str:
    try:
        args_str = ast.unparse(func_node.args)
        sig = f"{func_node.name}({args_str})"
        if func_node.returns:
            sig += f" -> {ast.unparse(func_node.returns)}"
        return sig
    except Exception:
        return f"{func_node.name}(...)"


def analyze_file(file_path: Path) -> Dict[str, Any]:
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(file_path))
    except Exception:
        return {}

    result: Dict[str, Any] = {
        'functions': [],
        'classes': [],
        'total_loc': len(source.splitlines()),
    }

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result['functions'].append({
                'name': node.name,
                'sig': reconstruct_signature(node),
                'cc': _cyclomatic_complexity(node),
                'loc': _count_lines(node),
                'params': _param_count(node),
                'lineno': node.lineno,
                'end_lineno': getattr(node, 'end_lineno', node.lineno),
            })
        elif isinstance(node, ast.ClassDef):
            class_methods = []
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_methods.append({
                        'name': child.name,
                        'sig': reconstruct_signature(child),
                        'cc': _cyclomatic_complexity(child),
                        'loc': _count_lines(child),
                        'params': _param_count(child),
                        'lineno': child.lineno,
                        'end_lineno': getattr(child, 'end_lineno', child.lineno),
                    })
            node_type = 'class'
            for dec in node.decorator_list:
                dec_str = ast.unparse(dec) if hasattr(ast, 'unparse') else ''
                if 'dataclass' in dec_str:
                    node_type = 'dataclass'
                    break
            for base in node.bases:
                base_str = ast.unparse(base) if hasattr(ast, 'unparse') else ''
                if 'ABC' in base_str or 'Abstract' in base_str:
                    node_type = 'abc'
                    break
            fields = []
            for child in node.body:
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    fields.append(child.target.id)
                elif isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            fields.append(target.id)
            result['classes'].append({
                'name': node.name,
                'type': node_type,
                'methods': class_methods,
                'fields': fields,
                'loc': _count_lines(node),
                'method_count': len(class_methods),
                'lcom': round(_compute_lcom(node), 2),
                'lineno': node.lineno,
                'end_lineno': getattr(node, 'end_lineno', node.lineno),
                'bases': [ast.unparse(b) if hasattr(ast, 'unparse') else '' for b in node.bases],
            })

    # Content classification signals for panel auto-detection
    n_module_constants = 0
    n_dataclass_or_typedef = 0
    for child in ast.iter_child_nodes(tree):
        if isinstance(child, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            n_module_constants += 1
        elif isinstance(child, ast.ClassDef):
            _up = ast.unparse if hasattr(ast, 'unparse') else (lambda x: '')
            is_dc = any('dataclass' in _up(d) for d in child.decorator_list)
            is_td = any('TypedDict' in _up(b) or 'NamedTuple' in _up(b)
                        for b in child.bases)
            if is_dc or is_td:
                n_dataclass_or_typedef += 1
    result['module_constants'] = n_module_constants
    result['dataclass_or_typedef_count'] = n_dataclass_or_typedef

    return result


def extract_imports(file_path: Path) -> List[ImportInfo]:
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(file_path))
    except Exception:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(ImportInfo(
                    module=alias.name,
                    names=[alias.asname or alias.name.split('.')[-1]],
                    is_from=False,
                    level=0,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = [alias.name for alias in node.names]
            imports.append(ImportInfo(
                module=module,
                names=names,
                is_from=True,
                level=node.level or 0,
            ))
    return imports


def detect_entry_point(file_path: Path) -> bool:
    try:
        source = file_path.read_text(encoding='utf-8')
        tree = ast.parse(source, filename=str(file_path))
    except Exception:
        return False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.If):
            test = node.test
            if (isinstance(test, ast.Compare) and
                isinstance(test.left, ast.Name) and
                test.left.id == '__name__' and
                len(test.comparators) == 1 and
                isinstance(test.comparators[0], ast.Constant) and
                test.comparators[0].value == '__main__'):
                return True
    return False


def resolve_import_to_file(module_str: str, project_root: Path) -> Optional[Path]:
    parts = module_str.split('.')
    pkg_path = project_root / Path(*parts) / '__init__.py'
    if pkg_path.exists():
        return pkg_path
    if len(parts) > 1:
        mod_path = project_root / Path(*parts[:-1]) / f'{parts[-1]}.py'
    else:
        mod_path = project_root / f'{parts[0]}.py'
    if mod_path.exists():
        return mod_path
    return None


def get_stdlib_modules() -> Set[str]:
    if hasattr(sys, 'stdlib_module_names'):
        return sys.stdlib_module_names
    return {
        'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections',
        'contextlib', 'copy', 'csv', 'dataclasses', 'datetime', 'decimal',
        'enum', 'functools', 'hashlib', 'importlib', 'inspect', 'io',
        'itertools', 'json', 'logging', 'math', 'operator', 'os',
        'pathlib', 'pickle', 'pprint', 'random', 're', 'shutil',
        'signal', 'socket', 'sqlite3', 'string', 'struct', 'subprocess',
        'sys', 'tempfile', 'textwrap', 'threading', 'time', 'traceback',
        'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'xml',
    }


def build_code_map(project_root: Path, data: dict) -> Dict[str, dict]:
    seen: Set[str] = set()
    result: Dict[str, dict] = {}
    for n in data.get('nodes', []):
        fp = n.get('file_path', '')
        if not fp or fp in seen:
            continue
        seen.add(fp)
        full = project_root / fp
        if not full.exists():
            continue
        analysis = analyze_file(full)
        if not analysis:
            continue
        file_entry: Dict[str, Any] = {
            'classes': [],
            'functions': [],
            'total_loc': analysis.get('total_loc', 0),
        }
        for cls in analysis.get('classes', []):
            methods = []
            for m in cls.get('methods', []):
                methods.append({
                    'name': m['name'],
                    'sig': m.get('sig', ''),
                    'lineno': m.get('lineno', 0),
                    'end_lineno': m.get('end_lineno', 0),
                    'cc': m.get('cc', 0),
                    'params': m.get('params', 0),
                    'loc': m.get('loc', 0),
                })
            file_entry['classes'].append({
                'name': cls['name'],
                'lineno': cls.get('lineno', 0),
                'end_lineno': cls.get('end_lineno', 0),
                'loc': cls.get('loc', 0),
                'lcom': cls.get('lcom', 0),
                'method_count': cls.get('method_count', 0),
                'methods': methods,
            })
        for fn in analysis.get('functions', []):
            file_entry['functions'].append({
                'name': fn['name'],
                'sig': fn.get('sig', ''),
                'lineno': fn.get('lineno', 0),
                'end_lineno': fn.get('end_lineno', 0),
                'cc': fn.get('cc', 0),
                'params': fn.get('params', 0),
                'loc': fn.get('loc', 0),
            })
        result[fp] = file_entry
    return result
