"""Settings for the test suite: the real settings over a hermetic config.

`use_test_config` ignores the developer's `.env` and shell, so every adapter is
`simulated` and no test can reach the network by accident.
"""

from core.config import use_test_config

use_test_config()

from server.settings import *  # noqa: E402, F403
