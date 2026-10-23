"""Read the existing intake contract without initializing or migrating a store."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from .active_intake import intake_status
from .intake_jobs import notifications


class ReadModelError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _SnapshotStore:
    """Only the connection interface required by the two service readers."""
    def __init__(self, connection):
        self._connection = connection

    @contextmanager
    def connection(self):
        yield self._connection


class IntakeReadModel:
    def __init__(self, workspace):
        self.database = Path(workspace).resolve() / 'lab.sqlite3'

    def snapshot(self, intake_id=None):
        if not self.database.is_file():
            raise ReadModelError('store_missing')
        con = None
        try:
            con = sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=2)
            con.row_factory = sqlite3.Row
            con.execute('PRAGMA query_only=ON')
            con.execute('BEGIN')
            store = _SnapshotStore(con)
            records = intake_status(store, intake_id)
            notices = notifications(store)
            result = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat()}
            if intake_id is None:
                result['intakes'] = records
            else:
                result['intake'] = records
                notices = [n for n in notices if n['intake_id'] == intake_id]
            result['notifications'] = notices
            return result
        except sqlite3.Error as exc:
            raise ReadModelError('store_unavailable') from exc
        except ValueError as exc:
            # Service readers distinguish a missing ID before decoding its state.
            code = 'intake_not_found' if str(exc) == 'Unknown intake' else 'state_invalid'
            raise ReadModelError(code) from exc
        except (TypeError, KeyError, IndexError) as exc:
            raise ReadModelError('state_invalid') from exc
        finally:
            if con is not None:
                con.close()
