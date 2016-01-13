#! /usr/bin/env claw
########
# Copyright (c) 2016 GigaSpaces Technologies Ltd. All rights reserved
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

import argh
import os
import psutil
import shlex

from random import choice
from fabric import colors
from fabric import context_managers as fabric_ctx
import fabric.contrib.files as fab_files
from time import sleep
from claw import cosmo

PYCHARM_PACKAGE_URL = \
    'https://s3.eu-central-1.amazonaws.com/' + \
    'cloudify-dev/remote-debug/pycharm-debug.egg'
REST_SERVICE_ENV_FILE_PATH = '/etc/sysconfig/cloudify-restservice'
MANAGER_EASY_INSTALL_PATH = '/opt/manager/env/bin/easy_install'
DEBUGGER_ENV_VAR = 'DEBUG_REST_SERVICE'

logger = None


class reverse_tunnel(object):
    '''SSH reverse tunnel
    '''
    def __init__(self, port, host_address, key_path):
        self.port = port
        self.host_address = host_address
        self.key_path = key_path

    def open(self):
        ssh_cmd = \
            'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' +\
            '-qNT -i {key} -R{port}:localhost:{port} {host_address}'.format(
                key=self.key_path,
                port=self.port,
                host_address=self.host_address
            )
        self.process = psutil.Popen(shlex.split(ssh_cmd))

    def close(self):
        try:
            self.process.kill()
        except psutil.NoSuchProcess:
            pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def is_alive(self):
        self.process.poll()
        return self.process.returncode is None


def _is_listening_to_port(port, connection_type='tcp'):
    """
    Check if a port is being listened to
    :param port: port # to check
    :param type: connection types to scan. see psutil docs for options
    """
    conns = psutil.net_connections(connection_type)
    return any([(conn.laddr[1] == port and conn.status == 'LISTEN')
                for conn in conns])


def _wait_for_port(port):
    is_port_ready = False
    try:
        while not is_port_ready:
            is_port_ready = _is_listening_to_port(port)
            sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        return is_port_ready


def _inject_env_var(ssh, port):
    if fab_files.contains(REST_SERVICE_ENV_FILE_PATH, DEBUGGER_ENV_VAR):
        return

    inject_env_cmd = \
        """
        # append new line if needed
        ! [[ "$(tail -n1 {file_path})" =~ ^\ *$ ]] && echo '' >> {file_path}
        # append env var
        echo '{env_var}={port}' >> {file_path}
        """.format(
            env_var=DEBUGGER_ENV_VAR,
            port=port,
            file_path=REST_SERVICE_ENV_FILE_PATH)
    ssh.sudo(inject_env_cmd)


def _restart_rest_service(ssh):
    restart_rest_service_cmd = 'systemctl restart cloudify-restservice'
    ssh.sudo(restart_rest_service_cmd)


def _connect_manager_to_debugger(ssh, port):

    config = cosmo.handler_configuration
    ip = config['manager_ip']
    user = config['manager_user']
    key_path = os.path.expanduser(config['manager_key'])
    host_address = '{}@{}'.format(user, ip)

    logger.info('Opening reverse tunnel at port {}'.format(port))
    with reverse_tunnel(port=port,
                        host_address=host_address,
                        key_path=key_path) as tunnel:
        logger.info('Injecting debugger port into REST service environment')
        _inject_env_var(ssh, port)

        logger.info('Restarting Manager REST service')
        _restart_rest_service(ssh)

        logger.info('Debugging is now active, press CTRL+C to stop')
        try:
            while True:
                sleep(1)
                if not _is_listening_to_port(port):
                    logger.warn('Debugger server has disconnected')
                    break
                elif not tunnel.is_alive():
                    logger.error('Reverse tunnel has terminated')
                    break
        except KeyboardInterrupt:
            print ''
        finally:
            logger.info('Cleaning up manager environment')
            _cleanup_manager_environment(ssh)


def _download_pycharm_package(ssh, remote_path):
    download_cmd = 'curl {} -o {}'.format(PYCHARM_PACKAGE_URL,
                                          remote_path)
    ssh.run(download_cmd)


def _install_pycharm_package(ssh, remote_path):
    install_cmd = \
        '{} {}'.format(MANAGER_EASY_INSTALL_PATH, remote_path)
    ssh.sudo(install_cmd)


def _cleanup_manager_environment(ssh):
    reset_env_cmd = \
        "sed -i '/{}/d' {}".format(DEBUGGER_ENV_VAR,
                                   REST_SERVICE_ENV_FILE_PATH)
    ssh.sudo(reset_env_cmd)
    _restart_rest_service(ssh)


def _colorize_logger(logger, level, color, bold=False):
    color_func = getattr(colors, color)
    logger_func = getattr(logger, level)

    def color_decorator(log_func, color, bold):
        def colored_log_func(msg, *args, **kwargs):
            return log_func(color_func(msg, bold=bold, *args, **kwargs))
        return colored_log_func

    setattr(logger, level, color_decorator(logger_func, color, bold))
    return logger


def _silly_farewell():
    farewells = [
        'Another bug bites the dust',
        'Did you squash a bug?',
        'We\'ll meet again my friend'
    ]
    return '{} (^_^) bye!'.format(choice(farewells))


@argh.arg('-p', '--port', help='the debugger server port')
@argh.arg('-v', '--verbose', help='show more output')
def script(port=1985, verbose=False):
    '''
    Connect the manager REST service to a local debugger server
    '''
    global logger
    logger = cosmo.logger

    # set colors for logger levels
    logger = _colorize_logger(logger, 'info', 'green', bold=True)
    logger = _colorize_logger(logger, 'warn', 'yellow', bold=True)
    logger = _colorize_logger(logger, 'error', 'red', bold=True)

    remote_path = '/tmp/pycharm-debug.egg'
    output_to_hide = [] if verbose else ['commands', 'status']

    with cosmo.ssh() as ssh, fabric_ctx.hide(*output_to_hide):
        logger.info('Waiting for debugger server to start at port {}'
                    .format(port))
        is_port_ready = _wait_for_port(port)
        if not is_port_ready:
            return

        if not fab_files.exists(remote_path):
                logger.info('Downloading PyCharm egg at remote manager')
                _download_pycharm_package(ssh, remote_path)

                logger.info(
                    'Installing PyCharm package in remote manager virtualenv')
                _install_pycharm_package(ssh, remote_path)

        _connect_manager_to_debugger(ssh, port)

        logger.info(_silly_farewell())
