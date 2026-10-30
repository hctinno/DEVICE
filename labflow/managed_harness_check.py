"""Managed caller for the frozen virtual harness; never changes engine bytes."""
from pathlib import Path
import sys
import uuid
from .development_paths import check_development_workspace, load_layout


def main(argv=None):
    arguments=list(sys.argv[1:] if argv is None else argv)
    from .virtual_fleet.harness_check import main as frozen_main
    if arguments==['--help']:
        return frozen_main(arguments)
    check_development_workspace(Path.cwd())
    if not any(value=='--output' or value.startswith('--output=') for value in arguments):
        arguments=['--output',str(load_layout().output('fleet-harness-check/'+uuid.uuid4().hex)),*arguments]
    return frozen_main(arguments)


if __name__=='__main__':raise SystemExit(main())
