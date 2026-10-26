import json
import unittest
from unittest.mock import patch

from Services.ai_safety_analysis import analyze_safety_data


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        return False

    def read(self):
        return self.payload


class AISafetyAnalysisTests(unittest.TestCase):
    def test_openai_receives_aggregates_and_returns_validated_analysis(self):
        analysis = {
            "summary": "The small sample is inconclusive.",
            "future_hotspots": [],
            "likely_causes": [{
                "cause": "Possible pedestrian risk",
                "evidence": "One matching record",
                "confidence": "Low",
            }],
            "actions": [{
                "action": "Review crossing safety",
                "reason": "Pedestrian risks were identified",
                "priority": "Low",
            }],
            "limitations": "Traffic exposure was not available.",
        }
        response_payload = {
            "choices": [{
                "message": {"content": json.dumps(analysis)},
            }],
        }
        incident = {
            "cause_code": "PRIVATE-REFERENCE",
            "date": "2024-06-25",
            "county": "MAKUENI",
            "place": "KITUI SCHOOL",
            "accident_info": "PEDESTRIAN CROSSING",
            "victim": "PEDESTRIAN",
            "fatalities": "0",
            "latitude": "-1.0",
            "longitude": "37.0",
        }
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch(
                "Services.ai_safety_analysis.urllib.request.urlopen",
                return_value=FakeResponse(json.dumps(
                    response_payload
                ).encode("utf-8")),
            ) as open_url,
        ):
            result = analyze_safety_data([incident])

        request = open_url.call_args.args[0]
        request_body = json.loads(request.data.decode("utf-8"))
        evidence = json.loads(request_body["messages"][1]["content"])
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")
        self.assertEqual(evidence["record_count"], 1)
        self.assertNotIn("PRIVATE-REFERENCE", json.dumps(evidence))
        self.assertNotIn("PEDESTRIAN CROSSING", json.dumps(evidence))
        self.assertNotIn("latitude", evidence)
        self.assertEqual(result["analysis"], analysis)


if __name__ == "__main__":
    unittest.main()
