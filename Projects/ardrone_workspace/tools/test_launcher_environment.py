"""Regression check for a shell with both image and local overlays sourced."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class LauncherEnvironmentTest(unittest.TestCase):
    def test_local_overlay_takes_precedence_after_repeated_sourcing(self):
        helper = Path(__file__).with_name('prepare_workspace.sh').resolve()
        with tempfile.TemporaryDirectory(prefix='launcher workspace ') as directory:
            workspace = Path(directory)
            (workspace / 'install').mkdir()
            # Model colcon's prepend-non-duplicate behavior: an existing entry
            # is left in place, even when another overlay now precedes it.
            (workspace / 'install/local_setup.bash').write_text('''
for variable in AMENT_PREFIX_PATH PYTHONPATH; do
    case "$variable" in
        AMENT_PREFIX_PATH) entry="$workspace/install/ardrone_gazebo" ;;
        PYTHONPATH) entry="$workspace/build/ardrone_gazebo" ;;
    esac
    case ":${!variable}:" in
        *":$entry:"*) ;;
        *) export "$variable=$entry:${!variable}" ;;
    esac
done
''')
            result = subprocess.run(['bash', '-c', '''
set -euo pipefail
workspace=$1
source "$2"
for attempt in 1 2; do
    export AMENT_PREFIX_PATH="/opt/image:$workspace/install/ardrone_gazebo:/opt/ros"
    export PYTHONPATH="/opt/image/python:$workspace/build/ardrone_gazebo:/opt/ros/python"
    source_local_workspace
    [[ "$AMENT_PREFIX_PATH" == "$workspace/install/ardrone_gazebo:/opt/image:/opt/ros" ]]
    [[ "$PYTHONPATH" == "$workspace/build/ardrone_gazebo:/opt/image/python:/opt/ros/python" ]]
done
''', 'check', str(workspace), str(helper)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
