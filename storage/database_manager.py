import sqlite3
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from storage.file_manager import FileManager


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exception_type, exception, traceback):
        try:
            return super().__exit__(exception_type, exception, traceback)
        finally:
            self.close()


class DatabaseManager:
    INCIDENT_FIELDS = FileManager.FIELDNAMES
    USER_FIELDS = (
        "id", "username", "email", "role", "status", "agency_name",
        "created_at",
    )

    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(
            self.database_path,
            timeout=30,
            factory=ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('admin', 'agency', 'road_user')),
                    status TEXT NOT NULL CHECK (status IN ('active', 'pending')),
                    agency_name TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS incidents (
                    id INTEGER PRIMARY KEY,
                    time TEXT NOT NULL DEFAULT '',
                    base TEXT NOT NULL DEFAULT '',
                    county TEXT NOT NULL DEFAULT '',
                    road TEXT NOT NULL DEFAULT '',
                    place TEXT NOT NULL DEFAULT '',
                    accident_info TEXT NOT NULL DEFAULT '',
                    cause_code TEXT NOT NULL DEFAULT '',
                    victim TEXT NOT NULL DEFAULT '',
                    fatalities TEXT NOT NULL DEFAULT '0',
                    date TEXT NOT NULL DEFAULT '',
                    latitude TEXT NOT NULL DEFAULT '',
                    longitude TEXT NOT NULL DEFAULT '',
                    reporter_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS incidents_cause_code_idx
                    ON incidents(cause_code);
                CREATE INDEX IF NOT EXISTS incidents_reporter_id_idx
                    ON incidents(reporter_id);
                CREATE TABLE IF NOT EXISTS app_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

    def migrate_csv(self, csv_path):
        """Import a legacy CSV once, retaining the first exact duplicate only."""
        csv_path = Path(csv_path)
        if not csv_path.is_file():
            return {"imported": 0, "duplicates_removed": 0}
        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM app_metadata WHERE key = 'csv_import_complete'"
            ).fetchone():
                return {"imported": 0, "duplicates_removed": 0}
        rows = FileManager(csv_path).load_incidents()
        unique_rows = []
        seen = set()
        for row in rows:
            key = tuple(row.get(field, "") for field in self.INCIDENT_FIELDS)
            if key in seen:
                continue
            seen.add(key)
            unique_rows.append(row)

        with self._connect() as connection:
            if connection.execute(
                "SELECT 1 FROM app_metadata WHERE key = 'csv_import_complete'"
            ).fetchone():
                return {"imported": 0, "duplicates_removed": 0}
            if connection.execute("SELECT 1 FROM incidents LIMIT 1").fetchone():
                connection.execute(
                    "INSERT OR REPLACE INTO app_metadata(key, value) "
                    "VALUES ('csv_import_complete', 'existing database')"
                )
                return {"imported": 0, "duplicates_removed": 0}
            placeholders = ", ".join("?" for _ in self.INCIDENT_FIELDS)
            columns = ", ".join(self.INCIDENT_FIELDS)
            connection.executemany(
                f"INSERT INTO incidents ({columns}) VALUES ({placeholders})",
                [
                    tuple(row.get(field, "") for field in self.INCIDENT_FIELDS)
                    for row in unique_rows
                ],
            )
            connection.execute(
                "INSERT INTO app_metadata(key, value) VALUES "
                "('csv_import_complete', 'yes')"
            )
        return {
            "imported": len(unique_rows),
            "duplicates_removed": len(rows) - len(unique_rows),
        }

    def ensure_admin(self, username, email, password):
        if not password:
            return
        with self._connect() as connection:
            connection.execute(
                "UPDATE users SET role = 'road_user', status = 'active' "
                "WHERE role = 'admin' AND username != ? COLLATE NOCASE",
                (username,),
            )
            existing = connection.execute(
                "SELECT id FROM users WHERE username = ? COLLATE NOCASE "
                "OR email = ? COLLATE NOCASE LIMIT 1",
                (username, email),
            ).fetchone()
            password_hash = generate_password_hash(password)
            if existing:
                connection.execute(
                    "UPDATE users SET username = ?, email = ?, password_hash = ?, "
                    "role = 'admin', status = 'active' WHERE id = ?",
                    (username, email, password_hash, existing["id"]),
                )
            else:
                connection.execute(
                    "INSERT INTO users (username, email, password_hash, role, status) "
                    "VALUES (?, ?, ?, 'admin', 'active')",
                    (username, email, password_hash),
                )

    def can_bootstrap_admin(self):
        with self._connect() as connection:
            return connection.execute(
                "SELECT 1 FROM users LIMIT 1"
            ).fetchone() is None

    def create_first_admin(self, username, email, password):
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM users LIMIT 1"
            ).fetchone():
                return None
            cursor = connection.execute(
                "INSERT INTO users "
                "(username, email, password_hash, role, status) "
                "VALUES (?, ?, ?, 'admin', 'active')",
                (
                    username.strip(),
                    email.strip().lower(),
                    generate_password_hash(password),
                ),
            )
            return cursor.lastrowid

    def create_user(self, username, email, password, role, agency_name=""):
        status = "pending" if role == "agency" else "active"
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO users "
                "(username, email, password_hash, role, status, agency_name) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    username.strip(), email.strip().lower(),
                    generate_password_hash(password), role, status,
                    agency_name.strip(),
                ),
            )
            return cursor.lastrowid

    def get_user(self, user_id):
        if not user_id:
            return None
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, username, email, role, status, agency_name, created_at "
                "FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def authenticate(self, username_or_email, password):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ? COLLATE NOCASE "
                "OR email = ? COLLATE NOCASE LIMIT 1",
                (username_or_email.strip(), username_or_email.strip()),
            ).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return None
        user = dict(row)
        user.pop("password_hash", None)
        return user

    def pending_agencies(self):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, username, email, agency_name, created_at "
                "FROM users WHERE role = 'agency' AND status = 'pending' "
                "ORDER BY created_at"
            ).fetchall()
        return [dict(row) for row in rows]

    def approve_agency(self, user_id):
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE users SET status = 'active' "
                "WHERE id = ? AND role = 'agency' AND status = 'pending'",
                (user_id,),
            )
            return cursor.rowcount == 1

    def count_incidents(self):
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]

    def load_incidents(self, owner_user_id=None, agency_name=None):
        with self._connect() as connection:
            if agency_name:
                rows = connection.execute(
                    "SELECT * FROM incidents WHERE reporter_id IS NULL OR "
                    "reporter_id IN (SELECT id FROM users WHERE role = 'agency' "
                    "AND status = 'active' AND agency_name = ? COLLATE NOCASE) "
                    "ORDER BY id",
                    (agency_name,),
                ).fetchall()
            elif owner_user_id is None:
                rows = connection.execute(
                    "SELECT * FROM incidents ORDER BY id"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM incidents WHERE reporter_id = ? ORDER BY id",
                    (owner_user_id,),
                ).fetchall()
        result = []
        for row in rows:
            record = {field: row[field] for field in self.INCIDENT_FIELDS}
            record["_record_id"] = row["id"]
            record["_reporter_id"] = row["reporter_id"]
            result.append(record)
        return result

    def save_incidents(self, incidents):
        placeholders = ", ".join("?" for _ in self.INCIDENT_FIELDS)
        columns = ", ".join(self.INCIDENT_FIELDS)
        with self._connect() as connection:
            connection.execute("DELETE FROM incidents")
            connection.executemany(
                f"INSERT INTO incidents ({columns}) VALUES ({placeholders})",
                [
                    tuple(row.get(field, "") for field in self.INCIDENT_FIELDS)
                    for row in incidents
                ],
            )

    def add_incident(
        self, time, date, county, road, base, place, accident_info,
        fatalities, victim, cause_code, latitude="", longitude="",
        reporter_id=None,
    ):
        incident = {
            "time": time, "date": date, "county": county, "road": road,
            "base": base, "place": place, "accident_info": accident_info,
            "fatalities": fatalities, "victim": victim, "cause_code": cause_code,
            "latitude": latitude, "longitude": longitude,
        }
        with self._connect() as connection:
            cursor = connection.execute(
                f"INSERT INTO incidents ({', '.join(self.INCIDENT_FIELDS)}, reporter_id) "
                f"VALUES ({', '.join('?' for _ in self.INCIDENT_FIELDS)}, ?)",
                tuple(incident[field] for field in self.INCIDENT_FIELDS)
                + (reporter_id,),
            )
            return cursor.lastrowid

    def search_incident(
        self, cause_code, owner_user_id=None, agency_name=None,
    ):
        with self._connect() as connection:
            if agency_name:
                row = connection.execute(
                    "SELECT * FROM incidents WHERE cause_code = ? AND "
                    "(reporter_id IS NULL OR reporter_id IN "
                    "(SELECT id FROM users WHERE role = 'agency' AND status = 'active' "
                    "AND agency_name = ? COLLATE NOCASE)) ORDER BY id LIMIT 1",
                    (str(cause_code), agency_name),
                ).fetchone()
            elif owner_user_id is None:
                row = connection.execute(
                    "SELECT * FROM incidents WHERE cause_code = ? "
                    "ORDER BY id LIMIT 1",
                    (str(cause_code),),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM incidents WHERE cause_code = ? AND reporter_id = ? "
                    "ORDER BY id LIMIT 1",
                    (str(cause_code), owner_user_id),
                ).fetchone()
        if not row:
            return None
        return {
            **{field: row[field] for field in self.INCIDENT_FIELDS},
            "_record_id": row["id"],
            "_reporter_id": row["reporter_id"],
        }

    def update_incident(
        self, cause_code, updates, owner_user_id=None, agency_name=None,
    ):
        allowed = set(self.INCIDENT_FIELDS)
        changes = {
            field: str(value) for field, value in updates.items()
            if field in allowed
        }
        if not changes:
            return False
        assignments = ", ".join(f"{field} = ?" for field in changes)
        parameters = list(changes.values()) + [str(cause_code)]
        owner_clause = ""
        if agency_name:
            owner_clause = (
                " AND (reporter_id IS NULL OR reporter_id IN "
                "(SELECT id FROM users WHERE role = 'agency' "
                "AND status = 'active' AND agency_name = ? COLLATE NOCASE))"
            )
            parameters.append(agency_name)
        elif owner_user_id is not None:
            owner_clause = " AND reporter_id = ?"
            parameters.append(owner_user_id)
        with self._connect() as connection:
            cursor = connection.execute(
                f"UPDATE incidents SET {assignments} WHERE id = "
                f"(SELECT id FROM incidents WHERE cause_code = ?{owner_clause} "
                "ORDER BY id LIMIT 1)",
                parameters,
            )
            return cursor.rowcount == 1

    def delete_incident(
        self, cause_code, owner_user_id=None, agency_name=None,
    ):
        parameters = [str(cause_code)]
        owner_clause = ""
        if agency_name:
            owner_clause = (
                " AND (reporter_id IS NULL OR reporter_id IN "
                "(SELECT id FROM users WHERE role = 'agency' "
                "AND status = 'active' AND agency_name = ? COLLATE NOCASE))"
            )
            parameters.append(agency_name)
        elif owner_user_id is not None:
            owner_clause = " AND reporter_id = ?"
            parameters.append(owner_user_id)
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM incidents WHERE id = "
                f"(SELECT id FROM incidents WHERE cause_code = ?{owner_clause} "
                "ORDER BY id LIMIT 1)",
                parameters,
            )
            return cursor.rowcount == 1

    def deduplicate_incidents(self):
        incidents = self.load_incidents()
        seen = set()
        duplicate_ids = []
        for incident in incidents:
            key = tuple(incident.get(field, "") for field in self.INCIDENT_FIELDS)
            key += (incident.get("_reporter_id"),)
            if key in seen:
                duplicate_ids.append(incident["_record_id"])
                continue
            seen.add(key)
        if duplicate_ids:
            with self._connect() as connection:
                connection.executemany(
                    "DELETE FROM incidents WHERE id = ?",
                    [(record_id,) for record_id in duplicate_ids],
                )
        return self.load_incidents(), len(duplicate_ids)

    def backup(self, destination):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            target = sqlite3.connect(destination)
            try:
                connection.backup(target)
            finally:
                target.close()
        return destination
