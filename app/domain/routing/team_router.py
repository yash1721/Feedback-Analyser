from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RoutingResult:
    team: str
    matched_keyword: str | None = None


class TeamRouter(ABC):
    @abstractmethod
    def route(self, text: str) -> RoutingResult:
        raise NotImplementedError

