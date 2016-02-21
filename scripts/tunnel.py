#! /usr/bin/env claw

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
