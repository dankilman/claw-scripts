#! /usr/bin/env claw
########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
############

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

    def __init__(self, source_root):
        handler_configuration = cosmo.handler_configuration
        self.ip = handler_configuration['manager_ip']
        self.user = handler_configuration['manager_user']
        self.hoststring = '{}@{}'.format(self.user, self.ip)
        self.key = os.path.expanduser(handler_configuration['manager_key'])
        self.control_path = cosmo.dir / 'control'
        self.source_root = source_root
        self.ssh = bake(sh.ssh).bake(
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'StrictHostKeyChecking=no',
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
            src='{}/{}/{}'.format(
                self.source_root, package_dir[package], package),
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


def _sync_and_restart_all(source_root):
    with Synchronizer(source_root) as sync:
        sync.sync_and_restart_all()


def _sync_and_restart(env, package, service, source_root):
    with Synchronizer(source_root) as sync:
        sync.sync_and_restart(env, package, service)


def script(source_root='~/dev/cloudify'):
    """
    This sync script will rsync code that lives on your machine to the
    management machine through ssh.
    After doing that, it will restart Cloudify services so they can
    reload code that may have changed during rsync.

    It assumes all of Cloudify Manager dependencies reside within <source_root>
    For the list of dependencies, see the package_dir dict
    """
    _sync_and_restart_all(source_root)
