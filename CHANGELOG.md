# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]

## [1.0.1] - 2017-12-18
### Changed

* `Stage` takes more parameters to modify the while creating a new instance. It is no longer necessary to create a new
    class if you only want the stage prohibit parallel execution. `Stage` takes now this parameters `is_canary`,
    `allow_parallel_execution`, `can_fail`, `pool_params`.
