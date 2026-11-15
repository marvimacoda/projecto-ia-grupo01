"""Os 7 algoritmos de busca (genéricos: só conhecem a interface Problema).

BFS, DFS, IDS, Custo Uniforme (UCS), Gulosa, A* e A* Ponderado (WA*).
Cada algoritmo recebe (problema, ctx) e devolve o No objectivo ou None.
`resolver(...)` corre um algoritmo com limites de tempo/memória e devolve
um Resultado com as métricas pedidas.
"""
from __future__ import annotations

import heapq
import itertools
import time
import tracemalloc
from collections import deque
from dataclasses import dataclass
from typing import Optional

from problema import No, Problema, caminho


class LimiteExcedido(Exception):
    pass


@dataclass
class Limites:
    tempo: float = 60.0                 # segundos
    memoria: int = 2 * 1024 ** 3        # bytes (medidos com tracemalloc)
    profundidade: int = 60              # DFS / IDS (nº máximo de acções)


@dataclass
class Resultado:
    algoritmo: str
    estado: str                         # "ok" | "falhou" | "sem_solucao"
    motivo: str = ""
    solucao: Optional[list] = None
    custo: Optional[float] = None
    comprimento: Optional[int] = None
    expandidos: int = 0
    gerados: int = 0
    max_fronteira: int = 0
    reexpandidos: int = 0
    tempo: float = 0.0
    memoria_pico: int = 0


class Contexto:
    """Contadores + verificação periódica dos limites."""

    def __init__(self, limites: Limites):
        self.limites = limites
        self.t0 = time.perf_counter()
        self.expandidos = 0
        self.gerados = 0
        self.max_fronteira = 0
        self.reexpandidos = 0
        self.cortou = False             # DFS/IDS: o limite de profundidade cortou ramos?
        self._n = 0

    def tick(self):
        self._n += 1
        if self._n & 127 == 0:
            self.verificar()

    def verificar(self):
        if time.perf_counter() - self.t0 > self.limites.tempo:
            raise LimiteExcedido("tempo")
        if tracemalloc.is_tracing() and tracemalloc.get_traced_memory()[0] > self.limites.memoria:
            raise LimiteExcedido("memoria")


def _filho(p: Problema, no: No, a) -> No:
    s2 = p.resultado(no.estado, a)
    return No(s2, no, a, no.g + p.custo(no.estado, a, s2), no.profundidade + 1)


# --------------------------------------------------------------------- BFS
def bfs(p: Problema, ctx: Contexto):
    """Busca em largura, com teste de objectivo na GERAÇÃO.

    Devolve a solução com menos acções, NÃO a de menor custo: como os custos
    dos passos são variáveis, o caminho mais curto em nº de passos pode custar
    mais (p.ex. duas deslocações baratas vs um reparo longo com muita carga
    desligada). Só seria óptima com custo de passo constante.
    """
    s0 = p.estado_inicial()
    no0 = No(s0, None, None, 0, 0)
    ctx.gerados = 1
    if p.e_objectivo(s0):
        return no0
    fronteira = deque([no0])
    visitados = {s0}
    while fronteira:
        no = fronteira.popleft()
        ctx.expandidos += 1
        ctx.tick()
        for a in p.accoes(no.estado):
            filho = _filho(p, no, a)
            if filho.estado in visitados:
                continue
            ctx.gerados += 1
            if p.e_objectivo(filho.estado):          # teste na geração
                return filho
            visitados.add(filho.estado)
            fronteira.append(filho)
        ctx.max_fronteira = max(ctx.max_fronteira, len(fronteira))
    return None


# --------------------------------------------------------------- DFS / IDS
def _sem_ciclo(p: Problema, no: No) -> list:
    """Sucessores cujo estado não aparece já no caminho raiz -> no."""
    res = []
    for a in p.accoes(no.estado):
        s2 = p.resultado(no.estado, a)
        n = no
        while n is not None:
            if n.estado == s2:
                break
            n = n.pai
        else:
            res.append(No(s2, no, a, no.g + p.custo(no.estado, a, s2), no.profundidade + 1))
    return res


