from unittest.mock import Mock

class SimpleNamespace:
    """A lightweight namespace that creates Mock objects for any undefined attribute.
    This mirrors the standard library's SimpleNamespace but ensures that attribute
    access for missing names returns a Mock, allowing test code to set
    ``mock_obj.attribute.return_value`` without pre‑creating the attribute.
    """
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"SimpleNamespace({self.__dict__})"

    def __getattr__(self, name):
        # Create a Mock for any missing attribute and store it for future use
        mock = Mock()
        setattr(self, name, mock)
        return mock
