#!/usr/bin/python -u

import jenkins

server = jenkins.Jenkins("http://localhost:8080", username="jenkins",
        password="LeeroyJenkins!")
version = server.get_version()
print "Jenkins version %s" % version

plugins = server.get_plugins_info()
print "Plugins:"
for p in plugins:
    print "\t%s" % p["shortName"]
