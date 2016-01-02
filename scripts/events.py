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

import sys
import json

from cloudify_cli.execution_events_fetcher import ExecutionEventsFetcher

from claw import cosmo


def script(execution_id,
           output=None,
           batch_size=1000,
           include_logs=True,
           timeout=3600):
    """Dump events of an execution in json format."""

    fetcher = ExecutionEventsFetcher(execution_id=execution_id,
                                     client=cosmo.client,
                                     batch_size=batch_size,
                                     include_logs=include_logs)

    stream = open(output, 'w') if output else sys.stdout

    def handle(batch):
        for event in batch:
            stream.write('{0}\n'.format(json.dumps(event)))

    try:
        fetcher.fetch_and_process_events(events_handler=handle,
                                         timeout=timeout)
    finally:
        if output:
            stream.close()
