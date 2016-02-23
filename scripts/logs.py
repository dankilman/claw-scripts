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


import shutil

from sh import tar

from claw import cosmo
from claw.commands import cfy


def script():
    """Run 'cfy logs' and extract output to CONFIGURATION_DIR/logs"""
    logs_dir = cosmo.dir / 'logs'
    if logs_dir.exists():
        shutil.rmtree(logs_dir, ignore_errors=True)
    logs_dir.mkdir()
    logs_tar = logs_dir / 'logs.tar.gz'
    with logs_dir:
        cfy.logs.get(destination_path=logs_tar).wait()
        tar('xf', logs_tar, strip_components=1)
        logs_tar.remove()
