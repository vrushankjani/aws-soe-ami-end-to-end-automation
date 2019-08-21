import pytest

from mock import MagicMock

class CodePipelineClientMock(object):
    def __init__(self, monkeypatch, module_path):
        self.success_mock = MagicMock()
        self.failure_mock = MagicMock()

        monkeypatch.setattr(
            '%s.codepipeline_client.put_job_success_result' % module_path,
            self.success_mock
        )

        monkeypatch.setattr(
            '%s.codepipeline_client.put_job_failure_result' % module_path,
            self.failure_mock
        )

    def get_success_mock(self):
        return self.success_mock

    def get_failure_mock(self):
        return self.failure_mock

    def put_job_success_result(self, *args, **kwargs):
        return self.success_mock(*args, **kwargs)

    def put_job_failure_result(self, *args, **kwargs):
        return self.failure_mock(*args, **kwargs)

@pytest.fixture
def codepipeline_client_mock(request, monkeypatch):
    """
    """
    module_path = getattr(request.module, "MODULE_PATH")
    mock_client = CodePipelineClientMock(monkeypatch, module_path)
    monkeypatch.setattr(
        '%s.codepipeline_client' % module_path,
        mock_client
    )
    return mock_client


