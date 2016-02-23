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

import os

import sh
from claw import cosmo

ssh = sh.ssh


def script(port, local=0, reverse=False):
    """Create a local/remote tunnel to/from a port on the management host"""
    handler_configuration = cosmo.handler_configuration
    ip = handler_configuration['manager_ip']
    user = handler_configuration['manager_user']
    key = os.path.expanduser(handler_configuration['manager_key'])
    if local == 0:
        local = port
    if reverse:
        message = 'Tunneling local port {} to remote host localhost:{}'.format(port, local)
    else:
        message = 'Tunneling remote port {} to local host localhost:{}'.format(port, local)
    cosmo.logger.info(message)
    command = ['-i', key,
               '{}@{}'.format(user, ip),
               '-R' if reverse else '-L', '{}:localhost:{}'.format(local, port)]
    p = ssh(*command, _bg=True)
    try:
        p.join()
    except KeyboardInterrupt:
        p.kill()
