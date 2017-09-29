# Copyright 2017 trivago N.V.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import deque
from .helper import LoggableObject
from .logging_helper import logging


class Pool(LoggableObject):

    def __init__(self, pool_size=10):
        super(Pool, self).__init__()
        self.pool_size = pool_size
        self.upcomming_tasks = deque()
        self.running_tasks = deque()
        self.finished_tasks = deque()
        self.log = logging.getLogger("root.pool")

    def add_task(self, task):
        self.upcomming_tasks.append(task)

    def consume_task(self):
        task = self.upcomming_tasks.popleft()
        task.start()
        self.running_tasks.append(task)

    def run(self,):
        while self.running_tasks or self.upcomming_tasks:
            # self.log.debug("running: {}, upcomming {}".format(len(self.running_tasks), len(self.upcomming_tasks)))
            while self.upcomming_tasks and len(self.running_tasks) < self.pool_size:
                self.log.info("consume task")
                self.consume_task()
            still_running_tasks = deque()
            while self.running_tasks:
                task = self.running_tasks.popleft()
                if task.poll() is None:
                    # task is not finished yet
                    # self.log.debug("task {} is not finished".format(task))
                    still_running_tasks.append(task)
                else:
                    self.log.info("task is finished :)")
                    self.finished_tasks.append(task)
            self.running_tasks = still_running_tasks
            # from time import sleep; sleep(0.5)

    @property
    def results(self):
        for task in self.finished_tasks:
            if task._exception:
                yield False
            else:
                task.get_result()
                yield task.was_successful()
