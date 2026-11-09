"""The audit log: one row for every passport view, including the denied ones.

write() never raises. If the log cannot be written the request must still work, but the failure
is logged so someone notices.
"""
import logging

log = logging.getLogger("landstack.audit")

VIEWED = "view_passport"
DENIED = "view_passport_denied"          # a citizen asked for a plot that is not theirs
NOT_FOUND = "view_passport_not_found"    # staff asked for a plot that does not exist

PDF_DOWNLOADED = "download_passport_pdf"
PDF_DENIED = "download_passport_pdf_denied"
PDF_NOT_FOUND = "download_passport_pdf_not_found"

# (shown, denied, not found): the three audit actions of one kind of request.
JSON_VIEW = (VIEWED, DENIED, NOT_FOUND)
PDF_DOWNLOAD = (PDF_DOWNLOADED, PDF_DENIED, PDF_NOT_FOUND)

INSERT_SQL = "INSERT INTO audit_log (username, role, ulpin, action) VALUES (%s, %s, %s, %s)"


def write(conn, user, ulpin, action):
    try:
        with conn.transaction():          # a savepoint: a failure here cannot spoil the request's connection
            conn.execute(INSERT_SQL, (user.username, user.role, ulpin, action))
        conn.commit()                     # the request itself only reads, so this saves just the audit row
    except Exception:  # noqa: BLE001
        log.exception("could not write audit row (user=%s, action=%s, ulpin=%s)", user.username, action, ulpin)
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
