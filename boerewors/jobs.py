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

from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from select import select
import os

from .result import Result, Ok, Err, Skip
from .helper import LoggableObject

try:
    from shlex import quote as cmd_quote
except ImportError:
    from pipes import quote as cmd_quote


class Job(LoggableObject):
    max_retries = 1

    def __init__(self, max_retries=None):
        super(Job, self).__init__()
        self.max_retries = self.__class__.max_retries if max_retries is None else max_retries
        self._job = None
        self._failed_finally = False
        self._result = None
        self.sub_task = None
        self._exception = None

    def reset(self):
        # we do not reset _job otherwise we could not handle max retries
        self._result = None
        self.sub_task = None
        self._exception = None

    def get_result(self, result_type=None, wait_for_it=True, can_fail=False):
        while wait_for_it and self.poll() is None:
            continue
        if not can_fail and self._exception:
            raise self._exception
        return self._result

    def start(self):
        self.sub_task = self.get_next_subtask()

    def job_wrapper(self):
        for idx in range(1, self.max_retries + 1):
            self.reset()
            self.log.info("try to execute {}/{}".format(idx, self.max_retries))
            try:
                for idx, sub_task in enumerate(self.run_job()):
                    self.log.debug("          {}.. subtask {}".format(idx, sub_task))
                    if isinstance(sub_task, LoggableObject):
                        sub_task.set_logging_info(self._logging_info, idx)

                    self.sub_task = sub_task
                    if isinstance(sub_task, Result):
                        self._result = sub_task
                        break
                    yield sub_task
            except Exception as e:
                self.log.exception("subtask had an exception and died")
                # self.set_exception_to_corresponding_sub_job(e)
                self._exception = e
            self.log.debug("sub_tasks done")
            if not self._exception and self._result:
                self.log.info("job successful")
                break
            self.log.info("job not successful")
            yield False
        else:
            self._failed_finally = True
            self.log.error("job failed finally")

    def poll(self):
        # import pdb; pdb.set_trace()
        if self._failed_finally or self._result:
            self.log.debug("task finished failed finally {}, result {}".format(self._failed_finally, self._result))
            return True

        if not self.sub_task:
            # this job has not been started yet
            self.log.debug("the sub task {} has not been started yet. Lets start it".format(repr(self.sub_task)))
            self.sub_task = self.get_next_subtask()
            # we need to stop here, otherwise we could run 2 steps in row (if the new subtask is allready finished)
            return None

        if isinstance(self.sub_task, Job):
            is_sub_task_finished = self.sub_task.poll()
            if is_sub_task_finished is None:
                return None

        next_sub_task = self.get_next_subtask()
        if next_sub_task:
            self.sub_task = next_sub_task
        else:
            # we are finished
            pass

    def get_next_subtask(self):
        if self._job is None:
            # initialize the job
            self._job = self.job_wrapper()
        try:
            return next(self._job)
        except StopIteration:
            return False

    def get_subtask_result(self, result_type=None, can_fail=False):
        """

        Args:
            result_type: depends on the subtask, will be passed to the get_result call
            can_fail: (default: False) if set to false, a possible stored exception will we be reraised.

        Returns:

        """
        return self.sub_task.get_result(result_type, can_fail=can_fail)

    def error_if_subtask_failed(self):
        """
        Check if the subtask wasn't successful and return and Error Result object. Otherwise return None.
        Returns: Error | None

        """
        try:
            result = self.get_subtask_result()
        except Exception as e:
            return self.Error("Subtask raised an Exception: {}".format(e))
        if isinstance(result, Result) and not result:
            return result

        if not self.sub_task.was_successful():
            return self.Error("Subtask failed: {}".format(result))

        # sub_task was ok
        return None

    def run_job(self):
        """
        generator that yields sub jobs

        yield SSHTask("ls /appdata/www/")
        # check results
        if self.sub_task.returncode:
            pass
        """
        raise NotImplementedError()

    def was_successful(self):
        self.log.debug("was_successfull result {}, exception {}".format(self._result, self._exception))
        if self._result is None and self._exception is None:
            # we will not force execution. I will Return False
            return False
        return not bool(self._exception) and bool(self._result)

    def Ok(self, value=True):
        return Ok(value)

    def Error(self, value):
        return Err(value)

    def Skip(self, value=True):
        return Skip(value)


def _decode(output):
    if hasattr(output, 'decode'):
        output = output.decode('utf8')
    return output


