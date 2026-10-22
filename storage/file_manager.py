
import csv


class FileManager:
    def __init__(self, file_path):
        """Store the path of the CSV file."""
        self.file_path=file_path

    def load_incidents(self):
        """Read incident records from the CSV file."""
        incidents=[]
        with open(self.file_path,"r") as file:
          reader=csv.DictReader(file)
          for incident in reader:
              incidents.append(incident)
          return incidents

    def save_incidents(self, incidents):
        """Save a collection of incident records to the CSV file."""
        with open(self.file_path,"a",newline="")as file:
            fieldnames=["time","date","county","road","base","place","accident_info","fatalities","victim","cause_code"]
            writer=csv.DictWriter(file,fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(incidents)

        

    def add_incident(self,time,date,county,road,base,place,accident_info,fatalities,victim,cause_code):
        """Add one incident record to the stored data."""
        incidents=self.load_incidents()
        incident={ 
           "time":time,
           "date":date,
           "county":county,
           "road": road,
           "base": base,
           "place": place,
           "accident_info": accident_info,
           "fatalities":fatalities,
           "victim":victim,
           "cause_code":cause_code
    }
        if incident in incidents:
            print("Incident already recorded!")
            return False
        file_exists = self.file_exists()

        with open(self.file_path, "a", newline="") as file:
         fieldnames = [
            "time", "date", "county", "road", "base",
            "place", "accident_info", "fatalities",
            "victim", "cause_code"
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        writer.writerow(incident)
        print("Incident recorded successfully!")
        return True
    def file_exists(self):
        """Check whether the CSV file exists."""
        try:
            with open(self.file_path,"r")as file:
                content=file.read()
        except FileNotFoundError:
            return False
        else:
            return True
manager=FileManager("incident.csv")
manager.file_path
