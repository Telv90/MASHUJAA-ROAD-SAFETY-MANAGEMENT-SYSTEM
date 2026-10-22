#  MASHUJAA ROAD SAFETY MANAGEMENT SYSTEM
## FUNCTIONAL REQUIREMENTS
### MODULE 1: ACCIDENT REGISTRATION AND VALIDATION
The road safety management system should be able to record:
1. Incident ID
2. Accident date and time
3. Country and road name
4. Accident type: collision,pedestrian accident,rollover or other
5. Number of vehicles involved
6. Number of injuries and fatalities
7. Weather and road conditions
8. Suspected contribution factor,such as speeding,poor visibility,or unsafe road design.
#### Requirements
1. Reject invalid dates,negative counts,empty names,and duplicate incidents IDs.
2. Ensure fatalities and injuries are logically consistent with the incident data.
3. Allow users to view,search,update and delete accidenet records.
### MODULE 2: ROAD RISK EVALUATION
The road safety management system should be able to calculate risk score and classify the result as Low,Moderate,High,Critical based on:
1. Weather severity
2. Road surface condition visibility
3. Speed-related factors
4. Pedestrian presence
5. Accident severity,including injuries and fatalities
#### REQUIREMENTS
1. The risk calculation should be separate from user Interface.
2.  Explain factors contributing to each score.
3. Explain the factors contributing to each score.
4. Recommend suitable preventive measures based on the identified risks.
5. Test the boundaries between risk categories.
### ROAD BLACKSPOT ANALYSIS
The system should be able to analyse stored records to identify locations that are repeatedly experience accidents.
##### REQUIREMENTS
1. Count accidents per road of location.
2. Rank locations by accident Frequency.
3. Map out locations with fatalities.
4. Produce a summary report of the most frequent accidents types and contributing factors.
5. Differentiate between high accident count and high severity count.
### MODULE 3: REPORTS GENERATION
The raod  safety sytem should be able to:
1. Save accident records when the program loads.
2. Load existing records when the program starts.
3. Handle missing,empty or malformed data files without an unexplained crash.
4. Generate summary reports containing total accidents,injuries,fatalities,risk categories and  hotspots.
5. Export  a report to a separate file.
## NON-FUNCTIOANL REQUIREMENTS
The road safety system should be able to:
1. Load within 5 seconds.
2. Be easy to use.
3. Produce results within 5 seconds
