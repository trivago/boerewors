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

from datetime import datetime
from context import BoereworsExecutor, runners, jobs, stage, logging_helper
import pytest

slow = pytest.mark.skipif(
    not pytest.config.getoption("--runslow"),
    reason="need --runslow option to run"
)


class SillyJob(jobs.Job):
    def __init__(self, counter=5, index=-1):
        super(SillyJob, self).__init__()
        self.counter = counter
        self.index = index

    def run_job(self):
        yield True

    def poll(self):
        self.counter -= 1
        self.log.info("   counter is at {}".format(self.counter))
        if self.counter <= 0:
            self._result = "Juhu"
            return True


class FailJob(jobs.Job):
    def run_job(self):
        self._exception = ValueError("lol exception")
        print("i failed")
        yield True


class StageTesting(stage.Stage):
    def get_jobs(self):
        yield SillyJob(1)
        yield SillyJob(2)
        yield SillyJob(3)


class StageFailing(stage.Stage):
    def get_jobs(self):
        yield SillyJob(1)
        yield FailJob()
        yield SillyJob(3)


class StageDistribute(stage.Stage):
    def get_jobs(self):
        yield SillyJob(5)
        yield SillyJob(5)
        yield SillyJob(5)


class MyRunner(runners.Runner):
    # _stages = [StageTesting()]
    def get_stages(self):
        yield StageTesting()
        yield StageDistribute()


def test_executor():
    executor = BoereworsExecutor(runners=[MyRunner()])
    assert executor.run(argv=[])


class FailRunner(runners.Runner):
    def get_stages(self):
        yield StageFailing()
        yield StageDistribute()


class FailSetupRunner(runners.Runner):
    def setup(self, args=None):
        print("will return false")
        return False

    def get_stages(self):
        yield StageDistribute()

def test_executor_fail():
    executor = BoereworsExecutor(runners=[FailRunner()])
    assert not executor.run(argv=[])

    # The executor will indicate an error if the setup of the runner fails
    executor = BoereworsExecutor(runners=[FailSetupRunner()])
    assert not executor.run(argv=[])


class TimeRunner(runners.Runner):
    def __init__(self, canary=True, parallel=True, num_jobs=10, pool_size=10):
        super(TimeRunner, self).__init__()
        self.canary = canary
        self.parallel = parallel
        self.num_jobs = num_jobs
        self.pool_size = pool_size

    def get_stages(self):
        time_stage = TimeStage(self.num_jobs, self.pool_size)
        time_stage.is_canary = self.canary
        time_stage.allow_parallel_execution = self.parallel
        yield time_stage


class TimeStage(stage.Stage):
    def __init__(self, num_jobs=10, pool_size=10):
        super(TimeStage, self).__init__()
        self.num_jobs = num_jobs
        self.pool_params = dict(pool_size=pool_size)

    def get_jobs(self):
        for i in range(self.num_jobs):
            yield jobs.PopenJob(['sleep', '1'])


def check_time(runner, min_time=0, max_time=10):
    root_logger = logging_helper.logging.getLogger("root")
    old_level = root_logger.level
    root_logger.setLevel(logging_helper.logging.INFO)
    executor = BoereworsExecutor(runners=[runner])
    before = datetime.now()
    assert executor.run(argv=[])
    excution_time = datetime.now() - before
    assert min_time < excution_time.total_seconds() < max_time
    root_logger.setLevel(old_level)


@slow
def test_popenjob_canary_parallel():
    check_time(TimeRunner(), max_time=3)


def test_popenjob_nocanary_parallel():
    check_time(TimeRunner(canary=False), max_time=2)


@slow
def test_popenjob_noparallel():
    check_time(TimeRunner(canary=False, parallel=False, num_jobs=5), max_time=6, min_time=5)


# This is a integration test, similliar to the distribute jobs.job
job_id = 0


class DistributeJob(jobs.Job):
    def __init__(self, id, max_retries=None):
        self.id = id
        super(DistributeJob, self).__init__()

    def run_job(self):
        """
        simmulation of a failed distribute jobs.job
        """
        global job_id
        job_id = self.id
        try:
            yield jobs.BourneShell('echo "oh no";false')
            self.log.notice(self.get_subtask_result('stdout'))
            yield self.Ok()
        except Exception as e:
            yield self.Error('error: {}'.format(e))


class DistributeCodeJob(jobs.Job):
    def run_job(self):
        """
        simmulation of the distribution of code and cache
        """
        yield DistributeJob(1)
        yield self.error_if_subtask_failed()
        yield DistributeJob(2)
        yield self.error_if_subtask_failed()
        yield self.Ok()


class DistributeStage(stage.Stage):
    """
    minimalistic version of the trivago stage
    """

    def __init__(self, job_klass, *args, **kw):
        self.job_klass = job_klass
        super(DistributeStage, self).__init__(*args, **kw)

    def get_jobs(self):
        """
        yield one jobs.job
        """
        yield self.job_klass()


class DistributeRunner(runners.Runner):
    def get_stages(self):
        """
        minimal runner that yield a stage for the code distribute jobs.job
        """
        yield DistributeStage(DistributeCodeJob)


def test_not_implemented():
    executor = BoereworsExecutor(runners=[DistributeRunner()])
    # the distribute jobs.job should fail if there is an error during the ssh / distribute jobs.job
    assert not executor.run([])

    # if the code distribute failed, the cache should not be distributed
    assert job_id == 1


global_job_index = -1


class SimpleStage(stage.Stage):

    def get_jobs(self):
        global global_job_index
        for idx in range(5):
            global_job_index = idx
            print("jobs.job {} yielded".format(idx))
            yield SillyJob(idx)


class LimitRunner(runners.Runner):
    def get_stages(self):
        yield SimpleStage()


def test_limit_parameter():
    executor = BoereworsExecutor(runners=[LimitRunner()])
    executor.setup_arg_parser()
    executor.run([])

    assert global_job_index == 4

    executor.run(['--limit', '2'])
    assert global_job_index == 1


class NonParallelSimpleStage(stage.Stage):

    allow_parallel_execution = False

    def get_jobs(self):
        global global_job_index
        for idx in range(5):
            print("jobs.job {} yielded".format(idx))
            global_job_index = idx
            yield SillyJob(index=idx)

    def cleanup(self, errors):
        from collections import Counter
        print(list(j.index for j in self._joblist))
        c = Counter([str(j.index) for j in self._joblist])
        print(c)
        for idx, count in c.items():
            assert count == 1


class NonParallelRunner(runners.Runner):
    def get_stages(self):
        yield NonParallelSimpleStage()


def test_non_parallel():
    executor = BoereworsExecutor(runners=[NonParallelRunner()])
    executor.setup_arg_parser()
    executor.run([])
