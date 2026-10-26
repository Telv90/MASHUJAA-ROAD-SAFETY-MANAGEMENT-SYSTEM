import json
import os
import urllib.error
import urllib.request
from collections import Counter

from Services.hotspot_forecasting import forecast_hotspots


CAUSE_KEYWORDS = {
    "speed_or_loss_of_control": ("SPEED", "OVERSPEED", "LOST CONTROL", "ROLLOVER"),
    "pedestrian_risk": ("PEDESTRIAN", "CROSSING", "FOOT"),
    "motorcycle_risk": ("MOTORCYCLE", "M/CYCLE", "M/CYCLIST", "RIDER"),
    "overtaking_or_collision": ("OVERTAK", "HEAD ON", "COLLISION"),
    "visibility_or_road_condition": ("VISIBILITY", "DARK", "RAIN", "POTHOLE", "SURFACE"),
}


def build_analysis_evidence(incidents):
    cause_counts = Counter()
    monthly_counts = Counter()
    locations = Counter()
    fatalities = 0

    for incident in incidents:
        description = " ".join((
            incident.get("accident_info", ""),
            incident.get("victim", ""),
        )).upper()
        matched_causes = [
            cause for cause, keywords in CAUSE_KEYWORDS.items()
            if any(keyword in description for keyword in keywords)
        ]
        if matched_causes:
            cause_counts.update(matched_causes)
        else:
            cause_counts["unclassified"] += 1

        incident_date = incident.get("date", "")
        if len(incident_date) >= 7:
            monthly_counts[incident_date[:7]] += 1
        if incident.get("place", "").strip():
            locations[(
                incident.get("place", "").strip(),
                incident.get("county", "").strip(),
            )] += 1
        fatalities += int(incident.get("fatalities") or 0)

    return {
        "record_count": len(incidents),
        "fatalities": fatalities,
        "cause_category_counts": dict(cause_counts.most_common()),
        "monthly_record_counts": dict(sorted(monthly_counts.items())[-12:]),
        "top_locations": [
            {"location": place, "county": county, "record_count": count}
            for (place, county), count in locations.most_common(10)
        ],
    }


def analyze_safety_data(incidents, forecast=None):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI analysis is not configured.")

    evidence = build_analysis_evidence(incidents)
    forecast = forecast or forecast_hotspots(incidents)
    evidence["historical_hotspot_forecast"] = {
        "status": forecast["status"],
        "period": forecast["period"],
        "latest_date": forecast["latest_date"],
        "projections": forecast["forecasts"],
    }
    payload = {
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a cautious road-safety analyst. Analyze only the "
                    "provided aggregate counts and the supplied historical "
                    "hotspot forecast. Cause-category counts may overlap and "
                    "are not mutually exclusive. Do not state that an "
                    "association proves a cause, invent evidence, or claim "
                    "traffic exposure data that is absent. Do not create "
                    "independent forecasts; summarize the supplied "
                    "projections only, and return no future hotspots when "
                    "their status is not available. Return JSON with keys "
                    "summary (string), future_hotspots (array of objects "
                    "with location, county, expected_incidents, confidence, "
                    "rationale as strings), likely_causes (array of objects "
                    "with cause, evidence, confidence), actions (array of "
                    "objects with action, reason, priority), and limitations "
                    "(string)."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(evidence, ensure_ascii=True),
            },
        ],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    try:
        content = result["choices"][0]["message"]["content"]
    except (IndexError, KeyError, TypeError) as error:
        raise ValueError(
            "The AI response did not contain message content."
        ) from error
    analysis = json.loads(content)
    required_keys = {
        "summary", "future_hotspots", "likely_causes", "actions",
        "limitations",
    }
    if not isinstance(analysis, dict) or not required_keys.issubset(analysis):
        raise ValueError("The AI response did not match the expected format.")
    if (
        not isinstance(analysis["summary"], str)
        or not isinstance(analysis["future_hotspots"], list)
        or not isinstance(analysis["likely_causes"], list)
        or not isinstance(analysis["actions"], list)
        or not isinstance(analysis["limitations"], str)
    ):
        raise ValueError("The AI response contained invalid field types.")
    if any(
        not isinstance(item, dict)
        or not all(
            isinstance(item.get(field), str)
            for field in (
                "location", "county", "expected_incidents",
                "confidence", "rationale",
            )
        )
        for item in analysis["future_hotspots"]
    ):
        raise ValueError("The AI response contained invalid hotspot projections.")
    if any(
        not isinstance(item, dict)
        or not all(
            isinstance(item.get(field), str)
            for field in ("cause", "evidence", "confidence")
        )
        for item in analysis["likely_causes"]
    ):
        raise ValueError("The AI response contained invalid cause findings.")
    if any(
        not isinstance(item, dict)
        or not all(
            isinstance(item.get(field), str)
            for field in ("action", "reason", "priority")
        )
        for item in analysis["actions"]
    ):
        raise ValueError("The AI response contained invalid safety actions.")
    return {"analysis": analysis, "evidence": evidence}
