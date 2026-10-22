
class IncidentService:
    def __init__(self, file_manager):
        """Store the FileManager object."""
        self.file_manager = file_manager

    def register_incident(self, incident):
        """Validate and register a new incident."""

        incidents = self.file_manager.load_incidents()

        # Check whether the exact record already exists
        if incident in incidents:
            return "Incident already recorded!"

        # Save the new incident
        self.file_manager.add_incident(
            incident["time"],
            incident["date"],
            incident["county"],
            incident["road"],
            incident["base"],
            incident["place"],
            incident["accident_info"],
            incident["fatalities"],
            incident["victim"],
            incident["cause_code"]
        )

        return "Incident registered successfully!"

    def view_all_incidents(self):
        """Retrieve all stored incidents."""
        incidents = self.file_manager.load_incidents()
        return incidents

    def search_incident(self, cause_code):
        """Find incidents using a cause code."""

        incidents = self.file_manager.load_incidents()

        for incident in incidents:
            if incident["cause_code"] == str(cause_code):
                return incident

        return None

    def update_incident(self, cause_code, updates):
        """Update selected details of an incident."""

        incidents = self.file_manager.load_incidents()

        for incident in incidents:
            if incident["cause_code"] == str(cause_code):

                for field, value in updates.items():
                    if field in incident:
                        incident[field] = str(value)

                self.file_manager.save_incidents(incidents)
                return "Record updated successfully!"

        return "Incident not found!"

    def delete_incident(self, cause_code):
        """Delete an incident using its cause code."""

        incidents = self.file_manager.load_incidents()
        updated_incidents = []
        found = False

        for incident in incidents:
            if incident["cause_code"] == str(cause_code):
                found = True
            else:
                updated_incidents.append(incident)

        if found:
            self.file_manager.save_incidents(updated_incidents)
            return "Incident deleted successfully!"

        return "Incident not found!"
