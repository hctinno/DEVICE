"""Test-only paths derived from the managed layout, without creating state."""
from pathlib import Path

from labflow.development_paths import load_layout

REPO = Path(__file__).parents[1]


def fixture_root(name, *, repo=REPO):
    return load_layout(repo).directory('runs', 'migration-20261031/toolchains/' + name)


def workspace_expectations(repo=REPO):
    layout = load_layout(repo)
    workspace = layout.check_workspace(repo)
    for row in layout._document['workspaces']:
        if layout.root / row['path'] == Path(workspace['workspace']):
            return row['role'], row['branch']
    raise ValueError('test_workspace_declaration_missing')
