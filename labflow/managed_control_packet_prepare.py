"""Explicit managed caller for the frozen native packet-copy implementation."""
from .control_packet_prepare import prepare_control_packet as _prepare, _local_path, ControlPacketPrepareError
from .development_paths import reference_path, DevelopmentPathError, load_layout


def prepare_control_packet(source_dir, *, expected_index_sha256, workspace_root, packet_id):
    try:
        source=reference_path(_local_path(source_dir))
        workspace=reference_path(_local_path(workspace_root))
    except DevelopmentPathError:
        source=workspace=None
    if source is None:
        raise ControlPacketPrepareError('packet_prepare_path_invalid') from None
    if not workspace.is_relative_to(load_layout().directory('runs')):
        raise ControlPacketPrepareError('packet_prepare_path_invalid') from None
    return _prepare(source, expected_index_sha256=expected_index_sha256,
        workspace_root=workspace, packet_id=packet_id)
