from fabric.api import *
from fabric.contrib.project import rsync_project

env.use_ssh_config = True

env.hosts = ['pirage']

project = 'https://github.com/bj0/pirage.git'

@task
def clone():
    with cd('~/'):
        run('git clone {}'.format(project))

@task
def update():
    with cd('~/pirage'):
        run('git pull')

@task
def restart():
    sudo("supervisorctl restart pirage")
    sudo("supervisorctl status")

@task
def check():
    sudo("supervisorctl status")
