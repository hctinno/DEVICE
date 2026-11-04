"""Machine-readable diagnostics that retain original exceptions and group members."""
def error_details(exc):
    from dgm_lab.transport import CommunicationError
    from dgm_lab.core import InstrumentError
    from dgm_rf.core import RFError, CleanupError
    from .catalog import ProfileError
    from .session import SessionError
    if isinstance(exc, BaseExceptionGroup):
        code = "MULTIPLE_FAILURES"
    elif isinstance(exc, (KeyboardInterrupt, InterruptedError)):
        code = "CANCELLED"
    elif isinstance(exc, CleanupError):
        code = "CLEANUP_UNCONFIRMED"
    elif isinstance(exc, (CommunicationError, TimeoutError, ConnectionError)):
        code = "COMMUNICATION"
    elif isinstance(exc, ProfileError):
        code = "PROFILE"
    elif isinstance(exc, SessionError):
        code = "SESSION"
    elif isinstance(exc, (InstrumentError, RFError)):
        code = "DEVICE_RESPONSE"
    elif isinstance(exc, (TypeError, ValueError, KeyError)):
        code = "ARGUMENT"
    elif isinstance(exc, FileExistsError):
        code = "OUTPUT_EXISTS"
    else:
        code = "APPLICATION"
    record = {"code": code, "type": type(exc).__name__, "message": str(exc), "automatic_retry": False}
    if isinstance(exc, BaseExceptionGroup):
        record["errors"] = [error_details(child) for child in exc.exceptions]
    return record
