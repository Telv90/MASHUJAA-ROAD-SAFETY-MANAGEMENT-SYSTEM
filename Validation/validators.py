
accident_types=[
    "HEAD ON COLLISION",
    "MOTORCYCLE ACCIDENT",
    "PEDESTRIAN ACCIDENT",
    "LOSS OF CONTROL",
    "HIT & RUN",
]
def validate_cause_code(cause_code):
    if cause_code is None or cause_code==" " or cause_code=="":
        return False
    return True
def validate_required_fields(time,date,county,road,base,place,accident_info,fatalities,victim,cause_code):
    incident= { 
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
    if incident["road"]==" "or incident["road"]=="":
        return False
    elif incident["county"]==" "or incident["county"]=="":
        return False
    elif incident["cause_code"]==" "or incident["cause_code"]=="":
        return False
    elif incident["victim"]==" "or incident["victim"]=="":
        return False
    elif incident["accident_info"]==" "or incident["accident_info"]=="":
        return False
    elif incident["fatalities"]==" "or incident["fatalities"]=="":
        return False
    elif incident["time"]==" "or incident["time"]=="":
        return False
    elif incident["base"]==" "or incident["base"]=="":
        return False
    elif incident["place"]==" "or incident["place"]=="":
        return False
    else:
        return True
def validate_date(date):
    if len(date)!=10:
        return  False
    if date[2]!="/" or date[5]!="/":
        return False
    return True
def validate_time(time):
    if len(time)!=4:
        return False
    return True
def validate_accident_type(accident_type):
    for item in accident_types:
        if item==accident_type:
            return True
    return False
def validate_counts(fatalities):
    if int(fatalities)<0 or int(fatalities) is None:
        return False
    return True
def validate_duplicate_cause_code(cause_code,incidents):
    for incident in incidents:
        if incident["cause_code"]==cause_code:
            return False
    return True
print(validate_cause_code("C01"))   # True
print(validate_cause_code(""))      # False

print(validate_accident_type("HIT & RUN"))  # True
print(validate_accident_type("FLOODING"))   # False

print(validate_counts("3"))    # True
print(validate_counts("-2"))   # False

