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

from context import runners
try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


class MyRunner(runners.Runner):
    def get_stages(self):
        return [1, 2, 3]


def test_stages():
    runner = MyRunner()
    assert list(runner.get_stages()) == [1, 2, 3]
    assert list(runner.stages) == [1, 2, 3]


def test_setup_parser():
    runner = MyRunner()
    parser = Mock()
    runner.setup_parser(parser)
    assert True
