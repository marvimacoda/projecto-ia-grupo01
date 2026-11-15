"""Heurísticas do P8 (energia não fornecida restante) + utilitários de análise.

Notação: R = conjunto de avarias reparadas, L(R) = MW sem energia, r_f = tempo
de reparo da avaria f, T_n = instante (a contar de agora) em que o nó n volta
a ter energia. Custo restante de qualquer plano = soma_n mw[n] * T_n.

h0 = 0
-----
Trivialmente admissível e consistente. A*(h0) = Custo Uniforme.

h1 (soma dos reparos no caminho)
--------------------------------
    h1(s) = soma_{n sem energia} mw[n] * soma_{f no caminho raiz->n, f por reparar} r_f
Admissível: a equipa só faz uma coisa de cada vez, logo T_n >= soma dos r_f das
avarias por reparar no caminho de n; somando mw[n]*T_n obtém-se h1 <= h*.
Consistente: deslocar/carregar não altera h1 e custa >= 0. Reparar f custa
r_f * L(R) e h1 desce r_f * (carga da subárvore de f); como toda a subárvore de
f está sem energia, carga(subárvore f) <= L(R)  =>  h1(s) <= c + h1(s').

h2 (melhor ordem de reparo, com deslocações)
--------------------------------------------
    h2(R, local) = min_f [ (dist(local, local_f) + r_f) * L(R) + h2(R+{f}, local_f) ]
É o custo óptimo de um problema RELAXADO: ignora as peças/armazéns (as peças
aparecem de graça) mas mantém tempos de deslocação mínimos e de reparo.
Admissível: qualquer plano real induz uma ordem de reparos; nessa ordem o
problema relaxado nunca demora mais (menos esperas), logo custa <= ao real.
Consistente: reparar -> equação de Bellman do relaxado (h2 <= c + h2(s'));
ir de l para l': pela desigualdade triangular dist(l,f) <= dist(l,l')+dist(l',f),
logo h2(R,l) <= dist(l,l')*L(R) + h2(R,l'); carregar não muda h2 e custa >= 0.
Domina h1: cada T_n do relaxado >= soma dos r_f do caminho de n.
"""
from __future__ import annotations

import heapq
import itertools
from collections import defaultdict, deque


def h0(p, s) -> int:
    return 0


def h1(p, s) -> int:
    v = p.cache_h1.get(s.reparadas)
    if v is None:
        nao = ~s.reparadas
        v = 0
        for n in range(1, p.n_nos):
            bits = p.pm[n] & nao
            if bits:
                v += p.mw[n] * p.soma_reparo[bits]
        p.cache_h1[s.reparadas] = v
    return v


def _h2_rec(p, mask: int, local: int) -> int:
    if mask == p.completo:
        return 0
    chave = (mask, local)
    v = p.cache_h2.get(chave)
    if v is None:
        L = p.carga_desligada(mask)
        v = None
        for f in range(p.k):
            if not (mask >> f & 1):
                loc_f = p.av_local[f]
                c = (p.dist[local][loc_f] + p.av_reparo[f]) * L + _h2_rec(p, mask | (1 << f), loc_f)
                if v is None or c < v:
                    v = c
        p.cache_h2[chave] = v
    return v


def h2(p, s) -> int:
    return _h2_rec(p, s.reparadas, s.local)


HEURISTICAS = {"h0": h0, "h1": h1, "h2": h2}


# ----------------------------------------------------------------- análise
def grafo_completo(p, max_estados: int = 400_000):
    """Enumera todos os estados alcançáveis e as arestas (s, custo, s2). Só para instâncias pequenas."""
    s0 = p.estado_inicial()
    vistos = {s0}
    fila = deque([s0])
    arestas = []
    while fila:
        s = fila.popleft()
        for a in p.accoes(s):
            s2 = p.resultado(s, a)
            arestas.append((s, p.custo(s, a, s2), s2))
            if s2 not in vistos:
                vistos.add(s2)
                if len(vistos) > max_estados:
                    raise RuntimeError("instância demasiado grande para enumeração completa")
                fila.append(s2)
    return vistos, arestas


def h_estrela_todos(p, estados, arestas) -> dict:
    """h*(s) para todos os estados: UCS 'para trás' a partir dos estados objectivo."""
    pred = defaultdict(list)
    for s, c, s2 in arestas:
        pred[s2].append((s, c))
    cont = itertools.count()
    dist = {}
    heap = [(0, next(cont), s) for s in estados if p.e_objectivo(s)]
    heapq.heapify(heap)
    while heap:
        d, _, s = heapq.heappop(heap)
        if s in dist:
            continue
        dist[s] = d
        for ant, c in pred[s]:
            if ant not in dist:
                heapq.heappush(heap, (d + c, next(cont), ant))
    return dist   # estados sem entrada = sem caminho até ao objectivo (h* = inf)


def ramificacao_efectiva(N: int, d: int, tol: float = 1e-10) -> float:
    """b* tal que N + 1 = 1 + b* + b*^2 + ... + b*^d  (bisecção)."""
    if d <= 0:
        return 1.0
    f = lambda b: sum(b ** i for i in range(d + 1)) - (N + 1)
    lo, hi = 1.0, float(max(N, 2))
    if f(lo) >= 0:
        return 1.0
    while f(hi) < 0:
        hi *= 2
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if f(mid) < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2
