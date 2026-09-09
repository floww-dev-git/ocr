import abc


class FailureReporterInterface(abc.ABC):
    """Records a fault the officer was shielded from.

    An interactor that swallows an exception to keep the rest of the run alive
    still owes a developer the detail. Logging is I/O, so it travels through a
    port rather than being called from business logic.
    """

    @abc.abstractmethod
    def report(self, message: str, error: BaseException) -> None:
        pass
