from abc import ABC, abstractmethod
from collections.abc import Callable


class BasePostprocessor(ABC):
    """Base class for all postprocessors."""

    @property
    @abstractmethod
    def info(self) -> str:
        """A short description of the postprocessor."""
        pass

    def __init__(self, ai: Callable, config: dict) -> None:
        self.ai = ai
        self.config = config
