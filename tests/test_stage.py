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

import pytest
from context import stage


class FailStage(stage.Stage):
    can_fail = True

    def get_jobs(self):
        return [1, 2, 3]


def test_not_implemented():
    my_stage = stage.Stage()
    with pytest.raises(NotImplementedError):
        my_stage.get_jobs()


def test_should_continue():
    my_stage = stage.Stage()
    fail_stage = FailStage()

    assert fail_stage.should_continue(errors=False)
    assert fail_stage.should_continue(errors=True)

    assert my_stage.should_continue(errors=False)
    assert not my_stage.should_continue(errors=True)


def test_jobs():
    my_stage = FailStage()

    assert list(my_stage.jobs) == [1, 2, 3]
