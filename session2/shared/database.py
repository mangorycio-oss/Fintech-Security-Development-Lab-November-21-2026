import sqlite3
from contextlib import contextmanager


@contextmanager
def sqlite_transaction(database):
    db = sqlite3.connect(database)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
