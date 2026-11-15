"""Escreve as tabelas do relatório a partir dos CSV de experiencias.py.

Uso (na pasta do projecto, depois de correr experiencias.py):
    py -3.12 tabelas_relatorio.py                 (lê a pasta resultados/)
    py -3.12 tabelas_relatorio.py resultados_teste


"""
import os
import sys

import pandas as pd

pasta = sys.argv[1] if len(sys.argv) > 1 else "resultados"
df = pd.read_csv(os.path.join(pasta, "resultados.csv"))
reg = pd.read_csv(os.path.join(pasta, "regra_maior_carga.csv"))
saida = []


def p(linha=""):
    print(linha)
    saida.append(linha)


def n0(x):                       # inteiro com espaço nos milhares
    return f"{x:,.0f}".replace(",", " ")


def nd(x, d):                    # decimal com vírgula
    return f"{x:.{d}f}".replace(".", ",")


def tempo(x):
    return nd(x, 3 if x < 1 else 2)


ORDEM = [("BFS", "BFS", "—"), ("DFS", "DFS", "—"), ("IDS", "IDS", "—"), ("UCS", "UCS", "—"),
         ("Gulosa (h1)", "Gulosa", "h1"), ("Gulosa (h2)", "Gulosa", "h2"),
         ("A* (h0)", "A*", "h0"), ("A* (h1)", "A*", "h1"), ("A* (h2)", "A*", "h2"),
         ("WA* w=1.5 (h2)", "A* Pond. w=1,5", "h2"), ("WA* w=2 (h2)", "A* Pond. w=2", "h2"),
         ("WA* w=3 (h2)", "A* Pond. w=3", "h2")]

PL = {"pequena": "pequenas", "media": "médias", "grande": "grandes"}
NIVEIS = [("pequena", 7), ("media", 8), ("grande", 9)]

for nivel, num in NIVEIS:
    p(f"\n=== Tabela {num}: resultados médios, instâncias {PL[nivel]} ===")
    p("\t".join(["Algoritmo", "Heur.", "Resolvidas", "Custo médio", "Custo / óptimo", "Nós expandidos",
                 "Nós gerados", "Fronteira máx.", "Tempo (s)", "Memória (MB)"]))
    for cfg, alg, h in ORDEM:
        d = df[(df.nivel == nivel) & (df.config == cfg)]
        ok = d[d.estado == "ok"]
        k, n = len(ok), len(d)
        if k == 0:
            mot = d.motivo.mode().iloc[0]
            p("\t".join([alg, h, f"0/{n}", f"falhou ({'memória' if mot == 'memoria' else mot})"]))
        else:
            res = f"{k}/{n}" + ("*" if k < n else "")
            p("\t".join([alg, h, res, n0(ok.custo.mean()), nd(ok.razao_custo.mean(), 2),
                         n0(ok.expandidos.mean()), n0(ok.gerados.mean()), n0(ok.max_fronteira.mean()),
                         tempo(ok.tempo_s.mean()), nd(ok.memoria_mb.mean(), 2)]))
            if k < n:
                p(f"   * {cfg}: resolveu {k} das {n}; as outras {n - k} falharam ({', '.join(sorted(set(d[d.estado != 'ok'].motivo)))})")

p("\n=== Tabela 4: comparação das heurísticas no A* ===")
p("\t".join(["Instância", "k", "d", "Expandidos h0", "Expandidos h1", "Expandidos h2", "b* h1", "b* h2"]))
for nome in sorted(set(df.nome), key=lambda s: (["pequena", "media", "grande"].index(s.split("_")[0]), s)):
    def g(c):
        return df[(df.nome == nome) & (df.config == c)].iloc[0]
    a2 = g("A* (h2)")
    linha = [nome, str(int(a2.n_avarias)), str(int(a2.comprimento)) if a2.estado == "ok" else "—"]
    for h in ("h0", "h1", "h2"):
        r = g(f"A* ({h})")
        linha.append(n0(r.expandidos) if r.estado == "ok" else "falhou (tempo)")
    for h in ("h1", "h2"):
        r = g(f"A* ({h})")
        linha.append(nd(r.b_estrela, 2) if r.estado == "ok" else "—")
    p("\t".join(linha))

# ---- A* Ponderado e regra simples
p("\n=== Tabelas 10 e 11: A* Ponderado e regra 'maior carga' ===")
p("\t".join(["Nível", "Tempo A* h2", "Tempo WA* w=3", "Exp. A* h2", "Exp. WA* w=3",
             "Custo WA* w=3 / óptimo (média; máx.)", "Regra / óptimo (média)",
             "w=1,5 média (máx.)", "w=2 média (máx.)", "w=3 média (máx.)"]))
for nivel, _ in NIVEIS:
    base = df[(df.nivel == nivel) & (df.config == "A* (h2)")].set_index("nome")
    base = base[base.estado == "ok"]
    cel = {}
    for w in ("1.5", "2", "3"):
        d = df[(df.nivel == nivel) & (df.config == f"WA* w={w} (h2)")].set_index("nome")
        d = d[d.estado == "ok"]
        comuns = base.index.intersection(d.index)
        r = d.loc[comuns, "custo"] / base.loc[comuns, "custo"]
        cel[w] = (nd(r.mean(), 2), nd(r.max(), 2))
    w3 = df[(df.nivel == nivel) & (df.config == "WA* w=3 (h2)") & (df.estado == "ok")]
    rg = reg[reg.nome.str.startswith(nivel)]
    p("\t".join([nivel, tempo(base.tempo_s.mean()), tempo(w3.tempo_s.mean()), n0(base.expandidos.mean()),
                 n0(w3.expandidos.mean()), f"{cel['3'][0]} (máx. {cel['3'][1]})", nd(rg.razao.mean(), 2),
                 f"{cel['1.5'][0]} ({cel['1.5'][1]})", f"{cel['2'][0]} ({cel['2'][1]})", f"{cel['3'][0]} ({cel['3'][1]})"]))

# ---- números que o texto cita
p("\n=== Números citados no texto (confirmem e actualizem no relatório) ===")
ok = df[df.estado == "ok"]
p(f"Execuções: {len(df)} ({(df.estado == 'ok').sum()} ok, {(df.estado == 'falhou').sum()} falhadas)")
p(f"Memória de pico: máximo de uma execução = {nd(ok.memoria_mb.max(), 1)} MB; "
  f"maior média por configuração = {nd(ok.groupby(['nivel', 'config']).memoria_mb.mean().max(), 1)} MB")
p(f"Regra 'maior carga' / óptimo: média global {nd(reg.razao.mean(), 2)}, máximo {nd(reg.razao.max(), 2)}")
for nivel, _ in NIVEIS:
    for cfg in ("BFS", "IDS", "A* (h0)", "A* (h1)", "A* (h2)", "DFS"):
        d = df[(df.nivel == nivel) & (df.config == cfg)]
        p(f"  {nivel:8s} {cfg:8s}: resolvidas {int((d.estado == 'ok').sum())}/{len(d)}")
bs = ok[ok.algoritmo == "A*"].dropna(subset=["b_estrela"])
for h in ("h1", "h2"):
    x = bs[bs.heuristica == h].b_estrela
    if len(x):
        p(f"b* de {h}: entre {nd(x.min(), 2)} e {nd(x.max(), 2)}")

with open(os.path.join(pasta, "tabelas_relatorio.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(saida))
print(f"\nEscrito em {os.path.join(pasta, 'tabelas_relatorio.txt')}")
