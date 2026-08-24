class TestRequiredStep:
    """#2242: missing step ids raise a clear error, not StopIteration."""

    @staticmethod
    def _stub(steps):
        from attune.wizards.base import BaseWizard

        class _Stub:
            _find_step = BaseWizard._find_step
            _required_step = BaseWizard._required_step

            def __init__(self, inner_steps):
                self.steps = inner_steps

        return _Stub(steps)

    def test_missing_step_raises_value_error(self):
        from types import SimpleNamespace

        stub = self._stub([SimpleNamespace(id="present")])
        try:
            stub._required_step("absent")
        except ValueError as exc:
            assert "absent" in str(exc) and "present" in str(exc)
        else:
            raise AssertionError("expected ValueError")

    def test_present_step_returned(self):
        from types import SimpleNamespace

        step = SimpleNamespace(id="scan")
        stub = self._stub([step])
        assert stub._required_step("scan") is step