class PopenJob(Job):

    def __init__(self, *args, **kwargs):
        super(PopenJob, self).__init__()
        self.log.debug("init popenjob {} {}".format(args, kwargs))
        self.args = args
        self.kwargs = kwargs
        self.callback = None
        self.proc = None
        self._read_handles = []
        self._stdout = None
        self._stderr = None
        self._exception = None
        self._result = None

    def set_callback(self, callback):
        self.callback = callback

    def run_callback(self):
        if self.callback:
            self.callback(self)

    def get_result(self, result_type=None, can_fail=False):
        """Get result from bash command.

        Args:
            result_type (str): None, stdout, stderr, return
            can_fail (bool): True or False

        Returns:
            stdout || stderr || returncode

        """
        if self._exception:
            raise self._exception
        if self._result is None:
            try:
                if self.proc is None:
                    self.start()
                while self.poll() is None:
                    continue
            except Exception as e:
                self._exception = e
                self.log.exception(":(((")
                raise
        if not can_fail and not self.was_successful():
            self.log.error(u"process failed, stdout: {}".format(self._stdout))
            raise CalledProcessError(self._result, cmd=[self.args, self.kwargs], output=self._stdout)

        if result_type == "stdout":
            return self._stdout
        elif result_type == "stderr":
            return self._stderr
        elif result_type == "return":
            return self._result
        return self._result

    def start(self):
        self.log.debug("start task")
        self.proc = Popen(*self.args, **self.kwargs)
        self._read_handles = []
        if self.proc.stdout:
            self._read_handles.append(self.proc.stdout)
            self._stdout = ""
        if self.proc.stderr:
            self._read_handles.append(self.proc.stderr)
            self._stderr = ""

    def consume_pipes_non_blocking(self):

        def read_nonblocking(fileno):
            output = os.read(fileno, 10240)
            return len(output), output

        bytes_read_total = 1
        while bytes_read_total > 0:
            reader, _, _ = select([h for h in self._read_handles if not h.closed],[],[], 0)
            bytes_read_total = 0
            if self._stdout is not None and self.proc.stdout in reader:
                bytes_read, output = read_nonblocking(self.proc.stdout.fileno())
                self._stdout += _decode(output)
                bytes_read_total += bytes_read
            if self._stderr is not None and self.proc.stderr in reader:
                bytes_read, output = read_nonblocking(self.proc.stderr.fileno())
                self._stderr += _decode(output)
                bytes_read_total += bytes_read

    def poll(self):
        if self.proc is None:
            self.start()
            return None

        self.consume_pipes_non_blocking()

        retval = self.proc.poll()
        if retval is not None:
            self.consume_pipes_non_blocking()
            self._result = retval
            self.run_callback()

        return retval

    def was_successful(self):
        if self.proc is None or self.proc.returncode is None:
            return False

        retval = self._result == 0
        if retval:
            self.log.debug("this task was successful {}".format(repr(self._result)))
        else:
            self.log.debug("this task was unsuccessful {}".format(repr(self._result)))
            self.log.debug(u"stdout {}".format(self._stdout))
            self.log.debug(u"stderr {}".format(self._stderr))
        return retval


class BourneShell(PopenJob):

    def __init__(self, bash_command, stdout=PIPE, stderr=STDOUT):
        super(BourneShell, self).__init__(["bash", "-c", bash_command], stdout=stdout, stderr=stderr)
        self.log.debug("init bourneshell {}".format(bash_command))


class SSHJob(BourneShell):

    user = "sshuser"

    def __init__(self, ip, bash_command, user=None, options=None, stdout=PIPE, stderr=STDOUT):
        """SSHJob(ip, bash_command, user=None, options=None, stdout=PIPE, stderr=STDOUT)

        ip:             type str ip or hostname
        bash_command:   type str bash command that should be executed on the server
        user:           type str user name that connects to the server
        options:        type List[str] default: ['StrictHostKeyChecking=no', 'BatchMode=yes', 'ConnectTimeout=10']
        stdout:         type str or subprocess.PIPE
                            "pipe" creates a file object (default)
                            None disables stdout for the process
        stderr:         type str or subprocess.[PIPE|STDOUT]
                            "pipe" creates a file object
                            "stdout" redirects stderr to stdout (default)
                            None disables stderr for the process

        runs the following bash command '/usr/bin/ssh {options} {user}@{server} {bash_command}'

        the bash_command will be quoted to make sure that all of it is executed remotely

        """
        if options is None:
            options = ['StrictHostKeyChecking=no', 'BatchMode=yes', 'ConnectTimeout=10']

        if str(stdout).lower() == "pipe":
            stdout = PIPE
        if str(stderr).lower() == "pipe":
            stderr = PIPE
        if str(stderr).lower() == "stdout":
            stderr = STDOUT

        self.bash_command = cmd_quote(bash_command)
        data = {
            "user": self.user if user is None else user,
            "server": ip,
            "bash_command": self.bash_command,
            "options": ' '.join("-o {}".format(o) for o in options)
        }
        self.ip = ip
        ssh_command = '/usr/bin/ssh {options} {user}@{server} {bash_command}'.format(**data)
        super(SSHJob, self).__init__(ssh_command, stdout=stdout, stderr=stderr)
        self.ssh_command = ssh_command
        self.log.debug("init ssh with {}".format(data))

    def start(self):
        self.log.notice('\nSSH command started({ip}): \n{bash_command}'.format(bash_command=self.bash_command, ip=self.ip))
        super(SSHJob, self).start()
