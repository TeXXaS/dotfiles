#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 smarttab

import boto3
import time
from datetime import datetime, timedelta
import os
import json
import argparse
import logging as log
import re

# date regex
# DATE_RE = re.compile(r"(?P<year>[0-9]{4})\-(?P<month>[0-9]{2})\-(?P<day>[0-9]{2}) (?P<hour>[0-9]{2}):[0-9]{2}:[0-9]{2}")

# metadata filename
METADATA_NAME = 'metadata.json'

DELTA_TIME = timedelta(days=60)

client = boto3.client('logs')


def download(deltaTime, log_group_name, dir_name):
    """ download all streams since deltaTime. """

    streams = get_all_logstreams(log_group_name)
    streams = validate_metadata(streams, dir_name)
    # print streams
    timestamp = int(time.mktime((datetime.now() - deltaTime).timetuple()) * 1000)

    # be sure we have directory to store all the stuff
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    for stream in streams:
        # if stream is not marked for update, or is empty - let's skip it
        if not stream.get(u'update', False) \
                or stream.get(u'storedBytes', 0) == 0:
            continue

        get_stream_to_temp(dir_name, log_group_name, stream[u'logStreamName'], timestamp)
        # so log is stored into temp.log
        validate_downloaded_stream(dir_name, log_group_name, stream)

    store_metadata(streams, dir_name)


def get_all_logstreams(log_group_name):
    """fetch all log streams meta data """
    res = []
    response = None
    while True:
        if response is None:
            response = client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True)
        else:
            response = client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                nextToken=response['nextToken'])

        # response is valid, when contains logStreams....
        if u'logStreams' not in response or not response[u'logStreams']:
            break

        # some rewrite, it could be done by removing items as well...
        for i in response.get('logStreams', []):
            buf = {u'firstEventTimestamp': i.get(u'firstEventTimestamp'),
                   u'lastEventTimestamp': i.get(u'lastEventTimestamp'),
                   u'creationTime': i.get(u'creationTime'),

                   u'logStreamName': i.get(u'logStreamName'),
                   u'lastIngestionTime': i.get(u'lastIngestionTime'),
                   u'storedBytes': i.get(u'storedBytes')}
            res.append(buf)
        # after processing all stream entries from last chunk...
        if response is not None and u'nextToken' not in response:
            break
    return res


def get_stream_to_temp(dir_name, log_group_name, log_stream_name, timestamp):
    # stream is located in the file named by ec2, just like in cloud watch
    stream_path = os.path.join(dir_name, 'temp.log')
    if os.path.exists(stream_path):
        os.remove(stream_path)

    out = None
    response = None
    try:
        while True:
            # taking first response, and every next, by forward token
            if response is None:
                response = client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=log_stream_name,
                    startFromHead=True,
                    startTime=timestamp)
            else:
                response = client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=log_stream_name,
                    nextToken=response['nextForwardToken'])

            if u'events' not in response or not response[u'events']:
                break
            # this way file is created only if there are events
            if out is None:
                out = open(stream_path, 'w')

            # with out this split some lines ware putted into one...
            for event in response['events']:
                msgs = event[u'message'].split('\n')
                for msg in msgs:
                    out.write(msg.encode('utf-8').strip() + '\n')

            # so after processing all evens / messages from last chunk stuff is closed
            if response is not None and u'nextForwardToken' not in response:
                break
    finally:
        if out is not None:
            out.close()


def validate_downloaded_stream(dir_name, log_group_name, stream):
    new_path = os.path.join(dir_name, 'temp.log')
    new_size = os.stat(new_path).st_size
    if new_size == 0:
        # if new size is empty - file can be removed
        os.remove(new_path)
        return False
    # prepare list of old files
    files = get_files_for_stream(dir_name, stream[u'logStreamName'])

    max_cnt = None
    for f in files:
        # let's calc max numerator value
        if not f[1] is None:
            if max_cnt is None:
                max_cnt = f[1]
            elif max_cnt < f[1]:
                max_cnt = f[1]
        # validate against particular entry
        if os.stat(os.path.join(dir_name, f[0])) == new_size:
            return True
    # not matching - need to move saved temp.log to better name
    if max_cnt is None:
        os.rename(new_path, os.path.join(dir_name, stream[u'logStreamName'] + '.LOG'))
    else:
        os.rename(new_path, os.path.join(dir_name, stream[u'logStreamName'] + '_' + str(max_cnt+1) + '.LOG'))


def get_files_for_stream(dir_name, log_stream_name):
    """returns list of tuples - name + numerator putted into name """
    filename_re = re.compile(log_stream_name + r"(_(?P<num>[0-9]+))?.log")

    res = []
    for root, dirs, files in os.walk(dir_name, topdown=False):
        for name in files:
            re_group = filename_re.match(name)
            if not re_group is None:
                numerator = int(re_group.group('num')) if re_group.group('num') is not None else 0
                res.append((name, numerator))
    return res


def store_metadata(streams, dir_name):
    """Simple store to JSON file"""
    fp = open(dir_name + '/' + METADATA_NAME, 'w')
    try:
        json.dump(streams, fp)
    finally:
        fp.close()


def read_metadata(dir_name):
    """Simple load from JSON file"""
    metadata_path = dir_name + '/' + METADATA_NAME + '.log'
    if not os.path.exists(metadata_path):
        return []

    fp = open(metadata_path, 'r')
    try:
        return json.load(fp)
    finally:
        fp.close()


def validate_metadata(streams, dir_name):
    """
    Check which streams are new, prepare list with all streams - from file, and available.
    Mark streams that need update
    """
    res = []
    old_metadata = read_metadata(dir_name)
    old_streams = {}
    for i in old_metadata:
        old_streams[i[u'logStreamName']] = i

    for stream in streams:
        old = old_streams.pop(stream[u'logStreamName'], None)

        if old is None \
                or old[u'firstEventTimestamp'] != stream[u'firstEventTimestamp'] \
                or old[u'lastEventTimestamp'] < stream[u'lastEventTimestamp'] \
                or old[u'creationTime'] != stream[u'creationTime'] \
                or old[u'logStreamName'] != stream[u'logStreamName'] \
                or old[u'lastIngestionTime'] < stream[u'lastIngestionTime'] \
                or old[u'storedBytes'] < stream[u'storedBytes']:
            stream[u'update'] = True
            res.append(stream)
        else:
            stream[u'update'] = False
            res.append(stream)
    res += old_streams.values()
    return res


def parse_args():
    """ parse CLI input, and returns tuple of passed parameters """
    parser = argparse.ArgumentParser(
        __file__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Script used to fetch CloudWatch logs.")
    parser.add_argument("-o", "--output-dir", action='store',
                        help="output directory")
    parser.add_argument("-g", "--group-name", action='store',
                        help="log group name.")
    parser.add_argument("-d", "--debug", action='store_const', const=True,
                        help="all debug stuff - on screen")
    parser.add_argument("-n", "--dry-run", action='store_const', const=True,
                        help="do not do anything - just printout what should be executed")
    args = parser.parse_args()
    return args.output_dir, args.group_name, args.debug, args.dry_run


def main():
    output_dir, group_name, debug, dryRun = parse_args()

    if debug:
        log.basicConfig(format="%(levelname)s: %(message)s", level=log.DEBUG)
        log.info("started.")
    else:
        log.basicConfig(format="%(levelname)s: %(message)s")

    deltaTime = timedelta(days=60)
    download(deltaTime, group_name, output_dir)


if __name__ == "__main__":
    main()
