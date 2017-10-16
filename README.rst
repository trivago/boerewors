boerewors
=========


.. image:: https://gitlab.com/trivago/rta/boerewors/badges/master/pipeline.svg
.. image:: https://gitlab.com/trivago/rta/boerewors/badges/master/coverage.svg

Boerewors is a release tool written in Python to streamline all DSE/PSE
PHP releases. The name ``boerewors`` comes from the name of `a traditional sausage
for braai (BBQ) in
Namibia🇳🇦 <https://en.wikipedia.org/wiki/Boerewors>`__. Since it started
as a warmup script written in Python it reminded me of boerewors.

Dependencies
------------

For now it will work with the following Python versions. We might drop Python 2 support in the future.

-  Python 2.7
-  Python 3.4
-  Python 3.5
-  Python 3.6

Contribution
------------

t.b.d.

How to run the tests
--------------------

Running unit tests using py.test
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: bash

    pip install pytest mock
    py.test tests

How to add a new command
------------------------

1. Create a new runner and define the stages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    class NewJobRunner(Runner):

        is_canary = False

        def get_stages(self):
            yield Stage(self.config, NewJob)

        def load_config(self, args):
            return {
                "servers": ["hosta", "hostb"]
            }

    class NewStage(Stage):

        def __init__(self, config, job_class):
            super(NewStage, self).__init__()
            self.config = config
            self.job_class = job_class

        def get_jobs(self):
            for server in self.config["servers"]:
                yield self.job_class(server, self.config)


If you plan to prohibit parallel execution or want to fine tune the job
execution, we provided some useful class attributes.

.. code:: python

        is_canary = True

If ``is_canary`` is set to True (the default value), the first job will
be executed alone and the stage will fail immediately if it fails.

.. code:: python

        allow_parallel_execution = True
        can_fail = False

``allow_parallel_execution`` should be self explanatory. If ``can_fail``
is set to True, the stage will not fail, even if some jobs did.

.. code:: python

        pool_params = {}

With the ``pool_params`` you can provide some parameter for the
execution pool. For example ``pool_params = {'pool_size': 5}`` would
reduce the default pool size from 10 to 5. So only 5 jobs would run at
the same time.

It is worth to mention that the jobs are asynchronous and not parallel.
If the jobs are using only blocking statements you would not benefit
from the pool.

2. Write the job
~~~~~~~~~~~~~~~~

.. code:: python

    class NewJob(Job):

        max_retries = 2

        def __init__(self, server, config):
            self.server = server
            self.config = config
            super(NewJob, self).__init__()

        def run_job(self):
            cmds = [
                "curl {url} -o {save_to}",
                "mkdir -p {extract_to}",
                "cd {extract_to}",
                "tar -xpf {save_to}",
                "rm {save_to}",
            ]
            yield SSHJob(self.server, " && ".join(cmds).format(**config))
            self.log.info(self.get_subtask_result('stdout'))
            yield self.Ok()

.. attention::
    It is very important to query ``get_subtask_result`` after you yielded
    a subtask, otherwise a possible exception could be ignored and muted!

It is very important that at least one ``yield`` statement is used in
the ``run_job`` generator function. Usually you can provide a new
subtask to the executor and this generator function is continued as soon as
the subtask is finished.

When you ``yield self.Ok()`` at any point, you signal the executor, that
this job is finished successfully. A
``yield self.Error("descriptive reason why this job failed")`` will fail
the job immediately.

With the class property ``max_retries`` you can tell the executor how
many times the job should be retried in case of failure before it is
considered a final failure.

3. How to execute it
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    if __name__ == "__main__":
        executor = BoereworsExecutor(runners=[NewJobRunner()])
        executor.run()


To-Do
-----

- add config loading

Pull requests are encouraged!


License
-------

Copyright 2017 trivago N.V.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
