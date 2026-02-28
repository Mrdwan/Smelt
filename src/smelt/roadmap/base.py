from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self


@dataclass
class Step:
    id: str
    description: str
    done: bool


class RoadmapStorage(ABC):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

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
    def reset_step(self, step_id: str) -> None:
        pass

    @abstractmethod
    def remove_step(self, step_id: str) -> None:
        pass

    @abstractmethod
    def all_steps(self) -> list[Step]:
        pass
