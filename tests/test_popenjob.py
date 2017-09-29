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
from subprocess import PIPE


def test_failing_popenjob():
    failure = jobs.PopenJob(["false"])
    with pytest.raises(Exception):
        result = failure.get_result()
        print(result)

    with pytest.raises(Exception):
        jobs.PopenJob("Does not exist").get_result()

    failure = jobs.PopenJob(["true"])
    failure._exception = ValueError("test")
    with pytest.raises(ValueError):
        failure.get_result()


def test_success():
    echo = jobs.PopenJob(["echo", "lol"], stdout=PIPE)
    assert not echo.was_successful(), "the job should not be successful, it had not been started yet"
    # import pdb; pdb.set_trace()
    assert echo.get_result('stdout') == 'lol\n'
    assert echo.get_result('stderr') is None
    assert echo.was_successful()
    assert echo.get_result('return') == 0
    assert echo.get_result() == 0


def test_poll():
    echo = jobs.PopenJob(["echo", "lol"], stdout=PIPE)
    while echo.poll() is None:
        pass
    assert echo.was_successful()


def test_callback():
    echo = jobs.PopenJob(["echo", "lol"], stdout=PIPE)
    echo.set_callback(lambda x: print(x.get_result('stdout')))
    while echo.poll() is None:
        pass
    assert echo.was_successful()


def test_huge_output():
    big_output = jobs.PopenJob(["python", "-c", "print('when I slept in class, it was not to help Leo DiCaprio\\n' * 10000)"], stdout=PIPE)
    for i in range(1000000):
        if big_output.poll() is not None:
            print("fine")
            break
    else:
        assert False, "this test should not block"

if __name__ == "__main__":
    pytest.main("tests/test_popenjob.py")
