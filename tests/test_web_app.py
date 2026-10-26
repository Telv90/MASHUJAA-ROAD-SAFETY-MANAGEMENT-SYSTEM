import csv
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from Services.ai_safety_analysis import build_analysis_evidence
from storage.database_manager import DatabaseManager


class RoadSafetyWebAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.csv_path = self.temp_path / "incidents.csv"
        self.database_path = self.temp_path / "tusalama.sqlite3"
        with self.csv_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "time", "base", "county", "road", "place",
                    "accident_info", "cause_code", "victim",
                    "fatalities", "date",
                ],
            )
            writer.writeheader()
            writer.writerow({
                "time": "0630",
                "base": "KITUI",
                "county": "MAKUENI",
                "road": "KITUI-ITHOKWE",
                "place": "KITUI SCHOOL",
                "accident_info": "HEAD ON COLLISION",
                "cause_code": "A-100",
                "victim": "M/CYCLIST",
                "fatalities": "1",
                "date": "2024-06-25",
            })
        self.app = create_app(
            self.csv_path,
            admin_password="test-admin-password",
            database_path=self.database_path,
        )
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.login()

    def tearDown(self):
        self.temp_dir.cleanup()

    def login(self):
        response = self.client.get("/login")
        token = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        self.assertIsNotNone(token)
        return self.client.post(
            "/login",
            data={
                "password": "test-admin-password",
                "username": "admin",
                "csrf_token": token.group(1).decode(),
            },
            follow_redirects=True,
        )

    def csrf_token(self):
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def test_first_admin_can_be_created_once_from_login(self):
        app = create_app(
            self.csv_path,
            database_path=self.temp_path / "bootstrap.sqlite3",
        )
        app.config["TESTING"] = True
        client = app.test_client()

        login_page = client.get("/login")
        self.assertIn(b"Create administrator account", login_page.data)
        setup_page = client.get("/setup-admin")
        token = re.search(rb'name="csrf_token" value="([^"]+)"', setup_page.data)
        self.assertIsNotNone(token)
        response = client.post(
            "/setup-admin",
            data={
                "username": "first-admin",
                "email": "admin@example.test",
                "password": "secure-test-password",
                "confirm_password": "secure-test-password",
                "csrf_token": token.group(1).decode(),
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Administrator account created", response.data)
        database = DatabaseManager(app.config["DATABASE_PATH"])
        account = database.authenticate("first-admin", "secure-test-password")
        self.assertIsNotNone(account)
        self.assertEqual(account["role"], "admin")
        self.assertEqual(client.get("/setup-admin").status_code, 404)
        self.assertNotIn(
            b"Create administrator account",
            client.get("/login").data,
        )

    def test_render_requires_persistent_session_and_database_settings(self):
        with patch.dict(
            "os.environ",
            {"RENDER": "true", "FLASK_SECRET_KEY": ""},
        ):
            with self.assertRaisesRegex(RuntimeError, "FLASK_SECRET_KEY"):
                create_app(
                    self.csv_path,
                    database_path=self.temp_path / "render.sqlite3",
                )

        with patch.dict(
            "os.environ",
            {"RENDER": "true", "FLASK_SECRET_KEY": "stable-test-key",
             "TUSALAMA_DATABASE_PATH": ""},
        ):
            with self.assertRaisesRegex(
                RuntimeError, "TUSALAMA_DATABASE_PATH"
            ):
                create_app(self.csv_path)

    def test_admin_setup_is_unavailable_after_any_account_exists(self):
        database_path = self.temp_path / "existing-user.sqlite3"
        database = DatabaseManager(database_path)
        database.create_user(
            "road-user", "user@example.test", "secure-test-password",
            "road_user",
        )
        app = create_app(
            self.csv_path,
            database_path=database_path,
        )
        app.config["TESTING"] = True
        self.assertEqual(app.test_client().get("/setup-admin").status_code, 404)

    def test_admin_login_required_and_logout(self):
        client = self.app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        login_page = client.get("/login")
        token = re.search(rb'name="csrf_token" value="([^"]+)"', login_page.data)
        response = client.post(
            "/login",
            data={
                "password": "wrong-password",
                "username": "admin",
                "csrf_token": token.group(1).decode(),
            },
            follow_redirects=True,
        )
        self.assertIn(b"Username/email or password is incorrect", response.data)

        login_page = client.get("/login")
        token = re.search(rb'name="csrf_token" value="([^"]+)"', login_page.data)
        client.post(
            "/login",
            data={
                "password": "test-admin-password",
                "username": "admin",
                "csrf_token": token.group(1).decode(),
            },
        )
        with client.session_transaction() as session:
            csrf_token = session["csrf_token"]
        response = client.post(
            "/logout", data={"csrf_token": csrf_token}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.get("/").status_code, 302)

    def test_dashboard_incidents_and_hotspot_pages_load(self):
        for path in ("/", "/incidents", "/analytics"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"KITUI SCHOOL", response.data)
        dashboard = self.client.get("/")
        self.assertIn(b"trend-chart", dashboard.data)
        self.assertIn(b"filter-panel", dashboard.data)
        self.assertIn(b'id="chart-data"', dashboard.data)
        analytics = self.client.get("/analytics")
        self.assertIn(b'id="chart-data"', analytics.data)
        self.assertIn(b"dashboard.js?v=", dashboard.data)

    def test_chart_data_api_updates_for_current_filters(self):
        response = self.client.get("/api/chart-data?county=MAKUENI")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["monthly"], {
            "labels": ["2024-06"],
            "values": [1],
            "fatal_incidents": [1],
        })
        self.assertEqual(data["hotspots"], {
            "labels": ["KITUI SCHOOL"],
            "values": [1],
            "fatal_incidents": [1],
        })

        filtered_response = self.client.get(
            "/api/chart-data?county=NAIROBI"
        )
        self.assertEqual(filtered_response.status_code, 200)
        self.assertEqual(filtered_response.get_json()["monthly"]["values"], [])

    def test_ai_evidence_contains_aggregates_without_raw_report_fields(self):
        evidence = build_analysis_evidence([{
            "cause_code": "PRIVATE-REFERENCE",
            "date": "2024-06-25",
            "county": "MAKUENI",
            "place": "KITUI SCHOOL",
            "accident_info": "HEAD ON COLLISION",
            "victim": "M/CYCLIST",
            "fatalities": "1",
            "latitude": "-1.0",
            "longitude": "37.0",
        }])
        self.assertEqual(evidence["record_count"], 1)
        self.assertEqual(evidence["fatalities"], 1)
        self.assertEqual(
            evidence["cause_category_counts"]["motorcycle_risk"], 1
        )
        self.assertNotIn("cause_code", evidence)
        self.assertNotIn("accident_info", evidence)
        self.assertNotIn("latitude", evidence)
        self.assertNotIn("longitude", evidence)

    def test_ai_analysis_requires_configuration_and_valid_csrf(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            response = self.client.post(
                "/api/ai-analysis",
                headers={"X-CSRF-Token": self.csrf_token()},
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENAI_API_KEY", response.get_json()["error"])

    def test_ai_analysis_returns_service_result(self):
        result = {
            "analysis": {
                "summary": "Observed patterns are limited.",
                "future_hotspots": [],
                "likely_causes": [],
                "actions": [],
                "limitations": "No exposure data was available.",
            },
            "evidence": {"record_count": 1},
        }
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch("app.analyze_safety_data", return_value=result),
        ):
            response = self.client.post(
                "/api/ai-analysis",
                headers={"X-CSRF-Token": self.csrf_token()},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), result)

    def test_incident_risk_and_report_export(self):
        response = self.client.get("/incidents/A-100/risk")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Moderate risk", response.data)

        report = self.client.get("/reports/export?format=csv")
        self.assertEqual(report.status_code, 200)
        self.assertIn("attachment;", report.headers["Content-Disposition"])
        self.assertIn(b"Total fatalities,1", report.data)
        excel = self.client.get("/reports/export?format=xlsx")
        self.assertEqual(excel.status_code, 200)
        self.assertIn("spreadsheetml", excel.headers["Content-Type"])
        pdf = self.client.get("/reports/export?format=pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.data.startswith(b"%PDF"))

    def test_create_update_and_delete_incident(self):
        data = {
            "cause_code": "B-200",
            "date": "2024-07-01",
            "time": "14:30",
            "county": "NAIROBI",
            "road": "MOMBASA ROAD",
            "place": "CITY CENTRE",
            "base": "EMBAKASI",
            "accident_info": "PEDESTRIAN ACCIDENT",
            "victim": "PEDESTRIAN",
            "fatalities": "0",
            "latitude": "-1.2864",
            "longitude": "36.8172",
        }
        response = self.client.post(
            "/incidents/new",
            data={**data, "csrf_token": self.csrf_token()},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"B-200", response.data)

        data["place"] = "UPDATED CENTRE"
        response = self.client.post(
            "/incidents/B-200/edit",
            data={**data, "csrf_token": self.csrf_token()},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"UPDATED CENTRE", response.data)

        analytics = self.client.get("/analytics")
        self.assertIn(b"mapped incidents", analytics.data)
        self.assertIn(b"-1.2864", analytics.data)

        response = self.client.post(
            "/incidents/B-200/delete",
            data={"csrf_token": self.csrf_token()},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"B-200", response.data)

        with self.csv_path.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual([row["cause_code"] for row in rows], ["A-100"])

    def test_duplicate_reference_is_rejected(self):
        response = self.client.post(
            "/incidents/new",
            data={
                "cause_code": "A-100",
                "date": "2024-07-01",
                "time": "14:30",
                "county": "NAIROBI",
                "road": "MOMBASA ROAD",
                "place": "CITY CENTRE",
                "base": "EMBAKASI",
                "accident_info": "PEDESTRIAN ACCIDENT",
                "victim": "PEDESTRIAN",
                "fatalities": "0",
                "csrf_token": self.csrf_token(),
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"already in use", response.data)

    def test_dashboard_filters_apply_to_records_and_exports(self):
        response = self.client.get(
            "/?county=MAKUENI&severity=Moderate"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"1 of your records", response.data)

        response = self.client.get(
            "/?county=NAIROBI&start_date=2024-01-01"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"0 of your records", response.data)

        response = self.client.get("/?start_date=2025-01-01&end_date=2024-01-01")
        self.assertEqual(response.status_code, 400)

        report = self.client.get(
            "/reports/export?format=csv&county=NAIROBI"
        )
        self.assertIn(b"Total incidents,0", report.data)

    def test_csv_reader_handles_repeated_headers_with_legacy_column_order(self):
        with self.csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "time", "date", "county", "road", "base", "place",
                "accident_info", "fatalities", "victim", "cause_code",
            ])
            writer.writerow([
                "1430", "2024-07-04", "NAIROBI", "MOMBASA ROAD",
                "EMBAKASI", "CITY CENTRE", "PEDESTRIAN ACCIDENT",
                "0", "PEDESTRIAN", "B-200",
            ])

        records = DatabaseManager(self.database_path).migrate_csv(self.csv_path)
        self.assertEqual(records["imported"], 0)
        # The one-time database import intentionally does not re-read modified CSVs.

    def test_csv_reader_repairs_known_legacy_misordered_values(self):
        with self.csv_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "time", "base", "county", "road", "place",
                "accident_info", "cause_code", "victim",
                "fatalities", "date",
            ])
            writer.writerow([
                "1300", "45", "KIRINYAGA", "SAGANA-KAGIO",
                "04/06/2025", "RIVER SAGANA", "SAGANA TOWN",
                "3", "MOTORIST", "HEAD ON COLLISION",
            ])

        from storage.file_manager import FileManager

        records = FileManager(self.csv_path).load_incidents()
        repaired = records[-1]
        self.assertEqual(repaired["place"], "RIVER SAGANA")
        self.assertEqual(repaired["fatalities"], "3")
        self.assertEqual(repaired["date"], "04/06/2025")

    def test_incident_register_is_paginated(self):
        database = DatabaseManager(self.database_path)
        for index in range(60):
            database.add_incident(
                "1200", "2024-06-25", "NAIROBI", "MOMBASA ROAD",
                "NAIROBI", f"LOCATION {index}", "HEAD ON COLLISION",
                "0", "MOTORIST", f"P-{index:03}",
            )

        first_page = self.client.get("/incidents")
        self.assertEqual(first_page.status_code, 200)
        self.assertIn(b"Page 1 of 2", first_page.data)
        self.assertEqual(first_page.data.count(b"<tr>"), 51)

        second_page = self.client.get("/incidents?page=2")
        self.assertEqual(second_page.status_code, 200)
        self.assertIn(b"Page 2 of 2", second_page.data)
        self.assertEqual(second_page.data.count(b"<tr>"), 12)

    def signup(self, role, username, email, agency_name=""):
        response = self.client.get("/signup")
        token = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        return self.client.post(
            "/signup",
            data={
                "username": username,
                "email": email,
                "password": "long-test-password-123",
                "role": role,
                "agency_name": agency_name,
                "csrf_token": token.group(1).decode(),
            },
            follow_redirects=True,
        )

    def test_profiles_signup_and_agency_approval_hierarchy(self):
        road_user = self.signup(
            "road_user", "roaduser01", "roaduser@example.ke"
        )
        self.assertEqual(road_user.status_code, 200)

        profile = self.client.get("/profile")
        self.assertIn(b"admin@tusalama.local", profile.data)

        agency_response = self.signup(
            "agency", "agencyuser", "agency@example.ke",
            agency_name="Sample Road Agency",
        )
        self.assertEqual(agency_response.status_code, 200)
        admin = DatabaseManager(self.database_path).authenticate(
            "admin", "test-admin-password"
        )
        pending = DatabaseManager(self.database_path).pending_agencies()
        self.assertEqual(len(pending), 1)

        approval = self.client.post(
            f"/admin/agencies/{pending[0]['id']}/approve",
            data={"csrf_token": self.csrf_token()},
            follow_redirects=True,
        )
        self.assertEqual(approval.status_code, 200)
        self.assertEqual(
            DatabaseManager(self.database_path).get_user(pending[0]["id"])["status"],
            "active",
        )

    def test_csv_migration_removes_exact_duplicate_records(self):
        duplicate_csv = self.temp_path / "duplicate.csv"
        rows = [
            {
                "time": "1200", "base": "NAIROBI", "county": "NAIROBI",
                "road": "MOMBASA ROAD", "place": "CBD",
                "accident_info": "COLLISION", "cause_code": "DUP-1",
                "victim": "DRIVER", "fatalities": "0", "date": "2024-02-01",
            },
        ]
        with duplicate_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file, fieldnames=DatabaseManager.INCIDENT_FIELDS
            )
            writer.writeheader()
            writer.writerows(rows * 2)
        target_db = self.temp_path / "dedupe.sqlite3"
        database = DatabaseManager(target_db)
        migrated = database.migrate_csv(duplicate_csv)
        self.assertEqual(migrated, {"imported": 1, "duplicates_removed": 1})
        self.assertEqual(database.count_incidents(), 1)

    def test_road_user_can_only_access_own_incidents_and_public_features(self):
        database = DatabaseManager(self.database_path)
        road_user_id = database.create_user(
            "publicroaduser", "public@example.ke",
            "long-test-password-123", "road_user",
        )
        database.add_incident(
            "1200", "2024-06-25", "NAIROBI", "MOMBASA ROAD", "EMBAKASI",
            "USER LOCATION", "COLLISION", "0", "DRIVER", "ROAD-OWN",
            reporter_id=road_user_id,
        )
        with self.client.session_transaction() as session:
            session["user_id"] = road_user_id

        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"USER LOCATION", dashboard.data)
        self.assertNotIn(b"KITUI SCHOOL", dashboard.data)
        self.assertEqual(self.client.get("/analytics").status_code, 403)
        self.assertEqual(self.client.get("/admin").status_code, 403)
        self.assertEqual(self.client.get("/profile").status_code, 200)

    def test_public_signal_route_returns_empty_when_no_sources_configured(self):
        with patch.dict(
            "os.environ",
            {
                "TUSALAMA_X_USER_IDS": "",
                "TUSALAMA_X_BEARER_TOKEN": "",
                "TUSALAMA_BSKY_HANDLES": "",
                "TUSALAMA_RSS_FEEDS": "",
            },
        ):
            response = self.client.get("/api/public-signals")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["signals"], [])
        self.assertIn("unverified", response.json["notice"])

    def test_geocode_endpoint_uses_configured_service_response(self):
        import io
        from urllib.error import URLError

        payload = (
            b'[{"lat":"-1.2864","lon":"36.8172",'
            b'"display_name":"Nairobi, Kenya"}]'
        )

        class FakeResponse:
            def __enter__(self):
                return io.BytesIO(payload)

            def __exit__(self, *_):
                return False

        with patch("app.urllib.request.urlopen", return_value=FakeResponse()) as opener:
            response = self.client.get("/api/geocode?q=Nairobi")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["latitude"], -1.2864)
        self.assertEqual(response.json["longitude"], 36.8172)
        opener.assert_called_once()
        self.assertEqual(
            self.client.get("/api/geocode?q=x").status_code,
            400,
        )


if __name__ == "__main__":
    unittest.main()
