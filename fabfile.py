from fabric.api import *
from fabric.contrib.project import rsync_project

env.use_ssh_config = True

env.hosts = ['pirage']

project = 'https://github.com/bj0/pirage.git'
remote_venv = '/home/pi/venvs/pirage'
remote_project = '/home/pi/pirage'


def venv_run(cmd):
    """run command inside virtual environment"""
    run('source {}/bin/activate && {}'.format(remote_venv, cmd))


# @task
# def setup_venv():
#    with cd(remote_project):
#        run('virtualenv venv')
#        venv_run('pip install -r requirements.txt')

@task
def pirage():
    with cd(remote_project):
        venv_run('python run.py')


@task
def clone():
    with cd('~/'):
        run('git clone {}'.format(project))


@task
def pull():
    with cd(remote_project):
        run('git pull')


@task
def start():
    sudo('supervicorctl start pirage')


@task
def stop():
    sudo('supervisorctl stop pirage')


@task
def restart():
    sudo("supervisorctl restart pirage")
    # sudo("supervisorctl status")


@task
def status():
    sudo("supervisorctl status")


@task
def update():
    """pull down and restart pirage"""
    pull()
    restart()
