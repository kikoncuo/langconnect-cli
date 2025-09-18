class MissingEnvironmentVariable(Exception):
    """Raised when a required environment variable is missing."""


class LangConnectRequestError(Exception):
    """Raised when a request to LangConnect fails irrecoverably."""
