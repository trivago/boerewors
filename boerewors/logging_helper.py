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

import logging
from logging import getLoggerClass, addLevelName, setLoggerClass, NOTSET, CRITICAL, ERROR, WARNING, INFO, DEBUG
# see https://docs.python.org/2/library/logging.html#logging-levels
NOTICE = 25
FORMAT = "%(levelname)s:\t[%(name)s]\t%(message)s"


class MyLogger(getLoggerClass()):

    def __init__(self, name, level=NOTSET):
        super(MyLogger, self).__init__(name, level)
        addLevelName(NOTICE, "NOTICE")

    def notice(self, msg, *args, **kwargs):
        if self.isEnabledFor(NOTICE):
            self._log(NOTICE, msg, args, **kwargs)


setLoggerClass(MyLogger)

root_logger = logging.getLogger('root')

if not root_logger.handlers:
    logging.basicConfig(level=NOTICE, format=FORMAT)
