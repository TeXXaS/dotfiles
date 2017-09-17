#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import psutil
import argparse
try:
    import simplejson as json
    as_json = True
except:
    import pickle
    as_json = False

from commands import getoutput
from collections import namedtuple

# named tuples
Desktop = namedtuple('Desktop', 'desktop active desktopgeometry viewport workingarea')
Size = namedtuple('Size', 'width height')
Rect = namedtuple('Rect', ('left', 'top') + Size._fields)
Window = namedtuple('Window', 'type window desktop pid left top width height classname username title')
WindowWithCmd = namedtuple('WindowWithCmd', Window._fields + ('cmdline', 'state'))
Process = namedtuple('Process', 'pid name username cmdline')

# RegExes used to process wmctrl output
wm_desktop_re = re.compile(
    r'(?P<desktop>[0-9]+)\s+' + 
    r'(?P<active>[\-\*])\s+' +
    r'DG\:\s+' +
    r'(?P<dg_width>[0-9]+)' +
    'x' +
    r'(?P<dg_height>[0-9]+)\s+' +
    r'VP\:\s+' +
    r'(?P<vp>(N/A|[0-9\,]+))\s+' +
    'WA:\s+'
    r'(?P<wa_left>[0-9]+)' +
    ',' +
    r'(?P<wa_top>[0-9]+)\s+'
    r'(?P<wa_width>[0-9]+)' +
    'x' +
    r'(?P<wa_height>[0-9]+)\s+' +                           
    r'(?P<title>.*?)$')
wm_window_re = re.compile(
    r'(?P<win>[A-Za-z0-9]+)\s+' +
    r'(?P<desktop>[\-0-9]+)\s+' +
    r'(?P<pid>[0-9]+)\s+' +
    r'(?P<left>[0-9]+)\s+' +
    r'(?P<top>[0-9]+)\s+' +
    r'(?P<width>[0-9]+)\s+' +
    r'(?P<height>[0-9]+)\s+' +
    r'(?P<class>[A-Za-z0-9\-\.]+)\s+' +
    r'(?P<uname>[a-z0-9]+)\s?' +
    r'(?P<title>.*?)$')

xprop_re = re.compile(
#    r'WM_NAME\((COMPOUND_TEXT|STRING)\) = "(?P<name>.*)"\n' + 
#    r'_NET_WM_PID\(CARDINAL\) = (?P<pid>[0-9]+)\n' +
    r'_NET_WM_STATE\(ATOM\) = (?P<state>.*)')

def list_desktops():
    """Call wmctrl program to fetch all desktops. At the moment not much used."""
    buf = getoutput('wmctrl -d')
    res = []
    for line in buf.split('\n'):
        grps = wm_desktop_re.search(line)
        dg = Size(
            width=int(grps.group('dg_width')), 
            height=int(grps.group('dg_height')))
        wa = Rect(
            left=int(grps.group('wa_left')),
            top=int(grps.group('wa_top')),
            width=int(grps.group('wa_width')),
            height=int(grps.group('wa_height')))
        d = Desktop(
            desktop=int(grps.group('desktop')),
            active=grps.group('active') == '*',
            desktopgeometry=dg,
            viewport=False,
            workingarea=wa)
        res.append(d)
    return res


def list_windows():
    """Call wmctrl program to fetch all windows returned as list of namedtuple - Window"""
    buf = getoutput('wmctrl -lGpx')
    res = []
    for line in buf.split('\n'):
        grps = wm_window_re.search(line)
        w = Window(
            type='Window',
            window=grps.group('win'),
            desktop=int(grps.group('desktop')), 
            pid=int(grps.group('pid')), 
            left=int(grps.group('left')), 
            top=int(grps.group('top')), 
            width=int(grps.group('width')), 
            height=int(grps.group('height')), 
            classname=grps.group('class'), 
            username=grps.group('uname'), 
            title=grps.group('title'))
        res.append(w)
    return res


def apply_window_state(window):
    """Update state of the window. Right now that means only geometry. First param for -e is gravity - 0 means leave as it was."""
    if 'MAXIMIZED_HORZ' in window.state or 'MAXIMIZED_VERT' in window.state:
        remove_maximized(window)
    cmd = 'wmctrl -ir ' + str(window.window) + \
                    ' -e 0,' + str(window.left) + ',' + str(window.top) + ',' + str(window.width) + ',' + str(window.height)
    ##print cmd
    ##res = 
    getoutput(cmd)
    ##print res
    if 'MAXIMIZED_HORZ' in window.state or 'MAXIMIZED_VERT' in window.state:
        restore_maximized(window)


