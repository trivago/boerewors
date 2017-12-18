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

from .helper import LoggableObject


class Stage(LoggableObject):

    is_canary = True
    allow_parallel_execution = True
    can_fail = False
    pool_params = {}

    def __init__(self,
                 is_canary=None,
                 allow_parallel_execution=None,
                 can_fail=None,
                 pool_params=None,
                ):
        super(Stage, self).__init__()
        if is_canary is not None:
            self.is_canary = is_canary
        if allow_parallel_execution is not None:
            self.allow_parallel_execution = allow_parallel_execution
        if can_fail is not None:
            self.can_fail = can_fail
        if pool_params is not None:
            self.pool_params = pool_params
        self._joblist = []

    @property
    def jobs(self):
        for idx, job in enumerate(self.get_jobs()):
            # provide logging info if the job accepts it
            getattr(job, 'set_logging_info', lambda *x: None)(self._logging_info, idx)
            self._joblist.append(job)
            yield job

    def should_continue(self, errors):
        if self.can_fail:
            return True
        return not errors

    def __repr__(self):
        return "Stage {}".format(self.name)

    __str__ = __repr__

    def setup(self):
        self.log.notice("Stage start")

    def cleanup(self, errors):
        self.log.notice("Stage finish {}\n".format("(errors occured)" if errors else ""))

    def collect_summary(self):
        summary = dict(failed_jobs=0, succeeded_jobs=0)
        for job in self._joblist:
            if job.was_successful():
                summary['succeeded_jobs'] += 1
            else:
                summary['failed_jobs'] += 1
        return summary

    def get_jobs(self):
        """
        an iterator that yields jobs, eg:

        for ip in self.ips:
            yield Job(ip)
        """
        raise NotImplementedError()
