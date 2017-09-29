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

import re
import json

from .errors import SymlinkException
from .logging_helper import logging, root_logger


def camel_case_to_snake_case(camel_case_input):
    return re.sub(r'[A-Z]', lambda x: "_{}".format(x.group().lower()), camel_case_input).strip('_')


class LoggableObject(object):

    def __init__(self):
        self._logging_info = '.'.join([root_logger.name, self.name])
        self.log = logging.getLogger(self._logging_info)

    @property
    def name(self):
        return camel_case_to_snake_case(self.__class__.__name__)

    def set_logging_info(self, parent, counter=None):
        elements = [parent, self.name]
        if counter:
            elements.append(str(counter))
        self._logging_info = '.'.join(elements)
        self.log = logging.getLogger(self._logging_info)


class MissingSymlink(SymlinkException):
    pass
