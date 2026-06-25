# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The New Relic Python Agent is an Application Performance Monitoring (APM) agent that instruments Python applications for performance monitoring and analytics. It supports Python 3.9+ and monitors applications by wrapping functions, tracking transactions, collecting metrics, and sending telemetry data to New Relic's backend services.

## Development Commands

### Running Tests

Tests are run using `tox` from the root of the repository. The test suite is organized by component/framework. Each component's test suite is a separate subdirectory under `tests/`. To run that test suite, call the tox environment that contains the folder name of the test suite. `tox` will handle calling `cd` into the correct directory (via the `changedir` setting in `tox.ini`).

```bash
# List test suites available to run
tox -l

# Run tests for a specific component (from repository root)
tox run -e linux-agent_features-py312-with_extensions

# Run tests for a framework integration (run `tox -l` for exact env names)
tox run -e python-framework_django-py312-Djangolatest
```

To iterate on a single test file with pytest directly, `cd` into that suite's directory first:

```bash
cd tests/agent_features
pytest test_agent_control_health_check.py -v
```

### Running Tests with Coverage

Running tests with `tox` automatically produces a coverage data file for that environment combination.

```bash
# Clear out old coverage files
rm .tox/**/.coverage.*
# Run tox to collect coverage for any number of environments
tox run-parallel -e python-framework_falcon-py313-falconlatest,python-framework_falcon-py314-falconlatest
# Combine data files (required, even for 1 input file)
coverage combine .tox/**/.coverage.*
# Generate the XML report, scoped to the file(s) you care about
coverage xml --include=newrelic/hooks/framework_falcon.py
# Read output file
cat coverage.xml
```

### Tox Environment Naming Convention

Tox environments follow this pattern:
`services_required-tests_folder-python_version-library_version[optional]-extensions[optional]`

Examples:
- `linux-agent_features-py312-with_extensions`
- `postgres-datastore_psycopg-py313-psycopg0302`
- `python-framework_flask-py311-flasklatest`

### Linting and Formatting

```bash
# Run ruff linter and formatter (line length is 120; see [tool.ruff] in pyproject.toml)
ruff check --fix && ruff format

# Run pre-commit hooks manually (ruff hooks are registered at the pre-push stage)
pre-commit run --all-files --hook-stage pre-push
```

### Building the Agent

```bash
# Install the agent in development mode
pip install -e .

# Install with C extensions explicitly enabled
NEW_RELIC_EXTENSIONS=true pip install -e .

# Install without C extensions
NEW_RELIC_EXTENSIONS=false pip install -e .
```

## Architecture

### Core Components

#### 1. **Import Hook System** (`newrelic/api/import_hook.py`)
The agent uses Python's import hook mechanism to automatically instrument third-party libraries. Import hooks are registered for specific modules and fire when those modules are first imported, allowing the agent to wrap functions before they're used. These are registered by calling `_process_module_definition(target, module, function)` where `target` is a string form of the instrumented library's module path, `module` is a string form of the module containing the instrument function under `newrelic.hooks.*`, and `function` is the name of the instrumentation hook to run on that module.

#### 2. **Instrumentation Hooks** (`newrelic/hooks/`)
Each file in the `hooks/` directory contains instrumentation for a specific library or framework. Hooks use `wrap_function_wrapper` and similar utilities to instrument code without modifying the original source. Each instrument function requires at least 1 import hook which will apply it, made by a call to `_process_module_definition` in the file `newrelic/config.py` under the function `_process_module_builtin_defaults`.

Pattern:
```python
def instrument_module_name(module):
    wrap_function_wrapper(module, 'ClassName.method', wrapper_function)
```

#### 3. **API Layer** (`newrelic/api/`)
Provides public APIs for:
- Transaction management (`transaction.py`, `background_task.py`)
- Trace decorators/context managers (`function_trace.py`, `datastore_trace.py`, `external_trace.py`)
- Error tracking (`error_trace.py`)
- Custom instrumentation points

