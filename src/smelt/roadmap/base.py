from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Step:
    id: str
    description: str
    done: bool


class RoadmapStorage(ABC):
    @abstractmethod
    def close(self) -> None:
        """Close any resources used by the roadmap."""
        pass

    @abstractmethod
    def add_step(self, description: str) -> str:
        pass

    @abstractmethod
    def next_step(self) -> Step | None:
        pass

    @abstractmethod
    def mark_done(self, step_id: str) -> None:
        pass

    @abstractmethod
    def all_steps(self) -> list[Step]:
        pass
