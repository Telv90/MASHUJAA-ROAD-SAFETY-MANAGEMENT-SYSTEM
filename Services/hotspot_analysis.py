
class HotspotAnalysis:
    def __init__(self, incidents):
        """Initialize the analysis with accident records."""
        self.incidents = incidents

    def count_by_county(self, county):
        """Count accidents recorded in a specific county."""
        score=0
        for incident in self.incidents:
            if incident["county"].upper()==county.upper():
                score+=1
        return score
    def count_by_road(self, road):
        """Count accidents recorded on a specific road."""
        count = 0

        for incident in self.incidents:
            if incident["road"].upper() == road.upper():
                count = count + 1

        return count


    def count_by_location(self, location):
        """Count accidents recorded at a specific location."""
        count = 0

        for incident in self.incidents:
            if incident["place"].upper() == location.upper():
                count = count + 1

        return count


    def find_high_risk_locations(self):
        """Identify locations with frequent accident records."""
        location_counts = {}

        for incident in self.incidents:
            location = incident["place"]

            if location in location_counts:
                location_counts[location] = location_counts[location] + 1
            else:
                location_counts[location] = 1

        high_risk_locations = []

        for location in location_counts:
            if location_counts[location] >= 3:
                high_risk_locations.append(location)

        return high_risk_locations


    def generate_hotspot_report(self):
        """Generate a summary of accident hotspots."""
        report = []

        for incident in self.incidents:
            location = incident["place"]

            already_added = False

            for item in report:
                if item["location"].upper() == location.upper():
                    already_added = True

            if already_added == False:
                count = self.count_by_location(location)

                hotspot = {
                    "location": location,
                    "accident_count": count
                }

                report.append(hotspot)

        return report
     


   