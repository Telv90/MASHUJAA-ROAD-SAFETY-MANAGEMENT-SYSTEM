
class IncidentService:
    def __init__(self, file_manager):
        """Store the FileManager object."""
        self.file_manager = file_manager

    def register_incident(self, incident, reporter_id=None):
        """Validate and register a new incident."""

        incidents = self.file_manager.load_incidents()

        if any(
            existing["cause_code"] == str(incident["cause_code"])
            for existing in incidents
        ):
            return "Incident already recorded!"

        if not self.file_manager.add_incident(
            incident["time"],
            incident["date"],
            incident["county"],
            incident["road"],
            incident["base"],
            incident["place"],
            incident["accident_info"],
            incident["fatalities"],
            incident["victim"],
            incident["cause_code"],
            incident.get("latitude", ""),
            incident.get("longitude", ""),
            reporter_id=reporter_id,
        ):
            return "Incident already recorded!"

        return "Incident registered successfully!"

    def view_all_incidents(self, owner_user_id=None, agency_name=None):
        """Retrieve all stored incidents."""
        if agency_name:
            incidents = self.file_manager.load_incidents(
                agency_name=agency_name
            )
        elif owner_user_id is None:
            incidents = self.file_manager.load_incidents()
        else:
            incidents = self.file_manager.load_incidents(owner_user_id)
        return incidents

    def search_incident(self, cause_code, owner_user_id=None, agency_name=None):
        """Find incidents using a cause code."""

        if hasattr(self.file_manager, "search_incident"):
            return self.file_manager.search_incident(
                cause_code, owner_user_id, agency_name
            )

        incidents = self.file_manager.load_incidents()

        for incident in incidents:
            if incident["cause_code"] == str(cause_code):
                return incident

        return None

    def update_incident(
        self, cause_code, updates, owner_user_id=None, agency_name=None,
    ):
        """Update selected details of an incident."""

        if hasattr(self.file_manager, "update_incident"):
            updated = self.file_manager.update_incident(
                cause_code, updates, owner_user_id, agency_name
            )
            return (
                "Record updated successfully!"
                if updated else "Incident not found!"
            )

        incidents = self.file_manager.load_incidents()

        for incident in incidents:
            if incident["cause_code"] == str(cause_code):

                for field, value in updates.items():
                    if field in incident:
                        incident[field] = str(value)

                self.file_manager.save_incidents(incidents)
                return "Record updated successfully!"

        return "Incident not found!"

    def delete_incident(
        self, cause_code, owner_user_id=None, agency_name=None,
    ):
        """Delete an incident using its cause code."""

        if hasattr(self.file_manager, "delete_incident"):
            deleted = self.file_manager.delete_incident(
                cause_code, owner_user_id, agency_name
            )
            return (
                "Incident deleted successfully!"
                if deleted else "Incident not found!"
            )

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
