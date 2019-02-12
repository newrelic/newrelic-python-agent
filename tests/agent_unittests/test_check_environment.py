import tempfile
import os
import shutil
import sys
import pytest
import newrelic.core.agent as agent


@pytest.mark.parametrize('content', [{}, {'opt': [1, 2, 3]}])
def test_check_environment_failing(content):
    temp_dir = tempfile.mkdtemp()

    try:
        uwsgi_dir = os.path.join(temp_dir, 'uwsgi')
        init_file = os.path.join(uwsgi_dir, '__init__.py')
        os.makedirs(uwsgi_dir)
        with open(init_file, 'w') as f:
            for key, value in content.items():
                f.write("%s = %s" % (key, value))

        sys.path.insert(0, temp_dir)
        import uwsgi
        for key, value in content.items():
            assert getattr(uwsgi, key) == value

        agent.check_environment()
    finally:
        shutil.rmtree(temp_dir)
        sys.path.remove(temp_dir)
        del sys.modules['uwsgi']
