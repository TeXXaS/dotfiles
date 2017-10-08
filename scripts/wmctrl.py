#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO - use structured logs instead of regex

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
WindowWithCmd = namedtuple('WindowWithCmd', Window._fields + ('cmdline',))
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
    r'(?P<wa_left>[\-0-9]+)' +
    ',' +
    r'(?P<wa_top>[\-0-9]+)\s+'
    r'(?P<wa_width>[0-9]+)' +
    'x' +
    r'(?P<wa_height>[0-9]+)\s+' +
    r'(?P<title>.*?)$')
wm_window_re = re.compile(
    r'(?P<win>[A-Za-z0-9]+)\s+' +
    r'(?P<desktop>[\-0-9]+)\s+' +
    r'(?P<pid>[0-9]+)\s+' +
    r'(?P<left>[\-0-9]+)\s+' +
    r'(?P<top>[\-0-9]+)\s+' +
    r'(?P<width>[0-9]+)\s+' +
    r'(?P<height>[0-9]+)\s+' +
    r'(?P<class>[A-Za-z0-9\-\.\_]+)\s+' +
    r'(?P<uname>[a-z0-9\-\_]+)\s?' +
    r'(?P<title>.*?)$')


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
        if grps is None:
            print "not matched " + line
            continue
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


def apply_window_state(stored, active):
    """Update state of the window. Right now that means only geometry. First param for -e is gravity - 0 means leave as it was."""
    print 'active: ' + active.classname + ' ' + active.title
    print ' -> ' + stored.classname + ' ' + stored.title
    cmd = 'wmctrl -ir ' + str(active.window) + \
          ' -e 0,' + str(stored.left) + ',' + str(stored.top) + ',' + str(stored.width) + ',' + str(stored.height)
    print cmd
    res = getoutput(cmd)
    print res


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


def match_window(active, loaded_windows):
    for loaded in loaded_windows:
        if active.pid == loaded.pid and active.window == loaded.window:
            ## print " pid and window match " + str(active) + "\n with " + str(active)
            return loaded
        elif (active.cmdline == loaded.cmdline or active.pid == loaded.pid or active.window == loaded.window) \
                and (active.classname == loaded.classname or active.title == loaded.title):
            ## print " matched " + str(active) + "\n with " + str(active)
            return loaded
        elif (active.cmdline[0] == loaded.cmdline[0]):
            ## print " matched II " + str(active) + "\n with " + str(active)
            return loaded

    print " not matched " + str(active)
    return None


def move_to_bigger_screen(window):
    """Update state of the window, by moving it to second screen."""
    if (window.left >= 1920):
        return
    cmd = 'wmctrl -ir ' + str(window.window) + \
          ' -e 0,' + str(window.left + 1920) + ',' + str(window.top) + ',' + str(window.width) + ',' + str(window.height)
    print cmd
    res = getoutput(cmd)
    print res


def restore_data(filename, setup):
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
    print active_windows
    for aw in active_windows:
        if aw.classname in ['xfce4-panel.Xfce4-panel', 'xfdesktop.Xfdesktop']:
            continue
        loaded = match_window(aw, loaded_windows)
        if loaded != None and loaded.desktop != -1:
            # merge states,
            apply_window_state(loaded, aw)
            continue
        if setup == 'multi':
            move_to_bigger_screen(aw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--save", dest='save',
                        help="store current content into passed file")
    parser.add_argument("-l", "--load", dest='load',
                        help="load positions form passed file")
    parser.add_argument("single", dest="setup",
                        help="is this single monitor setting")
    parser.add_argument("multi", dest="setup",
                        help="is this multi monitor setting")
    args = parser.parse_args()
    ## print args

    if args.save:
        print "storing data in " + args.save
        store_data(args.save)
    elif args.load:
        print "loading data from " + args.load
        restore_data(args.load, args.setup)


if __name__ == "__main__":
    main()
