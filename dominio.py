"""P8 - Equipa de reparação da rede eléctrica após ciclone.

MODELO
------
* Rede = árvore radial com raiz 0 (subestação). Cada nó n>0 tem uma carga
  mw[n] (MW) e a linha que o liga ao pai. Uma avaria é uma linha avariada
  (pai[n] -- n): desliga toda a subárvore de n.
* Locais = 2 armazéns (índices 0 e 1) + um local por avaria. As ruas têm
  tempos de deslocação (min); usamos a matriz de tempos mínimos (Floyd-Warshall).
* A equipa tem uma carrinha com capacidade para 3 peças (poste, isolador,
  transformador). Cada avaria pode exigir 1 peça do tipo indicado.
* Acções:  ("ir", destino)  |  ("carregar", tipo)  |  ("reparar", avaria)
* Custo de uma acção = duração(min) x carga ainda desligada (MW) no INÍCIO da
  acção (MW.min).  Logo o custo depende do que já foi reparado, mas só do
  estado actual -> o custo do caminho continua a ser uma soma de custos de
  passos (g aditivo) e o problema continua a ser um problema de caminho.

  Identidade útil (usada nas provas das heurísticas):
      custo total = soma_n  mw[n] x T_n
  em que T_n é o instante em que o nó n volta a ter energia.
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

import heuristicas
from problema import Problema

TIPOS = ("poste", "isolador", "transformador")
_INF = 10 ** 9


@dataclass(frozen=True, slots=True)
class EstadoRede:
    """Estado imutável e hashable.

    local     : índice do local onde a equipa está
    reparadas : máscara de bits das avarias já reparadas
    carga     : peças na carrinha (n_postes, n_isoladores, n_transformadores)
    stock     : stock restante nos armazéns (A_p, A_i, A_t, B_p, B_i, B_t)

    Não perde informação: com estes 4 campos sabe-se que acções são legais e
    quanta energia está por fornecer. O tempo NÃO entra no estado: acumula-se
    em g (custo do caminho).
    """
    local: int
    reparadas: int
    carga: tuple
    stock: tuple


def carregar_instancia(caminho_ficheiro: str) -> dict:
    with open(caminho_ficheiro, encoding="utf-8") as f:
        return json.load(f)


class ProblemaRede(Problema):
    def __init__(self, inst: dict):
        self.inst = inst
        self.n_nos = inst["n_nos"]
        self.pai = inst["pai"]
        self.mw = inst["carga_mw"]
        self.locais = inst["locais"]
        self.n_locais = len(self.locais)
        self.n_arm = len(inst["armazens"])
        self.capacidade = inst["capacidade"]
        self.t_carga = inst["t_carga"]
        self.stock_inicial = tuple(a[t] for a in inst["armazens"] for t in TIPOS)

        av = inst["avarias"]
        self.avarias = av
        self.k = len(av)
        self.completo = (1 << self.k) - 1
        self.av_no = [a["no"] for a in av]
        self.av_local = [a["local"] for a in av]
        self.av_reparo = [a["reparo_min"] for a in av]
        self.av_tipo = [TIPOS.index(a["peca"]) if a["peca"] else None for a in av]
        self.av_em_local = {a["local"]: i for i, a in enumerate(av)}
        self.mascara_tipo = [0, 0, 0]
        for i, t in enumerate(self.av_tipo):
            if t is not None:
                self.mascara_tipo[t] |= 1 << i

        # pm[n] = máscara das avarias no caminho raiz -> n (inclui a linha de n)
        bit_do_no = {n: i for i, n in enumerate(self.av_no)}
        assert all(self.pai[n] < n for n in range(1, self.n_nos)), "pai[n] < n"
        self.pm = [0] * self.n_nos
        for n in range(1, self.n_nos):
            self.pm[n] = self.pm[self.pai[n]] | (1 << bit_do_no[n] if n in bit_do_no else 0)
        # carga a jusante de cada avaria (MW desligados só por essa avaria/subárvore)
        self.carga_subarvore = [
            sum(self.mw[n] for n in range(1, self.n_nos) if self.pm[n] >> i & 1)
            for i in range(self.k)
        ]
        # soma dos tempos de reparo para cada subconjunto de avarias
        self.soma_reparo = [0] * (1 << self.k)
        for m in range(1, 1 << self.k):
            baixo = (m & -m).bit_length() - 1
            self.soma_reparo[m] = self.soma_reparo[m & (m - 1)] + self.av_reparo[baixo]

        # tempos mínimos de deslocação entre locais
        d = [[_INF] * self.n_locais for _ in range(self.n_locais)]
        for i in range(self.n_locais):
            d[i][i] = 0
        for a, b, t in inst["ruas"]:
            d[a][b] = min(d[a][b], t)
            d[b][a] = min(d[b][a], t)
        for m in range(self.n_locais):
            for i in range(self.n_locais):
                for j in range(self.n_locais):
                    if d[i][m] + d[m][j] < d[i][j]:
                        d[i][j] = d[i][m] + d[m][j]
        assert all(d[i][j] < _INF for i in range(self.n_locais) for j in range(self.n_locais))
        self.dist = d

        # caches (por instância)
        self._cache_L = {}
        self.cache_h1 = {}
        self.cache_h2 = {}

    # ------------------------------------------------------------------ util
    def carga_desligada(self, reparadas: int) -> int:
        """MW sem energia quando o conjunto de avarias reparadas é `reparadas`."""
        v = self._cache_L.get(reparadas)
        if v is None:
            nao = ~reparadas
            v = sum(self.mw[n] for n in range(1, self.n_nos) if self.pm[n] & nao)
            self._cache_L[reparadas] = v
        return v

    def por_reparar_tipo(self, s: EstadoRede, t: int) -> int:
        """Nº de avarias por reparar que precisam de uma peça do tipo t."""
        return (self.mascara_tipo[t] & ~s.reparadas).bit_count()

    def duracao(self, s: EstadoRede, a) -> int:
        if a[0] == "ir":
            return self.dist[s.local][a[1]]
        if a[0] == "carregar":
            return self.t_carga
        return self.av_reparo[a[1]]

    # ------------------------------------------------------- interface Problema
    def estado_inicial(self) -> EstadoRede:
        return EstadoRede(self.inst.get("inicio", 0), 0, (0, 0, 0), self.stock_inicial)

    def e_objectivo(self, s: EstadoRede) -> bool:
        return s.reparadas == self.completo

    def accoes(self, s: EstadoRede) -> list:
        acc = []
        for d in range(self.n_locais):                      # deslocações
            if d != s.local:
                acc.append(("ir", d))
        if s.local < self.n_arm and sum(s.carga) < self.capacidade:   # carregar
            for t in range(3):
                # poda segura: só carrega peças ainda necessárias
                if s.stock[3 * s.local + t] > 0 and s.carga[t] < self.por_reparar_tipo(s, t):
                    acc.append(("carregar", t))
        f = self.av_em_local.get(s.local)                  # reparar
        if f is not None and not (s.reparadas >> f & 1):
            t = self.av_tipo[f]
            if t is None or s.carga[t] > 0:
                acc.append(("reparar", f))
        return acc

    def resultado(self, s: EstadoRede, a) -> EstadoRede:
        tipo = a[0]
        if tipo == "ir":
            return EstadoRede(a[1], s.reparadas, s.carga, s.stock)
        if tipo == "carregar":
            t = a[1]
            carga = list(s.carga); carga[t] += 1
            stock = list(s.stock); stock[3 * s.local + t] -= 1
            return EstadoRede(s.local, s.reparadas, tuple(carga), tuple(stock))
        f = a[1]
        t = self.av_tipo[f]
        carga = s.carga
        if t is not None:
            c = list(carga); c[t] -= 1
            carga = tuple(c)
        return EstadoRede(s.local, s.reparadas | (1 << f), carga, s.stock)

    def custo(self, s: EstadoRede, a, s2: EstadoRede) -> int:
        return self.duracao(s, a) * self.carga_desligada(s.reparadas)

    def heuristica(self, s: EstadoRede, nome: str = "h0") -> float:
        return heuristicas.HEURISTICAS[nome](self, s)

    # -------------------------------------------------------- apresentação
    def descrever_accao(self, s: EstadoRede, a) -> str:
        if a[0] == "ir":
            return f"ir para {self.locais[a[1]]} ({self.dist[s.local][a[1]]} min)"
        if a[0] == "carregar":
            return f"carregar 1 {TIPOS[a[1]]} em {self.locais[s.local]} ({self.t_carga} min)"
        av = self.avarias[a[1]]
        return f"reparar {av['id']} (nó {av['no']}) em {self.av_reparo[a[1]]} min"

    def resumo_estado(self, s: EstadoRede) -> str:
        feitas = [self.avarias[i]["id"] for i in range(self.k) if s.reparadas >> i & 1]
        return (f"local={self.locais[s.local]} | carrinha(p,i,t)={s.carga} | "
                f"reparadas={feitas or '-'} | sem energia={self.carga_desligada(s.reparadas)} MW")

    def desenhar(self, s: EstadoRede) -> str:
        """Visualização ASCII da rede: [OK]=energizado, [--]=sem energia, XX=avaria."""
        filhos = defaultdict(list)
        for n in range(1, self.n_nos):
            filhos[self.pai[n]].append(n)
        nao = ~s.reparadas
        bit = {n: i for i, n in enumerate(self.av_no)}
        linhas = [self.resumo_estado(s), "Subestacao (no 0)"]

        def rec(n, prefixo):
            for idx, c in enumerate(filhos[n]):
                ultimo = idx == len(filhos[n]) - 1
                estado = "[--]" if self.pm[c] & nao else "[OK]"
                txt = f"{prefixo}{'+-- ' if ultimo else '|-- '}{estado} no {c} ({self.mw[c]} MW)"
                if c in bit:
                    i = bit[c]
                    av = self.avarias[i]
                    if s.reparadas >> i & 1:
                        txt += f"  <linha reparada {av['id']}>"
                    else:
                        txt += f"  XX AVARIA {av['id']} ({av['peca'] or 'sem peca'}, {av['reparo_min']} min, local {self.locais[av['local']]})"
                linhas.append(txt)
                rec(c, prefixo + ("    " if ultimo else "|   "))

        rec(0, "")
        return "\n".join(linhas)
