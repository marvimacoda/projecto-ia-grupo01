"""Interface genérica de um problema de busca + estrutura de nó.

Os algoritmos de busca (buscas.py) só conhecem esta interface: trocar de
problema não obriga a mudar nenhum algoritmo.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


class Problema(ABC):
    """Formalização de um problema de busca no espaço de estados."""

    @abstractmethod
    def estado_inicial(self) -> Any:
        """Devolve o estado inicial (imutável e hashable)."""

    @abstractmethod
    def accoes(self, s: Any) -> list:
        """Lista de acções aplicáveis no estado s."""

    @abstractmethod
    def resultado(self, s: Any, a: Any) -> Any:
        """Modelo de transição: estado que resulta de aplicar a em s."""

    @abstractmethod
    def custo(self, s: Any, a: Any, s2: Any) -> float:
        """Custo (>= 0) do passo s --a--> s2."""

    @abstractmethod
    def e_objectivo(self, s: Any) -> bool:
        """Teste de objectivo."""

    def heuristica(self, s: Any, nome: str = "h0") -> float:
        """Estimativa do custo restante a partir de s (h0 = 0 por omissão)."""
        return 0


@dataclass(frozen=True, slots=True, eq=False)
class No:
    """Nó da árvore de busca."""
    estado: Any
    pai: Optional["No"]
    accao: Any
    g: float
    profundidade: int


def caminho(no: No) -> list:
    """Reconstrói a solução como lista [(None, s0), (a1, s1), ..., (an, sn)]."""
    passos = []
    while no is not None:
        passos.append((no.accao, no.estado))
        no = no.pai
    passos.reverse()
    return passos
