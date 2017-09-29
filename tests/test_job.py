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

from __future__ import print_function
import pytest
from context import jobs


class DummyJob(jobs.Job):

    def __init__(self, counter=5):
        self.counter = counter

    def run_job(self):
        yield True

    def poll(self):
        self.counter -= 1
        print("  counter: {}".format(self.counter))
        if self.counter <= 0:
            self._result = "Juhu"
            return True


class ParentJob(jobs.Job):

    def run_job(self):
        print("running first child")
        yield DummyJob(2)
        self.sub_task._result
        print("running second child")
        yield DummyJob(3)
        print("clean up")
        yield self.Ok()
        assert False, "this line should not be executed anymore"


def test_simple_job():
    parent_job = ParentJob()
    # 2 (first job) + 3 (second job) + 1 (cleanup [yield OK])
    for _ in range(6):
        result = parent_job.poll()
        print("step: {}, result: {}".format(_, result))
        assert result is None
        # print(_)
    assert parent_job.poll()


def test_simple_job_blocking():
    parent_job = ParentJob()
    assert parent_job.get_result()


class FailJob(jobs.Job):

    def run_job(self):
        raise ValueError("lol exception")
        yield self.Ok()


class FailJob2(jobs.Job):

    def run_job(self):
        yield self.Error("lets just fail")


class FailPopenJob(jobs.PopenJob):

    def __init__(self,):
        super(FailPopenJob, self).__init__(['false'])


def test_fail_job():
    failure = FailJob()
    failure.max_retries = 5

    # 5 retries +1 for clean up
    for _ in range(6):
        result = failure.poll()
        assert result is None
        print("step: {}, result: {}".format(_, result))
    # assert False
    assert failure.poll()
    with pytest.raises(ValueError):
        failure.get_result()


def test_fail_job2():
    failure = FailJob2()
    failure.get_result()
    assert not failure.was_successful()


def test_fail_popenjob():
    failure = FailPopenJob()
    with pytest.raises(Exception):
        failure.get_result()


def test_not_implemented():
    job = jobs.Job()
    with pytest.raises(NotImplementedError):
        job.run_job()


def test_explizit_start():
    failure = FailJob()
    failure.max_retries = 5
    failure.start()

    # 5 retries +1 for clean up -1 for explizit start
    for _ in range(5):
        result = failure.poll()
        print("step: {}, result: {}".format(_, result))
        assert result is None
    assert failure.poll()
    with pytest.raises(ValueError):
        failure.get_result()


class FailSubJob(jobs.Job):

    def run_job(self):
        yield FailJob(1)
        self.get_subtask_result()
        yield self.Ok()


class FailSubPopenJob(jobs.Job):

    def run_job(self):
        yield FailPopenJob()
        self.get_subtask_result()
        yield self.Ok()


class FailSubSubJob(jobs.Job):

    def run_job(self):
        yield DummyJob(1)
        yield FailSubJob(1)
        self.get_subtask_result()
        yield self.Ok()


class FailSubSubPopenJob(jobs.Job):

    def run_job(self):
        yield DummyJob(1)
        yield FailSubPopenJob(1)
        self.get_subtask_result()
        yield self.Ok()


def test_fail_subjob():
    failure = FailSubJob()
    with pytest.raises(ValueError):
        failure.get_result()

    failure = FailSubSubJob()
    with pytest.raises(ValueError):
        failure.get_result()


def test_fail_subpopenjob():
    failure = FailSubPopenJob()
    with pytest.raises(Exception):
        failure.get_result()

    failure = FailSubSubPopenJob()
    with pytest.raises(Exception):
        failure.get_result()


class IgnoreFailSubJob(jobs.Job):

    def run_job(self):
        try:
            yield FailJob(1)
            self.get_subtask_result()
        except ValueError:
            pass
        yield self.Ok()


def test_try_except_fail_subjob():
    good_job = IgnoreFailSubJob()
    assert not good_job.was_successful()
    result = good_job.get_result()
    print("the result is {}".format(repr(result)))
    assert result
    assert good_job.was_successful()
