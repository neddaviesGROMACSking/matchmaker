
from matchmaker import __version__
import pytest

@pytest.mark.asyncio
class TestBasic:
    def test_version(self):
        assert __version__ == '0.1.0'
