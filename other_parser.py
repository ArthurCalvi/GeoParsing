import re 
import numpy as np
import calendar
from datetime import datetime 

#parse area
def search_for_area(notes):
    try :
        out = re.search(r"\d{2,5}[ ]{0,1}ha{1}", notes.lower())
        out =  int(out.group(0).split('ha')[0]) 
    except:
        out = None
    return out 
    
def parse_area(row):
    if np.isnan(row.area):
        return search_for_area(row.notes)
    else :
        return row.area

#parse date
dmonth = {month.lower(): index for index, month in enumerate(calendar.month_name) if month}

def parse_month(x : str) -> int:
    if not x.isnumeric():
        return dmonth.setdefault(x.lower(), None)
    elif int(x) < 13 and int(x) > 0: 
        return int(x) 
    else :
        return None

def parse_day(x:str)-> int:
    if x.isnumeric():
        return int(x)
    else : 
        return None

def parser_monthandday(x : str, mode='month')-> set:
    if mode == 'month':
        parser = parse_month
    elif mode == 'day':
        parser = parse_day

    out = []
    if isinstance(x, str):
        xlist = x.split(';')
        out = [parser(x.strip()) for x in (xlist[0],xlist[-1]) if x is not None]
        out = set([m for m in out if m is not None]) 

    if len(out)>0:
        return list(out)
    else :
        return [None]

def wrapper(s:str, mode='day'):

    s = parser_monthandday(s, mode=mode)
    if len(s) == 1 and s[0] is None:
        if mode == 'day':
            return [1,28]
        elif mode =='month':
            return [1,12]
    elif len(s) > 1 or (len(s) == 1 and s is not None):
        return [min(x, 28) for x in s]

        

def parse_date(row):
    lday = wrapper(row.day, 'day')
    lmonth = wrapper(row.month, 'month')
    lyear = list(set([row.start_year, row.end_year]))
    if isinstance(row.notes, str):
        if 'winter' in row.notes.lower():
            lmonth = [11,3]
        elif 'summer' in row.notes.lower():
            lmonth = [5,9]
    return datetime(year=lyear[0], month=lmonth[0], day=lday[0]), datetime(year=lyear[-1], month=lmonth[-1], day=lday[-1])

