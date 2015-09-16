#!/usr/bin/python -u

import os
import jenkins
from ConfigParser import SafeConfigParser

def install_plugin(name, version):
    os.system("curl -X POST -d '<jenkins><install plugin=\"%s@%s\" /></jenkins>' --header 'Content-Type: text/xml' http://jenkins:17fd353962ec135cdfd17d85e142605f@localhost:8080/pluginManager/installNecessaryPlugins" % (name, version))

server = jenkins.Jenkins("http://localhost:8080", username="jenkins",
        password="17fd353962ec135cdfd17d85e142605f")
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
    # XXX Need better logic for newer versions of plugins
    if p not in plugins:
        print("Need to install %s ver %s" % (p[0], p[1]))
        install_plugin(*p)
