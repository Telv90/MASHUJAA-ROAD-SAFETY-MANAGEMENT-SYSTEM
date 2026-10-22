class Incident:
    def __init__(self,time,date,county,road,place,base,accident_info,cause_code,fatalities,victim):
        self.time=time
        self.date=date
        self.county=county
        self.road=road
        self.place=place
        self.base=base
        self.accident_info=accident_info
        self.cause_code=cause_code
        self.fatalities=fatalities
        self.victim=victim
    def __str__(self):
        return f"{self.time}|{self.date}|{self.county}|{self.road}|{self.place}|{self.accident_info}|{self.victim}"
    def get_details(self):
       return { 
           "time": self.time,
           "date": self.date,
           "county": self.county,
           "road": self.road,
           "base": self.base,
           "place": self.place,
           "accident": self.accident_info,
           "fatalities": self.fatalities,
           "victim":self.victim,
           "cause code":self.cause_code
        }
   
    def update_details(self, updates):
     """Update selected incident attributes."""

     if not isinstance(updates, dict):
        raise TypeError("Updates must be provided as a dictionary.")

     allowed_fields = {
        "date",
        "time",
        "county",
        "road",
        "base",
        "place"
        "accident",
        "victim",
        "fatalities",
        "cause code"
     }

     for field, value in updates.items():
        if field not in allowed_fields:
            raise ValueError(f"Field '{field}' cannot be updated.")

        if value is None or value == "":
            raise ValueError(f"'{field}' cannot be empty.")

        if field in { "cause code", "fatalities"}:
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"'{field}' must be an integer.")

            if value < 0:
                raise ValueError(f"'{field}' cannot be negative.")

        setattr(self, field, value)


    def get_severity(self):

      if self.fatalities >0:
        return "Fatal"
      else:
        return "Property Damage / No Recorded Injuries"


    def to_dict(self):
      """Convert the incident object into a dictionary."""

      return {
        "incident_id": self.incident_id,
        "date": self.date,
        "time": self.time,
        "county": self.county,
        "road": self.road,
        "location": self.location,
        "accident_type": self.accident_type,
        "vehicles_involved": self.vehicles_involved,
        "injuries": self.injuries,
        "fatalities": self.fatalities,
        "weather": self.weather,
        "road_condition": self.road_condition,
        "contributing_factor": self.contributing_factor
    }
 
    