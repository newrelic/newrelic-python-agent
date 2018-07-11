Agent Benchmarks
----------------

This folder should contain a directed set of benchmarks to measure the overhead introduced by components of the agent. The benchmarks are run through [asv](https://github.com/airspeed-velocity/asv/).


Running
--------

```bash
virtualenv -p $(which python3.6) venv
source venv/bin/activate
pip install asv
pip install -e .

asv run -E existing:venv/bin/python
```