#### 4. **Core Engine** (`newrelic/core/`)
Contains the core agent logic:
- `agent.py` - Main agent singleton and lifecycle management
- `application.py` - Application instance management
- `*_node.py` - Node types for the transaction trace tree (database, external, function, etc.)
- `config.py` - Configuration management

#### 5. **Transaction Model**
Transactions are represented as trees of nodes:
- Each trace type (function, database, external call) creates a node
- Nodes track timing, metadata, and relationships
- The root transaction aggregates all nodes and generates metrics
- Transactions are context-local using thread-local or async context storage

#### 6. **Wrapper Architecture** (`newrelic/common/object_wrapper.py`)
The agent extensively uses function wrapping to inject instrumentation:
- `wrap_function_wrapper()` - Wraps functions/methods
- `FunctionWrapper` - Wrapper object that preserves function metadata
- Wrappers can be nested and maintain proper call order

#### 7. **Data Collection & Streaming**
- `data_collector.py` - HTTP-based protocol for sending telemetry
- `agent_streaming.py` - gRPC-based infinite tracing for distributed tracing
- Harvest cycle collects and sends metrics periodically (default: 60 seconds)

### Key Design Patterns

1. **Lazy Initialization**: The agent must be initialized before importing instrumented libraries for best results, but handles late initialization gracefully.

2. **Manual Instrumentation API**: Decorators and context managers (`@background_task`, `@function_trace`, `with` blocks) mark transaction and trace boundaries.

3. **Thread Safety**: Heavily uses thread-local storage and locks for managing per-thread transaction state.

4. **Async Support**: Special handling for asyncio, gevent, and other async frameworks with context propagation.

### Test Organization

Tests are organized by component type:
- `agent_features/` - Core agent functionality
- `agent_unittests/` - Unit tests
- `adapter_*/` - WSGI/ASGI server adapters
- `datastore_*/` - Database client libraries
- `framework_*/` - Web frameworks
- `external_*/` - HTTP client libraries
- `messagebroker_*/` - Message queue libraries
- `mlmodel_*/` - ML/AI framework integrations
- `logger_*/` - Logging framework integrations
- `testing_support/` - Test utilities and fixtures

### Configuration

Configuration sources (in order of precedence):
1. Environment variables (`NEW_RELIC_*`)
2. `newrelic.ini` config file
3. Programmatic configuration via `newrelic.agent.global_settings()`

Common environment variables:
- `NEW_RELIC_LICENSE_KEY` - License key for authentication
- `NEW_RELIC_APP_NAME` - Application name in APM
- `NEW_RELIC_CONFIG_FILE` - Path to config file
- `NEW_RELIC_DEVELOPER_MODE` - Enable developer mode for testing
- `NEW_RELIC_EXTENSIONS` - Control C extension compilation (true/false)

## Important Conventions

### Adding New Instrumentation

When adding support for a new library:

1. Create a hook file in `newrelic/hooks/` (e.g., `newrelic/hooks/framework_newlib.py`)
2. Implement `instrument_module_name()` function
3. Add test directory under `tests/` with matching name
4. Add tox environment definition in `tox.ini`
5. Register import hooks that trigger instrumentation (via `_process_module_definition` in `newrelic/config.py`)
6. Create tests that validate metrics, traces, and attributes

### Wrapper Function Signature

Wrappers should follow this pattern:
```python
def wrapper(wrapped, instance, args, kwargs):
    # wrapped: original function
    # instance: object instance (for bound methods) or object class (for class methods), or None (for functions and static methods)
    # args, kwargs: original call arguments for the wrapped function
    return wrapped(*args, **kwargs)
```

### Error Handling in Instrumentation

Instrumentation code must never break the application:
- Wrap instrumentation in try/except blocks
- Log instrumentation errors at debug level
- Always call the original wrapped function

### Testing Requirements

- Tests must be runnable via tox
- Use `tests/testing_support/validators/` for validating collected metrics/traces
- Each test directory needs its own `conftest.py` with necessary fixtures
