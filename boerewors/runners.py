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


class Runner(LoggableObject):

    def __init__(self):
        super(Runner, self).__init__()
        self._stage_counter = 0
        self.latest_stage = None

    def setup(self, args):
        return True

    @property
    def stages(self):
        for stage in self.get_stages():
            self._stage_counter += 1
            # provide logging info if the stage accepts it
            getattr(stage, 'set_logging_info', lambda *x: None)(self._logging_info, self._stage_counter)
            self.latest_stage = stage
            yield stage

    def setup_parser(self, parser):
        pass

    def cleanup(self):
        pass

    def __repr__(self):
        return "Runner {}".format(self.name)

    __str__ = __repr__

    def get_stages(self):
        raise NotImplementedError()
