
# Import required classes
from storage.file_manager import FileManager
from Services.incident_services import IncidentService
from Services.risk_assessment import RiskAssessment
from Services.hotspot_analysis import HotspotAnalysis


# Initialize application objects
file_manager = FileManager("incidents.csv")
incident_service = IncidentService(file_manager)
risk_assessment = RiskAssessment()


def display_menu():
    """Display the main application menu."""
    print("\n===== TUSALAMA ROAD SAFETY SYSTEM =====")
    print("1. Register an accident")
    print("2. View all accidents")
    print("3. Search for an accident")
    print("4. Update an accident")
    print("5. Delete an accident")
    print("6. Assess accident risk")
    print("7. Analyze accident hotspots")
    print("8. Generate hotspot report")
    print("9. Exit")



def register_accident():
    """Collect accident details and register a record."""

    incident = {}

    try:
        incident["time"] = input(
            "Enter the accident time (HHMM, 24-hour clock): "
        )
        incident["county"] = input(
            "Enter the county where the accident occurred: "
        )
        incident["road"] = input(
            "Enter the road where the accident occurred: "
        )
        incident["place"] = input(
            "Enter the accident location: "
        )
        incident["accident_info"] = input(
            "Enter a short description of the accident: "
        )
        incident["cause_code"] = input(
            "Enter the accident cause code: "
        )
        incident["victim"] = input(
            "Enter the victim type (cyclist/pedestrian etc.): "
        )
        incident["fatalities"] = int(input(
            "Enter the number of fatalities: "
        ))
        incident["date"] = input(
            "Enter the accident date (DD/MM/YYYY): "
        )
        incident["base"]=input(
            "Enter the base location of the accident: "
        )


    except ValueError:
        print("Age and fatalities must be valid integers!")
        return

    result = incident_service.register_incident(incident)
    print(result)

def view_all_accidents():
    """Display all recorded accidents."""

    incidents = incident_service.view_all_incidents()

    if len(incidents) == 0:
        print("No accident records found.")
        return

    for incident in incidents:
        print("----------------------------")
        print("Date:", incident["date"])
        print("Time:", incident["time"])
        print("County:", incident["county"])
        print("Road:", incident["road"])
        print("Place:", incident["place"])
        print("Accident details:", incident["accident_info"])
        print("Fatalities:", incident["fatalities"])
        print("Cause code:", incident["cause_code"])


def search_accident():
    """Search for an accident record."""
    try:
     cause_code=int(input("Enter the cause code"))
     incident=incident_service.search_incident(cause_code)
     if incident is not None:
        print(incident)
     else:
      print("cause code not found")
          
    except ValueError:
        return "Cause code should be an integer!Try again"
def update_accident():
    """Update an existing accident record."""
    cause_code = input("Enter the cause code of the accident: ")

    incident = incident_service.search_incident(cause_code)

    if incident is None:
        print("Accident record not found.")
        return

    print("\n===== UPDATE ACCIDENT =====")
    print("1. Time")
    print("2. Date")
    print("3. County")
    print("4. Road")
    print("5. Place")
    print("6. Accident information")
    print("7. Fatalities")
    print("8. Victim")
    print("9. Cause code")

    choice = input("Choose the field to update: ")

    if choice == "1":
        field = "time"
    elif choice == "2":
        field = "date"
    elif choice == "3":
        field = "county"
    elif choice == "4":
        field = "road"
    elif choice == "5":
        field = "place"
    elif choice == "6":
        field = "accident_info"
    elif choice == "7":
        field = "fatalities"
    elif choice == "8":
        field = "victim"
    elif choice == "9":
        field = "cause_code"
    else:
        print("Invalid choice.")
        return

    new_value = input("Enter the new value: ")

    updates = {field: new_value}

    result = incident_service.update_incident(cause_code, updates)

    print(result)
    


def delete_accident():
    """Delete an accident record."""
    cause_code = input("Enter the cause code of the accident: ")

    incident = incident_service.search_incident(cause_code)

    if incident is not None:
        result = incident_service.delete_incident(cause_code)
        print(result)
    else:
        print("Accident record not found.")


def assess_accident_risk():
    """Calculate and display an accident risk score."""
    cause_code = input("Enter the accident cause code: ")

    incident = incident_service.search_incident(cause_code)

    if incident is not None:
        score = risk_assessment.calculate_risk_score(incident)
        level = risk_assessment.get_risk_level(score)

        print("Risk score:", score)
        print("Risk level:", level)
    else:
        print("Accident record not found.")


def analyze_hotspots():
    """Analyze accident counts by road and location."""
    incidents = file_manager.load_incidents()

    if len(incidents) == 0:
        print("No accident records available.")
        return

    hotspot_analysis = HotspotAnalysis(incidents)

    print("\n1. Count accidents by road")
    print("2. Count accidents by location")

    choice = input("Choose an option: ")

    if choice == "1":
        road = input("Enter road name: ").upper()
        count = hotspot_analysis.count_by_road(road)
        print("Accidents recorded on", road, ":", count)

    elif choice == "2":
        location = input("Enter location: ")
        count = hotspot_analysis.count_by_location(location)
        print("Accidents recorded at", location, ":", count)

    else:
        print("Invalid choice.")

def generate_hotspot_report():
    """Display a summary of accident hotspots."""
    incidents = file_manager.load_incidents()

    if len(incidents) == 0:
        print("No accident records available.")
        return

    hotspot_analysis = HotspotAnalysis(incidents)
    report = hotspot_analysis.generate_hotspot_report()

    print("\n===== ACCIDENT HOTSPOT REPORT =====")

    for hotspot in report:
        print("Location:", hotspot["location"])
        print(f"Accident count: {hotspot['accident_count']}")
        print("-"*20)


def main():
    """Run the main application loop."""
    while True:
        display_menu()

        choice = input("Enter your choice (1-9): ")

        if choice == "1":
            register_accident()
        elif choice == "2":
            view_all_accidents()
        elif choice == "3":
            search_accident()
        elif choice == "4":
            update_accident()
        elif choice == "5":
            delete_accident()
        elif choice == "6":
            assess_accident_risk()
        elif choice == "7":
            analyze_hotspots()
        elif choice == "8":
            generate_hotspot_report()
        elif choice == "9":
            print("Thank you for using MASHUJAA.")
            break
        else:
            print("Invalid choice. Please select 1-9.")


if __name__ == "__main__":
    main()
