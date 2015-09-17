#!/usr/bin/python -u

import os
import shutil

import jenkins

from argparse import ArgumentParser
from ConfigParser import SafeConfigParser
from distutils.version import LooseVersion

class JenkinsUtility:
    def __init__(self, user, passwd, host="http://localhost:8080"):
        self.server = jenkins.Jenkins(host, username=user, password=passwd)
        self.info = self.server.get_info()
        self.url = self.info["primaryView"]["url"]
        
    def run_cmd(self, cmd):
        print(cmd)
        os.system(cmd)
    
    def download_cli_jar(self):
        # http://[server]/jnlpJars/jenkins-cli.jar
        self.run_cmd("wget {}jnlpJars/jenkins-cli.jar".format(self.url))
    
    def run_jenkins_cli(self, cmd):
        self.run_cmd("java -jar jenkins-cli.jar -s {} {}".format())
        
    def path_exists(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            
    def install_plugin(self, name, version):
        plugin = '"{}@{}"'.format(name, version)
        url = "{}/pluginManager/installNecessaryPlugins".format(self.url)
        request = self.server.Request(url,
                data="<jenkins><install plugin={} /></jenkins>".format(plugin),
                headers={"Content-Type": "text/xml"})
                
        print("Install {}.".format(plugin))
        res = self.server.jenkins_open(request)
    
    def verify_plugins(self, confFile="jenkins.cfg"):
        plugins = {}
        
        print "Installed Plugins:"
        for p in self.server.get_plugins_info():
            print "\t{}: {}".format(p["shortName"], p["version"])
            plugins[p["shortName"]] = p["version"]

        conf = SafeConfigParser()
        conf.read(confFile)

        for p in conf.items("Plugins"):
            installed = plugins.get(p[0])
            # Verify plugin version
            if(installed is not None
                    and LooseVersion(installed) >= LooseVersion(p[1])):
                continue
            
            self.install_plugin(*p)

    def copy_job(self, jobName):
        jobConf = self.server.get_job_config(jobName) # XML to write out
        
        path = "jobs/{}".format(jobName)
        self.path_exists(path)
        
        with open("{}/config.xml".format(path), "w") as f:
            f.write(jobConf)
        
        print("\tCreated {}/config.xml".format(path))
    
    def copy_view(self, viewName):
        viewConf = self.server.get_view_config(viewName) # XML to write out
        # No centralized "views" location
        self.path_exists("views")
        
        with open("views/{}.xml".format(viewName), "w") as f:
            f.write(viewConf)

        print("views/{}.xml created.".format(viewName))

    def copy_scriptler(self):
        """ If security is configured this method requires that the
        Anonymouse group has Overall:Read permissions.
        """
        if os.path.exists("scriptler"):
            shutil.rmtree("scriptler")
        cmd = "git clone {}scriptler.git".format(self.url)
        self.run_cmd(cmd)
        
    def copy_jenkins(self):
        print("Copy Jobs:")
        for job in self.info.get("jobs"):
            self.copy_job(job.get("name"))

        for view in [v for v in self.info.get("views")
                if v.get("name") != "All"]:
            print("Copy view {}.".format(view["name"]))
            self.copy_view(view["name"])
        
        self.copy_scriptler()
    
    def verify_job(self, job, config_xml):
        if self.server.job_exists(job):
            self.server.reconfig_job(job, config_xml)
        else:
            self.server.create_job(job, config_xml)
    
    def verify_view(self, view, config_xml):
        if self.server.view_exists(view):
            self.server.reconfig_view(view, config_xml)
        else:
            self.server.create_view(view, config_xml)
            
    def update_jobs(self):
        print("Updating Jobs:")
        for job in os.listdir("jobs"):
            with open(os.path.join("jobs", job, "config.xml"), "r") as f:
                config_xml = f.read()
            print("\tUpdate/create {} job.".format(job))
            self.verify_job(job, config_xml)
            
    def update_views(self):
        print("Updating Views:")
        for view in os.listdir("views"):
            with open(os.path.join("views", view), "r") as f:
                config_xml = f.read()
            view = view.rstrip(".xml")
            print("\tUpdate/create {} view.".format(view))
            self.verify_view(view, config_xml)
            
    def update_jenkins(self, confFile):
        try:
            version = self.server.get_version()
            print("Jenkins ver: {}".format(version))
        except jenkins.BadHTTPException as e:
            print("Unable to get the Jenkins version.\n\t{}".format(e))
        
        self.verify_plugins(confFile)
        self.update_jobs()
        self.update_views()
            
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
        print("Copy existing Jenkins instance at {}.".format(args.host))
        ju.copy_jenkins()
    elif args.update:
        print("Update existing Jenkins instance at {}.".format(args.host))
        ju.update_jenkins(args.config)
    else:
        parser.print_help()