def remove_maximized(window):
    new_state = ['_NET_WM_STATE_' + s for s in window.state if s != 'MAXIMIZED_HORZ' and s != 'MAXIMIZED_VERT' ]
    cmd = "xprop -id " + window.window + " -f _NET_WM_STATE 32a -set _NET_WM_STATE " + ",".join(new_state)
    getoutput(cmd)


def restore_maximized(window):
    new_state = ['_NET_WM_STATE_' + s for s in window.state ]
    cmd = "xprop -id " + window.window + " -f _NET_WM_STATE 32a -set _NET_WM_STATE " + ",".join(new_state)
    getoutput(cmd)
 

def _get_procs():
    """get list of processes, as pid dict. Used internally"""
    res = {}
    for i in psutil.process_iter():
        try:
            psProc = psutil.Process(i.pid)
            proc = Process(
                pid=psProc.pid, 
                name=psProc.name(),
                username=psProc.username(),
                cmdline=psProc.cmdline())
            res[proc.pid] = proc
        except Exception, e:
            print "got error " + str(e) + " while fetching system processes information - " + str(i)
    return res


def _get_xprops(window_id):
    """get xprops for window_id"""
    buf = getoutput('xprop -id ' + window_id + ' _NET_WM_STATE') # WM_NAME _NET_WM_PID
    grps = xprop_re.search(buf)
    if grps.group('state'):
        state_list = [ state.strip().replace('_NET_WM_STATE_', '') for state in grps.group('state').split(',') ]
    else:
        state_list = []
    return { # 'name': grps.group('name'),
             # 'pid': grps.group('pid'),
             'state': state_list }


def list_windows_with_programs():
    """uses list_windows, and adds `ps -eF` information to have full information"""
    procs = _get_procs()
    ##print procs
    windows = list_windows()
    ##print windows
    res = []
    for w in windows:
        p = procs[w.pid]
        if p:
            buf = w._asdict().copy()
            buf.update({'type': 'WindowWithCmd', 'cmdline': p.cmdline})
            xprops = _get_xprops(w.window)
            if xprops:
                buf.update(xprops)
            wp = WindowWithCmd(**buf)
        else:
            wp = WindowWithCmd(*w)
        res.append(wp)
    return res


def store_data(filename):
    """write list of windows into file, as json"""
    data = {
        'windows': list_windows_with_programs(),
        'desktops': list_desktops()}
    if as_json:
        dump = json.dumps(data)
        with open(filename, 'w') as f:
            f.write(dump)
    else:
        pickle.dump(data, open(filename, "wb"))


def to_namedtoople(buf):
    """JSON's loader object hook. Internal function responsible of converting passed dict into proper object. 
    Here it converts json objects into Window / WindowWithCmd named tuples"""
    typ = buf.get('type', None)
    if typ in ['Window', 'WindowWithCmd']:
        if typ == 'Window':
            return Window(**buf)
        elif typ == 'WindowWithCmd':
            return WindowWithCmd(**buf)
    else:
        return buf


def match_window(w, windows):
    for i in windows:
        if w.pid == i.pid and w.window == i.window:
            return i
        elif w.classname == i.classname and (w.pid == i.pid or w.window == i.window or w.title == i.title):
            return i
    return None


def restore_data(filename):
    """load list of windows from file, and apply settings to windows, that are available"""
    if as_json:
        with open(filename, 'r') as f:
            lines = f.readlines()
            dump = '\n'.join(lines)
        data = json.loads(dump, object_hook=to_namedtoople)
    else:
        data = pickle.load(open(filename, "rb"))

    loaded_windows = data['windows']
    active_windows = list_windows_with_programs()
    for w in loaded_windows:
        if w.desktop == -1:
            continue
        aw = match_window(w, active_windows)
        if aw != None and aw.desktop != -1:
            #merge states,
            apply_window_state(w)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--save", dest='save', 
                        help="store current content into passed file")
    parser.add_argument("-l", "--load", dest='load',
                        help="load positions form passed file")

    args = parser.parse_args()
    
    if args.save:
        store_data(args.save)
    elif args.load:
        restore_data(args.save)

    
if __name__ == "__main__":
    main()
