class NexVaultError(Exception):
    pass


class ValidationError(NexVaultError):
    pass


class InsufficientBalanceError(NexVaultError):
    pass


class OutOfStockError(NexVaultError):
    pass


class NotFoundError(NexVaultError):
    pass


class DuplicateProofError(NexVaultError):
    pass


class InvalidStateTransitionError(NexVaultError):
    pass


class UnauthorizedError(NexVaultError):
    pass
