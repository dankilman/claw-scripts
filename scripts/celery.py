#! /usr/bin/env claw

from claw import cosmo


def script(*args):
    """Run a celery command on the management worker"""
    with cosmo.ssh() as ssh:
        command = ('CELERY_WORK_DIR=/opt/mgmtworker/work '
                   '/opt/mgmtworker/env/bin/celery --config=cloudify.broker_config '
                   '{}'.format(' '.join(args)))
        ssh.run(command)
