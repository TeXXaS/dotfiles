#!/usr/bin/env python3
import boto3

eb_client = boto3.client('elasticbeanstalk')

EXPECTED_COUNT = 200

app_response = eb_client.describe_applications()
for app in app_response['Applications']:
    versions_count = len(app.get('Versions', []))
    if versions_count < EXPECTED_COUNT:
        print(F'{app["ApplicationName"]} skipping - found {versions_count} versions, which is less then {EXPECTED_COUNT}')
        continue

    vers_response = eb_client.describe_application_versions(ApplicationName=app['ApplicationName'])
    versions = sorted(vers_response.get('ApplicationVersions', []), key=lambda v: v['DateCreated'])
    versions = versions[:EXPECTED_COUNT]
    print(F'{app["ApplicationName"]} removing - {versions_count} versions')
    for ver in versions:
        print (F'removing - {VersionLabel} - {DateCreated} ')
        response = eb_client.delete_application_version(
            ApplicationName=ver['ApplicationName'],
            VersionLabel=ver['VersionLabel'],
            DeleteSourceBundle=True
        )

