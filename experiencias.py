"""Bateria de experiências: 3 níveis x 5 instâncias x 12 configurações.

Uso:   python experiencias.py                      (limites do enunciado: 60 s, 2 GB)
       python experiencias.py --limite-tempo 20    (execução mais rápida)

Saídas (pasta resultados/):
  resultados.csv          uma linha por (instância, algoritmo) - as falhas ficam registadas
  resumo_por_nivel.csv    médias por nível/algoritmo
  regra_maior_carga.csv   ordem óptima vs regra simples "reparar primeiro a maior carga"
  grafico_nos_expandidos.png, grafico_tempo.png, grafico_custo_vs_optimo.png
Nota: o tempo inclui o overhead do tracemalloc (igual para todos os algoritmos).
"""
from __future__ import annotations

import argparse
import os

import pandas as pd

import gerador
import heuristicas
from buscas import Limites, resolver
from dominio import ProblemaRede

CONFIGS = [  # (algoritmo, heurística, w)
    ("BFS", None, 1.0), ("DFS", None, 1.0), ("IDS", None, 1.0), ("UCS", None, 1.0),
    ("Gulosa", "h1", 1.0), ("Gulosa", "h2", 1.0),
    ("A*", "h0", 1.0), ("A*", "h1", 1.0), ("A*", "h2", 1.0),
    ("WA*", "h2", 1.5), ("WA*", "h2", 2.0), ("WA*", "h2", 3.0),
]


def rotulo(alg, h, w):
    if alg == "WA*":
        return f"WA* w={w:g} ({h})"
    return f"{alg} ({h})" if h else alg


def regra_maior_carga(p: ProblemaRede):
    """Regra simples: repara primeiro a avaria com maior carga a jusante.
    Para cada avaria: vai buscar a peça (se precisar) ao armazém mais próximo
    que a tenha, desloca-se ao local e repara. Devolve o custo (MW.min)."""
    s, custo = p.estado_inicial(), 0

    def aplicar(a):
        nonlocal s, custo
        assert a in p.accoes(s), (a, s)
        s2 = p.resultado(s, a)
        custo += p.custo(s, a, s2)
        s = s2

    for f in sorted(range(p.k), key=lambda f: -p.carga_subarvore[f]):
        t = p.av_tipo[f]
        if t is not None and s.carga[t] == 0:
            d = min((d for d in range(p.n_arm) if s.stock[3 * d + t] > 0), key=lambda d: p.dist[s.local][d])
            if s.local != d:
                aplicar(("ir", d))
            aplicar(("carregar", t))
        if s.local != p.av_local[f]:
            aplicar(("ir", p.av_local[f]))
        aplicar(("reparar", f))
    assert p.e_objectivo(s)
    return custo


def correr(nivel, indice, config, limites):
    alg, h, w = config
    inst = gerador.gerar_instancia(nivel, indice)
    p = ProblemaRede(inst)                      # problema novo => caches de h limpas (comparação justa)
    r = resolver(p, alg, h or "h2", w, limites)
    return dict(nivel=nivel, instancia=indice, nome=inst["nome"], semente=inst["semente"],
                n_avarias=len(inst["avarias"]), n_nos=inst["n_nos"],
                config=rotulo(alg, h, w), algoritmo=alg, heuristica=h or "", w=w,
                estado=r.estado, motivo=r.motivo, custo=r.custo, comprimento=r.comprimento,
                expandidos=r.expandidos, gerados=r.gerados, max_fronteira=r.max_fronteira,
                reexpandidos=r.reexpandidos, tempo_s=round(r.tempo, 3),
                memoria_mb=round(r.memoria_pico / 1e6, 2))