def _dfs_limitado(p: Problema, ctx: Contexto, limite: int, vistos: Optional[set] = None):
    pilha = [No(p.estado_inicial(), None, None, 0, 0)]
    ctx.gerados += 1
    while pilha:
        no = pilha.pop()
        if p.e_objectivo(no.estado):
            return no
        ctx.expandidos += 1
        ctx.tick()
        if vistos is not None:                       # instrumentação do IDS
            if no.estado in vistos:
                ctx.reexpandidos += 1
            else:
                vistos.add(no.estado)
        filhos = _sem_ciclo(p, no)
        if no.profundidade >= limite:
            if filhos:
                ctx.cortou = True
            continue
        ctx.gerados += len(filhos)
        pilha.extend(reversed(filhos))               # explora na ordem das acções
        ctx.max_fronteira = max(ctx.max_fronteira, len(pilha))
    return None


def dfs(p: Problema, ctx: Contexto):
    """Busca em profundidade: controlo de ciclos no caminho + limite de profundidade
    configurável (ctx.limites.profundidade). Não é completa com limite finito nem óptima."""
    return _dfs_limitado(p, ctx, ctx.limites.profundidade)


def ids(p: Problema, ctx: Contexto):
    """Aprofundamento iterativo. Reporta ctx.reexpandidos = expansões de estados
    que já tinham sido expandidos antes (nas iterações anteriores ou na mesma)."""
    vistos = set()
    for limite in range(ctx.limites.profundidade + 1):
        ctx.cortou = False
        no = _dfs_limitado(p, ctx, limite, vistos)
        if no is not None:
            return no
        if not ctx.cortou:                           # espaço esgotado sem cortes
            return None
    return None                                       # ctx.cortou=True => falhou por profundidade


# --------------------------------------------------------------------- UCS
def ucs(p: Problema, ctx: Contexto):
    """Custo uniforme com heapq. Entradas obsoletas (estado reencontrado com g
    menor) são descartadas ao sair da fila (lazy deletion)."""
    s0 = p.estado_inicial()
    no0 = No(s0, None, None, 0, 0)
    cont = itertools.count()
    heap = [(0, next(cont), no0)]
    melhor_g = {s0: 0}
    ctx.gerados = 1
    while heap:
        g, _, no = heapq.heappop(heap)
        if g > melhor_g[no.estado]:                   # entrada obsoleta
            continue
        if p.e_objectivo(no.estado):                  # teste na expansão
            return no
        ctx.expandidos += 1
        ctx.tick()
        for a in p.accoes(no.estado):
            filho = _filho(p, no, a)
            if filho.estado not in melhor_g or filho.g < melhor_g[filho.estado]:
                melhor_g[filho.estado] = filho.g
                heapq.heappush(heap, (filho.g, next(cont), filho))
                ctx.gerados += 1
        ctx.max_fronteira = max(ctx.max_fronteira, len(heap))
    return None


# ------------------------------------------------------------------ Gulosa
def gulosa(p: Problema, ctx: Contexto, h: str = "h1"):
    """Gulosa pela melhor escolha: f = h(n). Versão em grafo, não é óptima."""
    s0 = p.estado_inicial()
    no0 = No(s0, None, None, 0, 0)
    cont = itertools.count()
    heap = [(p.heuristica(s0, h), next(cont), no0)]
    visitados = {s0}
    ctx.gerados = 1
    while heap:
        _, _, no = heapq.heappop(heap)
        if p.e_objectivo(no.estado):
            return no
        ctx.expandidos += 1
        ctx.tick()
        for a in p.accoes(no.estado):
            filho = _filho(p, no, a)
            if filho.estado in visitados:
                continue
            visitados.add(filho.estado)
            ctx.gerados += 1
            heapq.heappush(heap, (p.heuristica(filho.estado, h), next(cont), filho))
        ctx.max_fronteira = max(ctx.max_fronteira, len(heap))
    return None


