#!/usr/bin/python

from botocore.session import Session

import re
import os
import sys
import botocore
import argparse
import jinja2


def striphtml(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)


def convert(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

parser = argparse.ArgumentParser(description="Generate aws stackstorm actions")
parser.add_argument('-d', '--outputdir', default="actions", help="base output directory")
parser.add_argument('-s', '--service', default=None, help="service to generate actions for (eg s3)")
args = parser.parse_args()

outputdir = args.outputdir
myservice = args.service

# print "outputdir: %s" % outputdir
# print "myservice: %s" % myservice

try:
    os.stat(outputdir)
except:
    os.mkdir(outputdir)

templateLoader = jinja2.FileSystemLoader(searchpath="templates")
templateEnv = jinja2.Environment(loader=templateLoader)

session = Session()

try:
    mysrv = session.get_service_model(myservice)
except botocore.exceptions.UnknownServiceError as e:
    print "\n%s\n" % e
    sys.exit(1)


for op in mysrv.operation_names:

    allvars = {}
    allvars['paramsreq'] = []
    allvars['params'] = []

    model = mysrv.operation_model(op)

    op = convert(op)

    print op
    allvars['action'] = op
    allvars['name'] = myservice + "_" + op
    allvars['service'] = myservice

    if model.input_shape is None:
        continue

    members = model.input_shape.members

    smodel = model.service_model

    # print smodel._shape_resolver

    smembers = model.input_shape._shape_model['members']
    for sname, sdata in smembers.items():
        tmp = {}
        stype = smodel._shape_resolver._shape_map[sdata['shape']]['type']
        # blob defined in boto as bytes or seekable file-like object - not supported here
        if stype == "blob":
            stype = "string"
        if stype == "long":
            stype = "integer"
        if stype == "structure":
            stype = "object"
        if stype == "map":
            stype = "object"
        if stype == "list":
            stype = "array"
        if stype == "timestamp":
            stype = "string"
        tmp['name'] = sname
        tmp['type'] = stype
        if 'documentation' in sdata:
            tmp['description'] = striphtml(sdata['documentation'].rstrip().replace('"', "'"))
        else:
            tmp['description'] = ''

        if sname in model.input_shape.required_members:
            allvars['paramsreq'].append(tmp)
        else:
            allvars['params'].append(tmp)

    actionyaml = outputdir + "/" + allvars['name'] + ".yaml"
    y = open(actionyaml, 'w')

    template = templateEnv.get_template('action_template.yaml.jinja')
    outputText = template.render(allvars).encode('utf8')  # pylint: disable=no-member
    y.write(outputText)

    y.close()
