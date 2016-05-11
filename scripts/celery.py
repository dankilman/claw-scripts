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

from claw import cosmo


def script(*args):
    """Run a celery command on the management worker"""
    with cosmo.ssh() as ssh:
        command = ('CELERY_WORK_DIR=/opt/mgmtworker/work '
                   '/opt/mgmtworker/env/bin/celery --config=cloudify.broker_config '
                   '{}'.format(' '.join(args)))
        ssh.sudo(command)
