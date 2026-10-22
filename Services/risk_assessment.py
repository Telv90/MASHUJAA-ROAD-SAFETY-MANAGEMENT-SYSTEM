
class RiskAssessment:
    def __init__(self):
        """Initialize the risk assessment rules."""
        pass
    def assess_fatalities(self, fatalities):
        """Assess risk based on the number of fatalities."""
        fatalities = int(fatalities)

        if fatalities >= 3:
            return 8
        elif fatalities >= 1:
            return 4
        else:
            return 0
    def assess_accident_type(self,accident_type):
        accident_type=str(accident_type).capitalize()
        if accident_type=="Hit and Run":
            return 10
        elif accident_type=="Pedestrian accident":
            return 8
        elif accident_type=="Motorcycle accident":
            return 6
        elif accident_type=="Head on collision":
            return 4
        elif accident_type=="Loss of control":
            return 2
        else:
            return 0
        
    def calculate_risk_score(self, incident):
        """Calculate the overall risk score for an incident."""
        fatalities = incident["fatalities"]
        accident_type=incident["accident_info"]
        accident_score=self.assess_accident_type(accident_type)
        fatalities_score = self.assess_fatalities(fatalities)
        score=accident_score+fatalities_score
        return score

    def get_risk_level(self, risk_score):
        """Classify the score as Low, Moderate, High, or Critical."""
        if risk_score>=15:
            return "Critical"
        elif risk_score>=10:
            return "High"
        elif risk_score>=5:
            return "Moderate"
        else:
            return "Low"
risk=RiskAssessment()
