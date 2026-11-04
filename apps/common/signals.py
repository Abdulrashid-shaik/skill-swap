"""SQLite connection tuning.

Applies pragmas on every new SQLite connection:
- WAL journal mode for better read/write concurrency.
- NORMAL synchronous for a reasonable durability/speed balance under WAL.
- foreign_keys ON to enforce FK constraints (defensive; Django sets this too).
- busy_timeout so brief write contention waits instead of erroring immediately.
"""
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def configure_sqlite(sender, connection, **kwargs):
    if connection.vendor != "sqlite":
        return
    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.execute("PRAGMA busy_timeout=5000;")