# ---------------------------------------------------------- A* / A* ponderado
def a_estrela(p: Problema, ctx: Contexto, h: str = "h2", w: float = 1.0):
    """A* em grafo (conjunto de fechados), f = g + w*h.

    w = 1  -> A* (óptimo se h admissível; com h consistente nunca reabre nós).
    w > 1  -> A* Ponderado: custo <= w * custo óptimo (h admissível), em geral
              expande muito menos nós. Se um fechado é reencontrado com menor g,
              é reaberto.
    """
    s0 = p.estado_inicial()
    no0 = No(s0, None, None, 0, 0)
    cont = itertools.count()
    h0_ = p.heuristica(s0, h)
    heap = [(w * h0_, h0_, next(cont), no0)]          # (f, h, desempate, no)
    melhor_g = {s0: 0}
    fechados = set()
    ctx.gerados = 1
    while heap:
        _, _, _, no = heapq.heappop(heap)
        if no.g > melhor_g[no.estado]:                # entrada obsoleta
            continue
        if p.e_objectivo(no.estado):
            return no
        fechados.add(no.estado)
        ctx.expandidos += 1
        ctx.tick()
        for a in p.accoes(no.estado):
            filho = _filho(p, no, a)
            s2 = filho.estado
            if s2 in melhor_g and filho.g >= melhor_g[s2]:
                continue
            fechados.discard(s2)                       # reabre, se estava fechado
            melhor_g[s2] = filho.g
            hv = p.heuristica(s2, h)
            heapq.heappush(heap, (filho.g + w * hv, hv, next(cont), filho))
            ctx.gerados += 1
        ctx.max_fronteira = max(ctx.max_fronteira, len(heap))
    return None


# ---------------------------------------------------------------- execução
ALGORITMOS = ("BFS", "DFS", "IDS", "UCS", "Gulosa", "A*", "WA*")


def resolver(p: Problema, algoritmo: str, h: str = "h2", w: float = 1.0,
             limites: Optional[Limites] = None, medir_memoria: bool = True) -> Resultado:
    """Corre `algoritmo` em `p` respeitando os limites; nunca omite falhas."""
    limites = limites or Limites()
    ctx = Contexto(limites)
    ja_tracava = tracemalloc.is_tracing()
    if medir_memoria and not ja_tracava:
        tracemalloc.start()
    elif medir_memoria:
        tracemalloc.reset_peak()
    ctx.t0 = time.perf_counter()
    estado, motivo, no = "ok", "", None
    try:
        if algoritmo == "BFS":
            no = bfs(p, ctx)
        elif algoritmo == "DFS":
            no = dfs(p, ctx)
        elif algoritmo == "IDS":
            no = ids(p, ctx)
        elif algoritmo == "UCS":
            no = ucs(p, ctx)
        elif algoritmo == "Gulosa":
            no = gulosa(p, ctx, h)
        elif algoritmo == "A*":
            no = a_estrela(p, ctx, h, 1.0)
        elif algoritmo == "WA*":
            no = a_estrela(p, ctx, h, w)
        else:
            raise ValueError(f"algoritmo desconhecido: {algoritmo}")
        if no is None:
            if ctx.cortou:
                estado, motivo = "falhou", "limite de profundidade"
            else:
                estado, motivo = "sem_solucao", "espaço de estados esgotado"
    except LimiteExcedido as e:
        estado, motivo = "falhou", str(e)
    except MemoryError:
        estado, motivo = "falhou", "memoria"
    tempo = time.perf_counter() - ctx.t0
    pico = tracemalloc.get_traced_memory()[1] if medir_memoria else 0
    if medir_memoria and not ja_tracava:
        tracemalloc.stop()
    r = Resultado(algoritmo, estado, motivo, None, None, None, ctx.expandidos, ctx.gerados,
                  ctx.max_fronteira, ctx.reexpandidos, tempo, pico)
    if no is not None:
        r.solucao, r.custo, r.comprimento = caminho(no), no.g, no.profundidade
    return r





