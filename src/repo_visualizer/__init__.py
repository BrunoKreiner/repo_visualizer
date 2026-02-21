__version__ = "0.1.0"


def generate(config=None, **kwargs):
    from repo_visualizer.cli import generate as _gen
    if config is not None:
        _gen(config)
    else:
        from repo_visualizer.config import VisualizerConfig
        _gen(VisualizerConfig(**kwargs))
