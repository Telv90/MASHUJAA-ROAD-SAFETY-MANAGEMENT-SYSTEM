import unittest
from datetime import date

from Services.hotspot_forecasting import (
    forecast_hotspots,
    recommend_safety_actions,
)


def monthly_records(start_year, start_month, months, incidents_per_month=2):
    records = []
    for offset in range(months):
        month_index = start_year * 12 + start_month - 1 + offset
        year, zero_based_month = divmod(month_index, 12)
        month = zero_based_month + 1
        for index in range(incidents_per_month):
            records.append({
                "date": f"{year:04d}-{month:02d}-15",
                "county": "NAIROBI",
                "place": "CITY CENTRE",
                "fatalities": "1" if index == 0 else "0",
                "accident_info": "PEDESTRIAN ACCIDENT",
                "victim": "PEDESTRIAN",
            })
    return records


class HotspotForecastTests(unittest.TestCase):
    def test_forecasts_rank_recent_locations_with_explainable_evidence(self):
        records = monthly_records(2024, 1, 12)
        forecast = forecast_hotspots(records, today=date(2024, 12, 20))

        self.assertEqual(forecast["status"], "available")
        self.assertEqual(forecast["records_used"], 24)
        self.assertEqual(forecast["months_observed"], 12)
        self.assertEqual(forecast["forecasts"][0]["location"], "CITY CENTRE")
        self.assertEqual(forecast["forecasts"][0]["fatal_incidents"], 12)
        self.assertGreater(
            forecast["forecasts"][0]["expected_incidents"], 0
        )

    def test_stale_data_does_not_present_current_forecast(self):
        forecast = forecast_hotspots(
            monthly_records(2023, 1, 12),
            today=date(2026, 10, 24),
        )
        self.assertEqual(forecast["status"], "stale_data")
        self.assertEqual(forecast["forecasts"], [])
        self.assertIn("old", forecast["message"])

    def test_insufficient_dates_are_reported(self):
        forecast = forecast_hotspots([{
            "date": "",
            "place": "Unknown",
            "fatalities": "0",
        }])
        self.assertEqual(forecast["status"], "no_dates")
        self.assertEqual(forecast["forecasts"], [])

    def test_recommendations_show_evidence_and_fatal_counts(self):
        records = monthly_records(2024, 1, 2)
        recommendations = recommend_safety_actions(records)
        pedestrian = next(
            item for item in recommendations
            if item["title"] == "Improve pedestrian protection"
        )
        self.assertEqual(pedestrian["evidence_count"], 4)
        self.assertEqual(pedestrian["fatal_count"], 2)
        self.assertEqual(pedestrian["locations"][0]["place"], "CITY CENTRE")


if __name__ == "__main__":
    unittest.main()
