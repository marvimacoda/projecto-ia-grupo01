"""Gerador de instâncias aleatórias do P8, reproduzíveis a partir de uma semente.

Semente do grupo: 2026 x 100 + nº do grupo (Pós-Laboral: + 50)
  -> Pós-Laboral, Grupo 1  =>  202651

Uso:  python gerador.py                (escreve instancias/<nivel>_<NN>.json)
      python gerador.py --n 5 --semente 202651
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random

SEMENTE_BASE = 2026 * 100 + 50 + 1      # 202651
N_INSTANCIAS = 5                        # Pós-Laboral: 5 por nível (Laboral: 10)

# nível -> (nº de nós da rede, intervalo do nº de avarias)
NIVEIS = {
    "pequena": dict(n_nos=20, avarias=(2, 3)),     # todos os algoritmos (incl. IDS) terminam
    "media":   dict(n_nos=22, avarias=(6, 8)),     # base do enunciado = 6 avarias; IDS já falha
    "grande":  dict(n_nos=26, avarias=(12, 13)),   # só as informadas (A*-h2, gulosa, WA*) terminam
}
TIPOS = ("poste", "isolador", "transformador")


def _ancestral(pai, a, b):
    """True se a é ancestral de b."""
    while b != -1:
        if b == a:
            return True
        b = pai[b]
    return False


def gerar_instancia(nivel: str, indice: int, semente: int = SEMENTE_BASE) -> dict:
    cfg = NIVEIS[nivel]
    rng = random.Random(f"{semente}:{nivel}:{indice}")   # determinístico
    n = cfg["n_nos"]
    k = rng.randint(*cfg["avarias"])

    # árvore radial: pai[i] < i
    pai = [-1] + [rng.randint(max(0, i - 5), i - 1) for i in range(1, n)]
    mw = [0] + [rng.randint(1, 9) for _ in range(1, n)]

    # k avarias (linhas pai[v]--v), com pelo menos um par aninhado
    for _ in range(200):
        nos = sorted(rng.sample(range(1, n), k))
        if any(_ancestral(pai, a, b) for a in nos for b in nos if a != b):
            break

    # locais: 0,1 armazéns; 2.. um por avaria; coordenadas e ruas
    coords = [(rng.uniform(0, 40), rng.uniform(0, 40)) for _ in range(2 + k)]
    locais = ["Armazem A", "Armazem B"] + [f"Local F{i + 1}" for i in range(k)]
    tempo = lambda i, j: max(2, round(0.7 * math.dist(coords[i], coords[j])))
    ruas = set()
    ordem = sorted(range(len(coords)), key=lambda i: coords[i][0])   # cadeia => conexo
    for a, b in zip(ordem, ordem[1:]):
        ruas.add((min(a, b), max(a, b)))
    for i in range(len(coords)):                                     # 2 vizinhos mais próximos
        viz = sorted((j for j in range(len(coords)) if j != i), key=lambda j: math.dist(coords[i], coords[j]))
        for j in viz[:2]:
            ruas.add((min(i, j), max(i, j)))
    ruas = [[a, b, tempo(a, b)] for a, b in sorted(ruas)]

    pesos = [None, "poste", "isolador", "transformador"]
    avarias = []
    for i, no in enumerate(nos):
        peca = rng.choices(pesos, weights=[25, 30, 25, 20])[0]
        avarias.append(dict(id=f"F{i + 1}", no=no, local=2 + i,
                            reparo_min=rng.randint(10, 40), peca=peca))

    # stock: cada peça necessária vai para um armazém aleatório (+ extras)
    armazens = [{t: 0 for t in TIPOS} for _ in range(2)]
    for a in avarias:
        if a["peca"]:
            armazens[rng.randint(0, 1)][a["peca"]] += 1
    for arm in armazens:
        for t in TIPOS:
            if rng.random() < 0.3:
                arm[t] += 1

    return dict(nome=f"{nivel}_{indice:02d}", nivel=nivel, indice=indice, semente=semente,
                n_nos=n, pai=pai, carga_mw=mw, locais=locais, ruas=ruas, avarias=avarias,
                armazens=armazens, capacidade=3, t_carga=2, inicio=0)


def gerar_todas(n_por_nivel: int = N_INSTANCIAS, semente: int = SEMENTE_BASE) -> list:
    return [gerar_instancia(nv, i, semente) for nv in NIVEIS for i in range(n_por_nivel)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=N_INSTANCIAS)
    ap.add_argument("--semente", type=int, default=SEMENTE_BASE)
    ap.add_argument("--saida", default="instancias")
    args = ap.parse_args()
    os.makedirs(args.saida, exist_ok=True)
    for inst in gerar_todas(args.n, args.semente):
        caminho = os.path.join(args.saida, inst["nome"] + ".json")
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(inst, f, indent=1, ensure_ascii=False)
        print("escrito", caminho, f"({len(inst['avarias'])} avarias)")


if __name__ == "__main__":
    main()
