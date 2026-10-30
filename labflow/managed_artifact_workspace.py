"""Managed RF storage; source-code roots and historical IO roots stay distinct."""
from pathlib import Path
from . import development_paths


def artifact_local_root(*, workspace_root=None, backend=None, create=False):
    layout=development_paths.load_layout()
    if workspace_root is None:
        local=layout.output('rf-artifacts/.local')
    else:
        if create:
            raise ValueError('historical_artifact_workspace_is_read_only')
        original=Path(workspace_root)
        if not original.is_absolute():
            raise ValueError('invalid_artifact_workspace')
        local=layout.reference(original/'.local')
    if not local.is_relative_to(layout.root) or local==layout.root:
        raise ValueError('artifact_workspace_outside_managed_root')
    if create:
        if backend is None:
            raise ValueError('artifact_workspace_requires_native_backend')
        from .control_packet_prepare import _Tree
        manager=_Tree(layout.root,backend)
        manager.directory(local,create=True)
    return local
