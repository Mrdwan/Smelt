class SmeltError(Exception):
    """Base exception for all Smelt errors."""


class RoadmapNotFoundError(SmeltError):
    pass


class NoStepsRemainingError(SmeltError):
    pass


class AgentNotFoundError(SmeltError):
    pass


class AgentError(SmeltError):
    pass


class StepNotFoundError(SmeltError):
    pass


class StorageError(SmeltError):
    pass


class PlanParseError(SmeltError):
    pass
