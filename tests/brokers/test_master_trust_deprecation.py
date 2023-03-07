import warnings

warnings.simplefilter("always")


def test_deprecation_warning():
    with warnings.catch_warnings(record=True) as w:
        from omspy.brokers.master_trust import MasterTrust

        message = str(w[-1].message).strip("\n")
        assert (
            message
            == "This MasterTrust broker module would be removed from version 0.16.0"
        )
