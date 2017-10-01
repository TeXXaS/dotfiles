#!/usr/bin/env python3

from os import path, walk
from fnmatch import fnmatch
from datetime import datetime
from openpyxl import load_workbook
from itertools import dropwhile, takewhile
import pprint


ROOT = "/home/mzaborow/Documents/Rekrutacje/jlabs"
FILE_PATTERN = "*_java_arkusz.xlsx"
MONTHLY_PATTERN = path.join(ROOT, "{0}_{1:02d}_m_zaborowski_raport.xlsx")


def iterate_over_files():
    """Iterates over files - starts from ROOT, and goes over all subdirectories.
    Only directories with no subdirectories, are taken, and file name must follow FILE_PATTERN"""
    for dir, subdirs, files in walk(ROOT):
        if subdirs:
            continue
        for name in files:
            if fnmatch(name, FILE_PATTERN):
                yield path.join(dir, name)


def get_version(ws):
    """takes worksheet and finds last row in first column, there is version of test sheet there"""
    idx = 200
    while ws['A' + str(idx)].value in [None, '', 'None']:
        idx -=1
    return ws['A' + str(idx)].value


def is_valid(data):
    """Checks if passed data is valid. In practice it means that all entries are filled"""
    if data is None or not isinstance(data, dict):
        return False
    for buf in data.values():
        if buf in [None, '', 'None']:
            return False
#        if  isinstance(1.0, float)
    known = ['date', 'name', 'avg', 'base', 'java', 'frameworks', 'version']
    return len(set(known).intersection(data.keys())) == len(known)
#TODO check elements' types


def extract_data_for_16_05_2017(ws):
    buf = ws['B2'].value
    if buf is None:
        return None  # different format
    if not isinstance(buf, datetime):
        try:
            buf = datetime.strptime(ws['B2'].value, '%Y.%m.%d')
        except ValueError:
            buf = datetime.strptime(ws['B2'].value, '%d.%m.%Y')
    return {'date': buf,
            'name': ws['B4'].value,
            'avg': ws['B9'].value,
            'base': ws['B11'].value,
            'java': ws['B21'].value,
            'frameworks': ws['B29'].value,
            'version': get_version(ws)}


def extract_data_for_01_03_2017(ws):
    buf = ws['B2'].value
    if buf is None:
        return None  # different format
    if not isinstance(buf, datetime):
        try:
            buf = datetime.strptime(ws['B2'].value, '%Y.%m.%d')
        except ValueError:
            buf = datetime.strptime(ws['B2'].value, '%d.%m.%Y')
    return {'date': buf,
            'name': ws['B4'].value,
            'avg': ws['B10'].value,
            'base': ws['B12'].value,
            'java': ws['B22'].value,
            'frameworks': ws['B30'].value,
            'version': get_version(ws)}


def extract_data_for_very_old(ws):
    if not get_version(ws) == 'Uwagi (inne informacje warte odnotowania)':
        return None
    buf = ws['B2'].value
    if buf is None:
        return None  # old format
    if not isinstance(buf, datetime):
        try:
            buf = datetime.strptime(ws['B2'].value, '%Y.%m.%d')
        except ValueError:
            buf = datetime.strptime(ws['B2'].value, '%d.%m.%Y')
    return {'date': buf,
            'name': ws['B4'].value,
            'avg': ws['B10'].value,
            'base': ws['B12'].value,
            'java': ws['B23'].value,
            'frameworks': ws['B33'].value,
            'version': get_version(ws)}


def extract_data(file_name):
    """From file, based on passed file name, extracts data - as dictionary"""
    wb = load_workbook(filename=file_name, data_only=True)
    ws = wb.active

    res = extract_data_for_16_05_2017(ws)
    if not is_valid(res):
        res = extract_data_for_01_03_2017(ws)
    if not is_valid(res):
        res = extract_data_for_very_old(ws)
    return res


def prepare_monthy_reports(entries):
    all_months = [ (entry['date'].year,entry['date'].month) for entry in entries]
    months = set(all_months)
    res = []
    for month in months:
        file_name = MONTHLY_PATTERN.format(*month)
        if path.isfile(file_name):
            print (file_name)
            # file exists so it should be opened
            wb = load_workbook(filename=file_name, data_only=True)
            ws = wb.active
            rep = {
                "name": file_name,
                "lines": []
            }
            res.append(rep)
            idx = 2
            while not ws['B' + str(idx)].value in [None, '', 'None']:
                ln = {'no': ws['A' + str(idx)].value,
                      'date': ws['B' + str(idx)].value,
                      'recruter': ws['C' + str(idx)].value,
                      'candidate_fname': ws['D' + str(idx)].value,
                      'candidate_lname': ws['E' + str(idx)].value,
                      'technology': ws['F' + str(idx)].value,
                      'type': ws['G' + str(idx)].value,
                      'avg': ws['H' + str(idx)].value,
                      'base': ws['I' + str(idx)].value,
                      'java': ws['J' + str(idx)].value,
                      'frameworks': ws['K' + str(idx)].value}
                rep['lines'].append(ln)
                idx += 1
        else:
            # no file - let's create one - easy case
            print ("file not exists =->" + file_name)
    return res


def update_reports():
    pass


pp = pprint.PrettyPrinter(indent=2)
# extract data
entries = [extract_data(file_name) for file_name in iterate_over_files()]
# filter out empty entries
entries = [en for en in entries if not en is None]
# pp.pprint(entries)
data = prepare_monthy_reports(entries)
for buf in data:
    for line in buf['lines']:
        # print(line)
        print("  {no:02d} {date:%Y.%m.%d} {recruter:20s} {candidate_fname:10s} {candidate_lname:12s} - {technology} {type:4s}: {avg: 2.2f} {base: 2.2f} {java: 2.2f} {frameworks: 2.2f}".format(**line), flush=True)
# filter for current month, and sort by date
now = datetime.now()
entries = [e for e in entries if e['date'].year == now.year ]
entries = sorted(entries, key=lambda e: e['date'])
# printout sample report
for buf in entries:
    print("{date:%Y.%m.%d} {name:20s} {avg: 2.2f} {base: 2.2f} {java: 2.2f} {frameworks: 2.2f}".format(**buf), flush=True)
