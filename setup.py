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
        self.run_cmd("java -jar jenkins-cli.jar -s {} {}".format(self.url, cmd))
        
    def restart_jenkins(self):
        print("Restarting Jenkins.")
        self.run_jenkins_cli("safe-restart")
            
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

        print("\tCreated views/{}.xml".format(viewName))

    def copy_scriptler(self):
        """ If security is configured this method requires that the
        Anonymouse group has Overall:Read permissions.
        """
        if os.path.exists("scriptler"):
            shutil.rmtree("scriptler")
        cmd = "git clone {}scriptler.git".format(self.url)
        self.run_cmd(cmd)
        
    def copy_jenkins(self, jenkinsPath):
        print("Copy Jenkins config.xml...")
        host = self.url.split("//")[1].split(":")[0]
        self.run_cmd("scp {}:{}/config.xml .".format(host, jenkinsPath))
        
        print("Copy Jobs:")
        for job in self.info.get("jobs"):
            self.copy_job(job.get("name"))
        
        print("Copy Views:")
        for view in [v for v in self.info.get("views")
                if v.get("name") != "All"]:
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
            
    def update_jenkins(self, confFile, jenkinsPath):
        try:
            version = self.server.get_version()
            print("Jenkins ver: {}".format(version))
        except jenkins.BadHTTPException as e:
            print("Unable to get the Jenkins version.\n\t{}".format(e))
        
        self.verify_plugins(confFile)
        self.update_jobs()
        self.update_views()
        
        # XXX Verify local jenkins/config.xml contains global properties (from jenkins.cfg)
        # merge with remote jenkins/config.xml?
        # print("Update Jenkins config.xml...")
        # host = self.url.split("//")[1].split(":")[0]
        # self.run_cmd("scp config.xml {}:".format(host))
        # self.run_cmd("ssh {} 'sudo mv config.xml {}'".format(host, jenkinsPath))
        
        print("Update Scriptler...")
        self.run_cmd("scp scriptler/* {}:scriptler".format(host))
        self.run_cmd("ssh {} 'sudo mv scriptler/* {}/scriptler/scripts'".format(
            host, jenkinsPath))
        
        self.restart_jenkins()
            
if __name__ == "__main__":
    description = ["Utility to backup and setup/update Jenkins.",
        "Recommend running ssh-copy-id [jenkinshost] before executing this",
            "script to alleviate password prompts.",
        "In order to successfully update the jenkins/config.xml file",
        "the user must have sudo permissions on the Jenkins instance."]
    parser = ArgumentParser(description=" ".join(description))
    
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
    parser.add_argument("-p", "--jenkinsPath", action="store",
            default="/var/lib/jenkins",
            help="Path to the Jenkins installation, default /var/lib/jenkins.")
    parser.add_argument("--config", action="store", default="jenkins.cfg",
        help="Location of the config file, default is 'jenkins.cfg'.")
    
    args = parser.parse_args()
    ju = JenkinsUtility(args.username, args.password, args.host)
    
    if(args.copy and args.jenkinsPath):
        print("Copy existing Jenkins instance at {}.".format(args.host))
        ju.copy_jenkins(args.jenkinsPath)
    elif(args.update and args.jenkinsPath):
        print("Update existing Jenkins instance at {}.".format(args.host))
        ju.update_jenkins(args.config, args.jenkinsPath)
    else:
        parser.print_help()
