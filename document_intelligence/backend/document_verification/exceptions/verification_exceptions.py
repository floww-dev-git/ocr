from common.exceptions.base import BaseExceptionClass


class IssuerAdapterNotRegistered(BaseExceptionClass):
    """The catalog points a document type at an issuer this build cannot call.

    Deliberately not folded into the `unreachable` outcome. An unreachable issuer
    tells the officer the department did not answer and offers a retry, which would
    be a lie here and would have them retrying a call that does not exist.
    """

    def __init__(self, issuer_service_id: str):
        self.issuer_service_id = issuer_service_id
