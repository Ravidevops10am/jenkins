#!/usr/bin/python -u

import jenkins
from ConfigParser import SafeConfigParser

server = jenkins.Jenkins("http://localhost:8080", username="jenkins",
        password="LeeroyJenkins!")
version = server.get_version()
print "Jenkins version %s" % version

plugins = []
print "Installed Plugins:"
for p in server.get_plugins_info():
    print "\t%s: %s" % (p["shortName"], p["version"])
    plugins.append((p["shortName"], p["version"]))

conf = SafeConfigParser()
conf.read("jenkins.cfg")

for p in conf.items("Plugins"):
    if p not in plugins:
        print("Need to install %s ver %s" % (p[0], p[1]))
