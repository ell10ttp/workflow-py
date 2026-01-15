# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-15

### Added

- `context.wait_for_event(step_name, event_id, timeout)` - Pause workflow execution until an external event occurs
- `context.notify(step_name, event_id, event_data)` - Notify waiting workflows from within a workflow
- `Client` and `AsyncClient` classes for notifying workflows from outside workflow context
- `WaitForEventResult` dataclass with `event_data` and `timeout` fields
- `NotifyResult` dataclass with `event_id` and `notified_count` fields
- `NotifyResponse` dataclass for Client.notify() responses
- Documentation for wait_for_event feature in README

### Fixed

- Fixed `workflow_parser.py` bug where `step.wait_timeout` used attribute access on a dictionary
- Fixed test failures caused by qstash-py API header prefix changes

## [0.1.4] - Previous

- Add workflow endpoint detection feature
- Ignore render and cf loop headers

## [0.1.3] - Previous

- Add Failure Function support

## [0.1.2] - Previous

- Initial stable release
