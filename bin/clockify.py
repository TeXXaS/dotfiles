#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 smarttab

import click
import requests
import json

from isodate import parse_datetime, parse_duration
from passpy import Store

STORE_PATH = "accounting/clockify"

#colors by https://pypi.org/project/colored/


class Clockify:
    def __init__(self, config=None):
        if config is None:
            self.store = Store()
            ctx = self.store.get_key(STORE_PATH)
            self.config = json.loads(ctx)
        else:
            self.config = config
        self.__headers()

    def __headers(self):
        self.headers = {
            'content-type': 'application/json',
            'X-Api-Key': self.config["api_key"]
        }

    def get_user(self):
        url = 'https://api.clockify.me/api/v1/user'
        raw = requests.get(url, headers=self.headers)
        if raw.status_code != 200:
            raise Exception("Error " + str(raw.status_code) + " while talking to " + url)
        res = json.loads(raw.text)
        if self.config['user_id'] is None:
            self.config['user_id'] = res['id']
        return res

    def get_workspaces(self):
        raw = requests.get('https://api.clockify.me/api/v1/workspaces', headers=self.headers)
        buf = json.loads(raw.text)
        res = {}
        for row in buf:
            res[row['id']] = row
        return res

    def get_tags(self, workspace_id):
        raw = requests.get(
            'https://api.clockify.me/api/v1//workspaces/{workspaceId}/tags'.format(workspaceId=workspace_id),
            headers=self.headers)
        buf = json.loads(raw.text)
        res = {}
        for row in buf:
            res[row['id']] = row
        return res

    def get_time_entries(self):
        self.get_user()
        user_id = self.config['user_id']
        workspace_id = self.config['workspace_id']

        url = 'https://api.clockify.me/api/v1/workspaces/{workspaceId}/user/{userId}/time-entries'.format(userId=user_id,
                                                                                            workspaceId=workspace_id)
        raw = requests.get(url, headers=self.headers)
        if raw.status_code != 200:
            raise Exception("Error " + str(raw.status_code) + " while talking to " + url)
        buf = json.loads(raw.text)
        res = []
        for row in buf:
            res.append({
                'id': row['id'],
                'userId': row['userId'],
                'projectId': row['projectId'],
                'workspaceId': row['workspaceId'],
                'tagIds': row['tagIds'],
                'description': row['description'],
                'startTime': parse_datetime(row['timeInterval']['start']),
                'endTime': parse_datetime(row['timeInterval']['end']),
                'duration': parse_duration(row['timeInterval']['duration']),
            })
        return res

    def print_month_stats(self, entries):
        # group days
        days = {}
        for entry in entries:
            dt = entry['startTime'].date()
            if not dt in days.keys():
                day = entry['duration']
            else:
                day = day + entry['duration']
            days[dt] = day

        row0 = ''
        row1 = ''
        w = None
        m = None
        keys = list(days.keys())
        keys.sort()
        for k in keys:
            v = days[k]
            if m is None:
                print(k.strftime('%b'))
                m = k.month
            elif m != k.month:
                print(row0)
                print(row1)
                row0 = ''
                row1 = ''
                print(k.strftime('%b'))
                m = k.month
                w = None

            if row0 != '':
                if not w is None and k.weekday() < w:
                    print(row0)
                    print(row1)
                    row0 = ''
                    row1 = ''
                w = k.weekday()
            if row0 == '':
                for _ in range(k.weekday()):
                    row0 += '    '
                    row1 += '    '
            row0 += ' ' + k.strftime('%d') + ' '
            row1 += ' ' + str(v.seconds / 60 / 60)
        if row0 != '':
            print(row0)
            print(row1)

@click.group()
def cli():
    pass


@cli.command(help="Create brand new configuration")
@click.argument('api_key')  # , help="Key provided by Clockify"
@click.argument('default_workspace_id')  # , help="Default workspace id"
@click.argument('default_project_id', required=False)  # , help="Default project id"
@click.argument('default_tag_ids', nargs=-1, required=False)  # , help="Default tag ifs"
def init(api_key, default_workspace_id, default_project_id, default_tag_ids):
    config = {
        'api_key': api_key,
        "user_id": None,
        "workspace_id": default_workspace_id,
        "project_id": default_project_id,
        "tag_ids": default_tag_ids
    }
    store = Store()
    c = Clockify(config)
    c.get_user()
    ctx = json.dumps(c.config)
    store.set_key(STORE_PATH, ctx, force=True)


@cli.command(help="Fetch user information")
def user():
    c = Clockify()
    print(c.get_user())


@cli.command(help="Print report")
def report():
    c = Clockify()
    c.get_user()
    entries = c.get_time_entries()
    c.print_month_stats(entries)


cli.add_command(init)
cli.add_command(user)
cli.add_command(report)

if __name__ == '__main__':
    cli()