def graficos(df, pasta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    configs = list(dict.fromkeys(df["config"]))
    cmap = plt.get_cmap("tab20")
    cor = {c: cmap(i) for i, c in enumerate(configs)}

    for coluna, nome, ylabel, escala in (("expandidos", "grafico_nos_expandidos.png", "nós expandidos", "log"),
                                         ("tempo_s", "grafico_tempo.png", "tempo (s)", "log")):
        fig, ax = plt.subplots(figsize=(9, 6))
        for c in configs:
            d = df[df.config == c]
            ok, mau = d[d.estado == "ok"], d[d.estado == "falhou"]
            m = ok.groupby("n_avarias")[coluna].mean()
            ax.plot(m.index, m.values, "-o", color=cor[c], label=c, ms=4)
            ax.scatter(mau["n_avarias"], mau[coluna].clip(lower=1e-3), marker="x", color=cor[c], s=45)
        ax.set_yscale(escala)
        ax.set_xlabel("tamanho da instância (nº de avarias)")
        ax.set_ylabel(ylabel + " (log)")
        ax.set_title(f"{ylabel} vs tamanho  (linha = média das execuções ok; x = falhou)")
        ax.grid(alpha=.3)
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        fig.savefig(os.path.join(pasta, nome), dpi=140)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 6))
    ok = df[(df.estado == "ok")]
    for c in configs:
        d = ok[ok.config == c]
        ax.scatter(d["custo_optimo"], d["custo"], color=cor[c], label=c, s=22, alpha=.8)
    lim = [0, ok["custo"].max() * 1.05]
    ax.plot(lim, lim, "k--", lw=1, label="custo = óptimo")
    ax.set_xlabel("custo óptimo (MW·min)")
    ax.set_ylabel("custo obtido (MW·min)")
    ax.set_title("Custo obtido vs custo óptimo")
    ax.grid(alpha=.3)
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(pasta, "grafico_custo_vs_optimo.png"), dpi=140)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite-tempo", type=float, default=60.0)
    ap.add_argument("--limite-mem-gb", type=float, default=2.0)
    ap.add_argument("--n", type=int, default=gerador.N_INSTANCIAS)
    ap.add_argument("--niveis", nargs="*", default=list(gerador.NIVEIS))
    ap.add_argument("--saida", default="resultados")
    ap.add_argument("--de-csv", help="não corre nada: reconstrói resumos/gráficos a partir de um CSV de linhas")
    args = ap.parse_args()
    os.makedirs(args.saida, exist_ok=True)
    limites = Limites(tempo=args.limite_tempo, memoria=int(args.limite_mem_gb * 1024 ** 3))

    linhas = []
    csv_parcial = os.path.join(args.saida, "resultados_parcial.csv")
    pre = pd.read_csv(args.de_csv).to_dict("records") if args.de_csv else None
    for nivel in ([] if pre else args.niveis):
        for i in range(args.n):
            for cfg in CONFIGS:
                linha = correr(nivel, i, cfg, limites)
                linhas.append(linha)
                print(f"{linha['nome']:>12} {linha['n_avarias']:>2}f {linha['config']:<16} {linha['estado']:<7} "
                      f"{linha['motivo']:<10} custo={linha['custo']} exp={linha['expandidos']} "
                      f"t={linha['tempo_s']}s mem={linha['memoria_mb']}MB", flush=True)
                pd.DataFrame(linhas).to_csv(csv_parcial, index=False)
    df = pd.DataFrame(pre if pre else linhas)

    # custo óptimo por instância = menor custo dos algoritmos que garantem optimalidade
    opt = (df[(df.estado == "ok") & df.config.isin(["UCS", "A* (h0)", "A* (h1)", "A* (h2)"])]
           .groupby("nome")["custo"].min())
    df["custo_optimo"] = df["nome"].map(opt)
    df["razao_custo"] = df["custo"] / df["custo_optimo"]
    # factor de ramificação efectivo (A*): N = nós gerados, d = nº de acções da solução
    df["b_estrela"] = [heuristicas.ramificacao_efectiva(int(g), int(d)) if (alg == "A*" and e == "ok") else None
                       for g, d, alg, e in zip(df.gerados, df.comprimento.fillna(0), df.algoritmo, df.estado)]
    df.to_csv(os.path.join(args.saida, "resultados.csv"), index=False)
    if os.path.exists(csv_parcial) and not pre:
        os.remove(csv_parcial)

    resumo = (df.groupby(["nivel", "config"], sort=False)
              .apply(lambda d: pd.Series(dict(
                  ok=(d.estado == "ok").sum(), falhou=(d.estado == "falhou").sum(),
                  expandidos=d.loc[d.estado == "ok", "expandidos"].mean(),
                  tempo_s=d.loc[d.estado == "ok", "tempo_s"].mean(),
                  memoria_mb=d.loc[d.estado == "ok", "memoria_mb"].mean(),
                  custo_medio=d.loc[d.estado == "ok", "custo"].mean(),
                  razao_custo=d.loc[d.estado == "ok", "razao_custo"].mean(),
                  b_estrela=d.loc[d.estado == "ok", "b_estrela"].mean())), include_groups=False)
              .round(3))
    resumo.to_csv(os.path.join(args.saida, "resumo_por_nivel.csv"))
    print("\n", resumo.to_string())

    # ordem óptima vs regra simples "maior carga"
    reg = []
    for nivel in args.niveis:
        for i in range(args.n):
            nome = f"{nivel}_{i:02d}"
            p = ProblemaRede(gerador.gerar_instancia(nivel, i))
            c_regra = regra_maior_carga(p)
            c_opt = opt.get(nome)
            reg.append(dict(nome=nome, n_avarias=p.k, custo_regra=c_regra, custo_optimo=c_opt,
                            razao=c_regra / c_opt if c_opt else None))
    reg = pd.DataFrame(reg)
    reg.to_csv(os.path.join(args.saida, "regra_maior_carga.csv"), index=False)
    print("\n", reg.round(3).to_string())

    graficos(df, args.saida)
    print("\nFicheiros escritos em", args.saida)


if __name__ == "__main__":
    main()
