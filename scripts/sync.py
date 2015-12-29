#! /usr/bin/env claw

import os
import time

import sh

from claw import cosmo
from claw.commands import bake


package_dir = {
    'amqp_influxdb': 'cloudify-amqp-influxdb',
    'cloudify': 'cloudify-plugins-common',
    'cloudify_agent': 'cloudify-agent',
    'cloudify_handler': 'cloudify-diamond-plugin',
    'cloudify_rest_client': 'cloudify-rest-client',
    'diamond_agent': 'cloudify-diamond-plugin',
    'dsl_parser': 'cloudify-dsl-parser',
    'manager_rest': 'cloudify-manager/rest-service',
    'plugin_installer': 'cloudify-agent',
    'script_runner': 'cloudify-script-plugin',
    'windows_agent_installer': 'cloudify-agent',
    'windows_plugin_installer': 'cloudify-agent',
    'worker_installer': 'cloudify-agent',
    'cloudify_system_workflows': 'cloudify-manager/workflows'

}

env_packages = {
    'amqpinflux': [
        'amqp_influxdb'
    ],
    'manager': [
        'cloudify',
        'cloudify_agent',
        'cloudify_handler',
        'cloudify_rest_client',
        'diamond_agent',
        'dsl_parser',
        'manager_rest',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
    ],
    'mgmtworker': [
        'cloudify',
        'cloudify_agent',
        'cloudify_handler',
        'cloudify_system_workflows',
        'cloudify_rest_client',
        'diamond_agent',
        'dsl_parser',
        'plugin_installer',
        'script_runner',
        'windows_agent_installer',
        'windows_plugin_installer',
        'worker_installer',
    ]
}


class Synchronizer(object):

    def __init__(self):
        handler_configuration = cosmo.handler_configuration
        self.ip = handler_configuration['manager_ip']
        self.user = handler_configuration['manager_user']
        self.hoststring = '{}@{}'.format(self.user, self.ip)
        self.key = os.path.expanduser(handler_configuration['manager_key'])
        self.control_path = cosmo.dir / 'control'
        self.ssh = bake(sh.ssh).bake(
            '-i', self.key,
            '-o', 'ControlPath={}'.format(self.control_path))
        self.ssh('-nNf',
                 '-o', 'ControlMaster=yes',
                 self.hoststring)
        # Unfortunate sleep here.
        # It blocks if we do .wait() in the previous
        # ssh command which I can't figure out why
        time.sleep(3)

    def close(self):
        self.ssh('-O', 'exit',
                 self.hoststring).wait()

    def _sync(self, src, dest):
        src = os.path.expanduser(src)
        rsync = bake(sh.rsync).bake(
            '--exclude', '.git',
            '--exclude', 'tests',
            '--exclude', 'test',
            verbose=True,
            recursive=True,
            compress=True,
            progress=True,
            delete=True,
            stats=True,
            rsync_path='sudo rsync',
            rsh='ssh -i {} -o ControlPath={}'.format(self.key,
                                                     self.control_path))
        rsync('{}/'.format(src),
              '{}:{}'.format(self.hoststring, dest)).wait()

    def _sync_package(self, env, package):
        self._sync(
            src='~/dev/cloudify/{}/{}'.format(
                package_dir[package], package),
            dest='/opt/{}/env/lib/python2.7/site-packages/{}'.format(
                env, package))

    def _sync_packages(self):
        for env, packages in env_packages.items():
            for package in packages:
                self._sync_package(env, package)

    def _restart_service(self, service):
        with cosmo.ssh() as ssh:
            ssh.sudo('systemctl restart cloudify-{}'.format(service))

    def _restart_services(self):
        for service in ['amqpinflux', 'mgmtworker', 'restservice']:
            self._restart_service(service)

    def sync_and_restart(self, env, package, service):
        self._sync_package(env, package)
        self._restart_service(service)

    def sync_and_restart_all(self):
        self._sync_packages()
        self._restart_services()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _sync_and_restart_all():
    with Synchronizer() as sync:
        sync.sync_and_restart_all()


def _sync_and_restart(env, package, service):
    with Synchronizer() as sync:
        sync.sync_and_restart(env, package, service)


script = _sync_and_restart_all
rest_service = lambda: _sync_and_restart('manager',
                                         'manager_rest',
                                         'restservice')
