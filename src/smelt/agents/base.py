from abc import ABC, abstractmethod


class Agent(ABC):
    @abstractmethod
    def run(self, message: str, context_files: list[str]) -> bool:
        """Run the agent with the given message. Returns True on success."""
        pass
