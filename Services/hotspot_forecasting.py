from collections import Counter, defaultdict
from datetime import date, datetime
from math import sqrt


DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y")
RECOMMENDATIONS = (
    (
        ("PEDESTRIAN", "CROSSING", "FOOT", "WALKER"),
        "Improve pedestrian protection",
        "Review crossing placement, lighting, footpaths, and vehicle speeds at the reported location.",
    ),
    (
        ("HEAD ON", "OVERTAK", "OVERTAKE", "COLLISION"),
        "Reduce head-on and overtaking risk",
        "Assess passing restrictions, centre-line markings, warning signs, and median protection.",
    ),
    (
        ("MOTORCYCLE", "M/CYCLE", "M/CYCLIST", "RIDER"),
        "Target motorcycle safety",
        "Check road-surface hazards and visibility, and coordinate helmet and rider-safety enforcement.",
    ),
    (
        ("ROLLED", "ROLLOVER", "LOST CONTROL", "LOSS OF CONTROL", "SPEED"),
        "Manage speed and loss-of-control risk",
        "Audit speed limits, curve warnings, surface condition, and roadside barriers.",
    ),
)


def parse_incident_date(value):
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except (TypeError, ValueError):
            continue
    return None


def _month_index(value):
    return value.year * 12 + value.month - 1


def _regression_forecast(values, horizon):
    count = len(values)
    mean_x = (count - 1) / 2
    mean_y = sum(values) / count
    variance_x = sum((index - mean_x) ** 2 for index in range(count))
    slope = (
        sum((index - mean_x) * (value - mean_y)
            for index, value in enumerate(values)) / variance_x
        if variance_x
        else 0.0
    )
    forecast = sum(
        max(0.0, mean_y + slope * (count + step - mean_x))
        for step in range(horizon)
    )
    residuals = [
        value - (mean_y + slope * (index - mean_x))
        for index, value in enumerate(values)
    ]
    residual_error = sqrt(sum(error * error for error in residuals) / count)
    return forecast, slope, residual_error


def forecast_hotspots(incidents, today=None, horizon=3):
    """Return an explainable monthly trend forecast and its evidence limits."""
    today = today or date.today()
    dated_records = [
        (incident, parse_incident_date(incident.get("date", "")))
        for incident in incidents
    ]
    dated_records = [
        (incident, incident_date)
        for incident, incident_date in dated_records
        if incident_date is not None and incident.get("place", "").strip()
    ]
    if not dated_records:
        return {
            "status": "no_dates",
            "message": "No valid incident dates are available to build a forecast.",
            "latest_date": None,
            "period": None,
            "records_used": 0,
            "months_observed": 0,
            "forecasts": [],
        }

    latest_date = max(incident_date for _, incident_date in dated_records)
    latest_month = date(latest_date.year, latest_date.month, 1)
    age_days = (today - latest_date).days
    recent_start_index = _month_index(latest_month) - 23
    recent_records = [
        (incident, incident_date)
        for incident, incident_date in dated_records
        if _month_index(incident_date) >= recent_start_index
        and _month_index(incident_date) <= _month_index(latest_month)
    ]
    observed_months = len({
        _month_index(incident_date)
        for _, incident_date in recent_records
    })
    start_month_index = _month_index(latest_month) - 11
    start_year, start_month = divmod(start_month_index, 12)
    start_month += 1
    month_labels = []
    for offset in range(12):
        month_index = _month_index(date(start_year, start_month, 1)) + offset
        year, month = divmod(month_index, 12)
        month_labels.append(f"{year:04d}-{month + 1:02d}")

    future_months = []
    for offset in range(1, horizon + 1):
        month_index = _month_index(latest_month) + offset
        year, month = divmod(month_index, 12)
        future_months.append(f"{year:04d}-{month + 1:02d}")
    period = f"{future_months[0]} to {future_months[-1]}"

    if age_days > 365:
        status = "stale_data"
        message = (
            f"The latest incident is {age_days} days old. Refresh the incident "
            "register with recent verified reports before treating a projection "
            "as a current forecast."
        )
    elif len(recent_records) < 12 or observed_months < 6:
        status = "insufficient_data"
        message = (
            "At least 12 incidents across 6 distinct recent months are needed "
            "for a useful trend projection. Keep recording verified incidents."
        )
    else:
        status = "available"
        message = (
            "Experimental, location-level linear trend over the latest 12 "
            "observed months; it is a planning signal, not a crash probability."
        )

    monthly_location_counts = defaultdict(Counter)
    fatal_counts = Counter()
    for incident, incident_date in recent_records:
        key = (
            incident.get("county", "").strip() or "Unknown county",
            incident.get("place", "").strip(),
        )
        month_label = incident_date.strftime("%Y-%m")
        monthly_location_counts[key][month_label] += 1
        if int(incident.get("fatalities") or 0) > 0:
            fatal_counts[key] += 1

    forecasts = []
    if status == "available":
        for (county, location), monthly_counts in monthly_location_counts.items():
            values = [monthly_counts[month] for month in month_labels]
            expected_count, monthly_trend, error = _regression_forecast(
                values, horizon
            )
            if expected_count <= 0:
                continue
            total_location_records = sum(monthly_counts.values())
            confidence = (
                "Higher"
                if total_location_records >= 24 and observed_months >= 18
                else "Moderate"
                if total_location_records >= 12 and observed_months >= 12
                else "Low"
            )
            forecasts.append({
                "county": county,
                "location": location,
                "expected_incidents": round(expected_count, 1),
                "historical_incidents": total_location_records,
                "fatal_incidents": fatal_counts[(county, location)],
                "monthly_trend": round(monthly_trend, 2),
                "trend_error": round(error, 2),
                "confidence": confidence,
            })
        forecasts.sort(
            key=lambda item: (
                item["expected_incidents"],
                item["fatal_incidents"],
                item["historical_incidents"],
            ),
            reverse=True,
        )

    return {
        "status": status,
        "message": message,
        "latest_date": latest_date.isoformat(),
        "period": period,
        "records_used": len(recent_records),
        "months_observed": observed_months,
        "forecasts": forecasts[:10],
    }


def recommend_safety_actions(incidents, limit=8):
    """Suggest practical audits from the recorded incident descriptions."""
    recommendations = []
    for keywords, title, action in RECOMMENDATIONS:
        matches = [
            incident for incident in incidents
            if any(
                keyword in incident.get("accident_info", "").upper()
                or keyword in incident.get("victim", "").upper()
                for keyword in keywords
            )
        ]
        if not matches:
            continue
        locations = Counter(
            (
                incident.get("place", "").strip(),
                incident.get("county", "").strip(),
            )
            for incident in matches
            if incident.get("place", "").strip()
        )
        recommendations.append({
            "title": title,
            "action": action,
            "evidence_count": len(matches),
            "fatal_count": sum(
                int(incident.get("fatalities") or 0) > 0
                for incident in matches
            ),
            "locations": [
                {"place": place, "county": county, "count": count}
                for (place, county), count in locations.most_common(3)
            ],
        })
    return sorted(
        recommendations,
        key=lambda item: (item["fatal_count"], item["evidence_count"]),
        reverse=True,
    )[:limit]
