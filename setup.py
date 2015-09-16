#!/usr/bin/python -u

import os
import jenkins

from argparse import ArgumentParser
from ConfigParser import SafeConfigParser
from distutils.version import LooseVersion

class JenkinsUtility:
    def __init__(self, user, passwd, host="http://localhost:8080"):
        self.user = user
        self.passwd = passwd
        self.host = host
        self.server = jenkins.Jenkins(self.host, username=self.user,
                password=self.passwd)
        self.info = self.server.get_info()
        
    def path_exists(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            
    def install_plugin(self, name, version):
        plugin = '"%s@%s"' % (name, version)
        url = "%s/pluginManager/installNecessaryPlugins" % self.info["primaryView"]["url"]
        request = jenkins.Request(url,
                data="<jenkins><install plugin=%s /></jenkins>" % plugin,
                headers={"Content-Type": "text/xml",
                    "Authorization": jenkins.auth_headers(self.user, self.passwd)})
                
        print("Install %s." % plugin)
        res = self.server.jenkins_open(request)
    
    def verify_plugins(self, confFile="jenkins.cfg"):
        plugins = {}
        
        print "Installed Plugins:"
        for p in self.server.get_plugins_info():
            print "\t%s: %s" % (p["shortName"], p["version"])
            plugins[p["shortName"]] = p["version"]

        conf = SafeConfigParser()
        conf.read(confFile)

        for p in conf.items("Plugins"):
            installed = plugins.get(p[0])
            if installed is not None:
                # Verify plugin version
                if LooseVersion(installed) >= LooseVersion(p[1]):
                    continue
            
            self.install_plugin(*p)

    def copy_job(self, jobName):
        jobConf = self.server.get_job_config(jobName) # XML to write out
        
        path = "jobs/%s" % jobName
        self.path_exists(path)
        
        with open("%s/config.xml" % path, "w") as f:
            f.write(jobConf)
        
        print("%s/config.xml created." % path)
    
    def copy_view(self, viewName):
        viewConf = self.server.get_view_config(viewName) # XML to write out
        # No centralized "views" location
        self.path_exists("views")
        
        with open("views/%s.xml" % viewName, "w") as f:
            f.write(viewConf)

        print("views/%s.xml created." % viewName)
        
    def copy_jenkins(self):
        for job in self.info.get("jobs"):
            print("Copy job %s." % job.get("name"))
            self.copy_job(job.get("name"))

        for view in [v for v in self.info.get("views")
                if v.get("name") != "All"]:
            print("Copy view %s." % view.get("name"))
            self.copy_view(view.get("name"))
    
    def update_jenkins(self, confFile):
        version = self.server.get_version()
        print("Jenkins ver: %s" % version)
        
        self.verify_plugins(confFile)
            
if __name__ == "__main__":
    parser = ArgumentParser(description="Utility to backup and setup jenkins.")
    parser.add_argument("username", action="store",
        help="Jenkins username for authentication.")
    parser.add_argument("password", action="store",
        help="Password or API Token for authentication.")
    parser.add_argument("--host", action="store",
        default="http://localhost:8080",
        help="Jenkins host, default is 'http://localhost:8080'.")
    parser.add_argument("-c", "--copy", action="store_true", default=False,
        help="Back up the existing local Jenkins instance.")
    parser.add_argument("-u", "--update", action="store_true", default=False,
        help="Update the local Jenkins instance from pwd.")
    parser.add_argument("--config", action="store", default="jenkins.cfg",
        help="Location of the config file, default is 'jenkins.cfg'.")
    
    args = parser.parse_args()
    ju = JenkinsUtility(args.username, args.password, args.host)
    
    if args.copy:
        print("Copy existing Jenkins instance at %s." % args.host)
        ju.copy_jenkins()
    elif args.update:
        print("Update existing Jenkins instance at %s." % args.host)
        ju.update_jenkins(args.config)
    else:
        parser.print_help()
