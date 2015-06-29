from fabric.api import *
from fabric.contrib.project import rsync_project

env.use_ssh_config = True

env.hosts = ['pirage']

project = 'https://github.com/bj0/pirage.git'

def venv_run(cmd):
    run('source ~/venv/bin/activate && {}'.format(cmd))

@task
def setup_venv():
    with cd('~/pirage'):
        run('virtualenv venv')
        venv_run('pip install -r requirements.txt')

@task
def pirage():
    with cd('~/pirage'):
        venv_run('python run.py')

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
