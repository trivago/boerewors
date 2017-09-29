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

import sys
from argparse import ArgumentParser
try:
    from itertools import izip as zip
except ImportError:
    # we are on python 3 and zip is an iterator already
    pass

from . import __version__ as boerewors_version
from . import __git_hash__ as boerewors_hash
from .pool import Pool
from .logging_helper import logging, NOTICE


def take_upto(max_elements=None, iterator=None):
    if iterator is None:
        iterator = []
    if max_elements is None:
        for element in iterator:
            yield element
    else:
        for i, element in zip(range(max_elements), iterator):
            yield element


class BoereworsExecutor(object):

    def __init__(self, runners, title=None):
        self.title = title if title else "boerewors"
        self.runners = {}
        self.parser = None
        self.log = logging.getLogger("root.executor")
        for runner in runners:
            try:
                self.runners[runner.name] = runner
            except Exception:
                self.log.warning("runner {} couldn't be added")
        self.setup_arg_parser()

    def setup_arg_parser(self):
        parser = ArgumentParser(self.title)
        parser.add_argument('--version', action='store_true')
        parser.add_argument('-v', '--verbose', action='count', default=0)
        parser.add_argument('--limit', type=int, help="limit the amount of jobs per stage")

        if len(self.runners) == 1:
            runner = list(self.runners.values())[0]
            parser.set_defaults(runner=runner.name)
            runner.setup_parser(parser)
        else:
            subparsers = parser.add_subparsers()
            for runner in self.runners.values():
                new_parser = subparsers.add_parser(runner.name)
                new_parser.set_defaults(runner=runner.name)
                runner.setup_parser(new_parser)
        self.parser = parser

    def run(self, argv=None):
        args = self.parser.parse_args(argv)
        if args.verbose >= 0:
            self.log.setLevel(max(NOTICE - args.verbose * 10, 5))
        runner = self.runners[args.runner]
        if args.version:
            print("boerewors {} v{} (git commit:{})".format(args.runner, boerewors_version, boerewors_hash))
            sys.exit(0)
        self.log.notice("running {} v{} (git commit:{})".format(args.runner, boerewors_version, boerewors_hash))
        if not runner.setup(args):
            self.log.error("E1485877222: setup of runner {} failed.".format(args.runner))
            return False
        errors = False
        for stage in runner.stages:
            stage.setup()
            errors = False
            try:
                jobs_iterator = take_upto(args.limit, stage.jobs)
                if stage.is_canary:
                    self.log.info("run canary job")
                    job = next(jobs_iterator)
                    self.log.debug("next job {}".format(job))
                    job.get_result()
                    if not job.was_successful():
                        # it failed exit
                        self.log.error("canary job failed. {}".format(job._result))
                        self.log.error("Stage {} failed. ".format(stage))
                        errors = True
                        break
                    self.log.info("canary job succeeded")

                if stage.allow_parallel_execution:
                    # maybe something like fail_early
                    pool = Pool(**stage.pool_params)
                    # pool.set_logging_info(stage._logging_info)
                    for job in jobs_iterator:
                        pool.add_task(job)
                    pool.run()
                    results = list(pool.results)
                    self.log.info(results)
                    self.log.info(all(results))
                    if not all(results):
                        self.log.error("Stage {} failed. ".format(stage))
                        for result in results:
                            if not result:
                                self.log.error(result)
                        errors = True
                else:
                    for job in jobs_iterator:
                        job.get_result()
                        if not job.was_successful():
                            self.log.error("Job {} failed".format(job))
                            errors = True

                if not stage.should_continue(errors):
                    self.log.warning(
                        "Stage {}, will not continue. {} {}".format(
                            stage, "(there have been errors)" if errors else "", errors))
                    break
            except StopIteration:
                self.log.warning("stage emitted no jobs")
            finally:
                stage.cleanup(errors=errors)
        runner.cleanup()
        return not errors
