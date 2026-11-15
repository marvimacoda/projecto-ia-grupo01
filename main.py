"""Menu do projecto P8 (equipa de reparação da rede eléctrica).

Interactivo:   python main.py
Directo:       python main.py --instancia instancias/pequena_00.json --algoritmo "A*" --h h2
               python main.py --nivel media --indice 1 --algoritmo WA* --w 2 --passos
"""
from __future__ import annotations

import argparse
import glob
import os

import gerador
from buscas import ALGORITMOS, Limites, resolver
from dominio import ProblemaRede, carregar_instancia
from experiencias import regra_maior_carga


def mostrar_solucao(p: ProblemaRede, r, passos: bool = True):
    if r.estado != "ok":
        print(f"\n>> {r.algoritmo}: {r.estado.upper()} ({r.motivo}) "
              f"[expandidos={r.expandidos}, tempo={r.tempo:.1f}s]")
        return
    print(f"\n>> {r.algoritmo}: solução com {r.comprimento} acções, custo {r.custo} MW.min")
    if passos:
        acc_total, t_total = 0, 0
        s = r.solucao[0][1]
        for i, (a, s2) in enumerate(r.solucao[1:], 1):
            c, d = p.custo(s, a, s2), p.duracao(s, a)
            acc_total += c
            t_total += d
            print(f"{i:>3}. t={t_total:>4} min | {p.descrever_accao(s, a):<48} | custo {c:>5} | acum. {acc_total:>6}")
            print(f"       -> {p.resumo_estado(s2)}")
            s = s2
        print("\nEstado final:")
        print(p.desenhar(s))
    print(f"\nMétricas: custo={r.custo} | comprimento={r.comprimento} | expandidos={r.expandidos} | "
          f"gerados={r.gerados} | fronteira máx.={r.max_fronteira} | reexpandidos={r.reexpandidos} | "
          f"tempo={r.tempo:.3f}s | memória pico={r.memoria_pico / 1e6:.2f} MB")


def pedir(texto, opcoes=None, defeito=None):
    while True:
        v = input(f"{texto}" + (f" [{defeito}]" if defeito is not None else "") + ": ").strip()
        if not v and defeito is not None:
            return defeito
        if opcoes is None or v in opcoes:
            return v
        print("  opção inválida")


def menu():
    inst, p = None, None
    alg, h, w = "A*", "h2", 1.0
    lim = Limites()
    while True:
        print("\n=== P8: reparação da rede eléctrica após ciclone ===")
        print(f" instância: {inst['nome'] if inst else '(nenhuma)'} | algoritmo: {alg} h={h} w={w} | "
              f"limites: {lim.tempo:g}s, {lim.memoria / 1024 ** 3:g}GB, prof.={lim.profundidade}")
        print(" 1) escolher instância (ficheiro)   2) gerar instância (nível/índice)")
        print(" 3) escolher algoritmo / heurística / limites")
        print(" 4) resolver e mostrar solução passo a passo")
        print(" 5) mostrar estado inicial          6) comparar com a regra 'maior carga'")
        print(" 0) sair")
        op = pedir("opção", {"0", "1", "2", "3", "4", "5", "6"})
        if op == "0":
            return
        if op == "1":
            ficheiros = sorted(glob.glob("instancias/*.json"))
            for i, f in enumerate(ficheiros):
                print(f"  {i}) {os.path.basename(f)}")
            i = int(pedir("número", {str(i) for i in range(len(ficheiros))}))
            inst = carregar_instancia(ficheiros[i])
        elif op == "2":
            nivel = pedir("nível (pequena/media/grande)", set(gerador.NIVEIS))
            idx = int(pedir("índice", defeito="0"))
            sem = int(pedir("semente", defeito=str(gerador.SEMENTE_BASE)))
            inst = gerador.gerar_instancia(nivel, idx, sem)
        elif op == "3":
            alg = pedir(f"algoritmo {ALGORITMOS}", set(ALGORITMOS), alg)
            if alg in ("Gulosa", "A*", "WA*"):
                h = pedir("heurística (h0/h1/h2)", {"h0", "h1", "h2"}, h)
            if alg == "WA*":
                w = float(pedir("peso w", defeito=str(w if w > 1 else 2.0)))
            lim.tempo = float(pedir("limite de tempo (s)", defeito=str(lim.tempo)))
            lim.memoria = int(float(pedir("limite de memória (GB)", defeito=str(lim.memoria / 1024 ** 3))) * 1024 ** 3)
            lim.profundidade = int(pedir("profundidade máx. (DFS/IDS)", defeito=str(lim.profundidade)))
        elif inst is None:
            print("  escolha primeiro uma instância (opção 1 ou 2)")
        else:
            p = ProblemaRede(inst)
            if op == "4":
                mostrar_solucao(p, resolver(p, alg, h, w, lim))
            elif op == "5":
                print(p.desenhar(p.estado_inicial()))
            elif op == "6":
                otimo = resolver(ProblemaRede(inst), "A*", "h2", 1.0, lim)
                c_regra = regra_maior_carga(ProblemaRede(inst))
                if otimo.estado == "ok":
                    print(f"regra 'maior carga': {c_regra} | óptimo (A*-h2): {otimo.custo} | "
                          f"regra é {100 * (c_regra / otimo.custo - 1):.1f}% pior")
                else:
                    print(f"regra 'maior carga': {c_regra} | A*-h2 falhou ({otimo.motivo})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instancia")
    ap.add_argument("--nivel", choices=list(gerador.NIVEIS))
    ap.add_argument("--indice", type=int, default=0)
    ap.add_argument("--algoritmo", choices=ALGORITMOS)
    ap.add_argument("--h", default="h2", choices=["h0", "h1", "h2"])
    ap.add_argument("--w", type=float, default=1.0)
    ap.add_argument("--limite-tempo", type=float, default=60.0)
    ap.add_argument("--passos", action="store_true", help="mostra a solução passo a passo")
    a = ap.parse_args()
    if not a.algoritmo:
        return menu()
    inst = carregar_instancia(a.instancia) if a.instancia else gerador.gerar_instancia(a.nivel or "pequena", a.indice)
    p = ProblemaRede(inst)
    if a.passos:
        print(p.desenhar(p.estado_inicial()))
    mostrar_solucao(p, resolver(p, a.algoritmo, a.h, a.w, Limites(tempo=a.limite_tempo)), a.passos)


if __name__ == "__main__":
    main()
