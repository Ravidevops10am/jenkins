FROM jenkins:2.32.1

MAINTAINER Vincent Caboara <vcaboara@gmail.com>

COPY plugins.txt /usr/share/jenkins/ref/
RUN install-plugins.sh $(cat /usr/share/jenkins/ref/plugins.txt)
