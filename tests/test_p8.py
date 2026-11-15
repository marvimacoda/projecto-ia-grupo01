"""10 testes pytest (Pós-Laboral). Correr:  pytest -q"""
import pytest

import gerador
import heuristicas
from buscas import Limites, resolver
from dominio import EstadoRede, ProblemaRede


# ---------------------------------------------------------------- fixtures
def inst_conhecida():
    """Rede de 6 nós feita à mão (valores fáceis de verificar).

        0 - 1 - 3          avaria F1: linha 0-1 (nó 1), poste, 10 min
        |   \\- 4          avaria F2: linha 1-3 (nó 3), sem peça, 5 min  (aninhada em F1)
        \\- 2 - 5
    cargas (MW): n1=3 n2=2 n3=4 n4=1 n5=5
    """
    return dict(
        nome="conhecida", n_nos=6, pai=[-1, 0, 0, 1, 1, 2], carga_mw=[0, 3, 2, 4, 1, 5],
        locais=["Armazem A", "Armazem B", "Local F1", "Local F2"],
        ruas=[[0, 1, 4], [0, 2, 6], [1, 3, 5], [2, 3, 3]],
        avarias=[dict(id="F1", no=1, local=2, reparo_min=10, peca="poste"),
                 dict(id="F2", no=3, local=3, reparo_min=5, peca=None)],
        armazens=[dict(poste=1, isolador=0, transformador=0), dict(poste=0, isolador=1, transformador=0)],
        capacidade=3, t_carga=2, inicio=0)


@pytest.fixture
def p():
    return ProblemaRede(inst_conhecida())


def todas_pequenas(n=3):
    return [ProblemaRede(gerador.gerar_instancia("pequena", i)) for i in range(n)]


def validar_plano(p, sol):
    """Repete o plano acção a acção: legalidade, objectivo final e custo somado."""
    s, total = sol[0][1], 0
    assert s == p.estado_inicial()
    for a, s2 in sol[1:]:
        assert a in p.accoes(s)
        assert p.resultado(s, a) == s2
        total += p.custo(s, a, s2)
        s = s2
    assert p.e_objectivo(s)
    return total


# ------------------------------------------------------------------ testes
def test_1_estado_inicial_e_objectivo(p):
    s0 = p.estado_inicial()
    assert s0 == EstadoRede(0, 0, (0, 0, 0), (1, 0, 0, 0, 1, 0))
    assert not p.e_objectivo(s0)
    assert p.e_objectivo(EstadoRede(0, 0b11, (0, 0, 0), s0.stock))
    assert hash(s0) == hash(p.estado_inicial())            # imutável e hashable


def test_2_sucessores_de_estado_conhecido(p):
    # Em A (armazém 0), sem peças: pode ir a qualquer outro local e carregar o poste
    # (o isolador do armazém B não é necessário -> poda); não há avaria em A.
    acc = p.accoes(p.estado_inicial())
    assert set(acc) == {("ir", 1), ("ir", 2), ("ir", 3), ("carregar", 0)}
    # Em F1 sem poste não se pode reparar; com poste pode
    s = EstadoRede(2, 0, (0, 0, 0), p.stock_inicial)
    assert ("reparar", 0) not in p.accoes(s)
    s = EstadoRede(2, 0, (1, 0, 0), p.stock_inicial)
    assert ("reparar", 0) in p.accoes(s)


def test_3_resultado_e_custo_depende_do_reparado(p):
    s0 = p.estado_inicial()
    # sem nada reparado: nós 1,3,4 sem energia = 3+4+1 = 8 MW; ir A->F1 = 6 min
    s1 = p.resultado(s0, ("ir", 2))
    assert p.custo(s0, ("ir", 2), s1) == 6 * 8
    # carregar poste: stock do armazém A desce, carrinha sobe
    sc = p.resultado(s0, ("carregar", 0))
    assert sc.carga == (1, 0, 0) and sc.stock[0] == 0
    # reparar F1 consome o poste e restaura 3+1 MW; só n3 (4 MW) fica sem energia
    sr = p.resultado(EstadoRede(2, 0, (1, 0, 0), s0.stock), ("reparar", 0))
    assert sr.reparadas == 0b01 and sr.carga == (0, 0, 0)
    assert p.carga_desligada(0b01) == 4
    # o MESMO tipo de passo custa menos depois de reparar: g continua aditivo
    assert p.custo(sr, ("ir", 3), p.resultado(sr, ("ir", 3))) == 3 * 4   # dist F1->F2 = 3


def test_4_instancia_sem_solucao():
    inst = inst_conhecida()
    inst["avarias"][1]["peca"] = "transformador"        # ninguém tem transformadores
    for alg, h in (("BFS", "h2"), ("UCS", "h2"), ("A*", "h2")):
        r = resolver(ProblemaRede(inst), alg, h, limites=Limites(tempo=20))
        assert r.estado == "sem_solucao" and r.solucao is None


def test_5_bfs_dfs_ids_devolvem_planos_validos():
    for pr in todas_pequenas(2):
        for alg in ("BFS", "DFS", "IDS"):
            r = resolver(ProblemaRede(pr.inst), alg, limites=Limites(tempo=30))
            assert r.estado == "ok", (alg, r.motivo)
            assert validar_plano(ProblemaRede(pr.inst), r.solucao) == r.custo
    r = resolver(ProblemaRede(inst_conhecida()), "IDS")
    assert r.estado == "ok" and r.reexpandidos > 0          # IDS re-expande nós


def test_6_astar_e_ucs_devolvem_o_mesmo_custo():
    for pr in todas_pequenas(3):
        c_ucs = resolver(ProblemaRede(pr.inst), "UCS").custo
        for h in ("h0", "h1", "h2"):
            r = resolver(ProblemaRede(pr.inst), "A*", h)
            assert r.estado == "ok" and r.custo == c_ucs
            assert validar_plano(ProblemaRede(pr.inst), r.solucao) == c_ucs
        # BFS minimiza nº de acções, não custo: nunca é melhor que o óptimo
        assert resolver(ProblemaRede(pr.inst), "BFS").custo >= c_ucs


@pytest.mark.parametrize("nome", ["h1", "h2"])
def test_7_admissibilidade(nome):
    for inst in [inst_conhecida()] + [gerador.gerar_instancia("pequena", i) for i in range(3)]:
        pr = ProblemaRede(inst)
        estados, arestas = heuristicas.grafo_completo(pr)
        hstar = heuristicas.h_estrela_todos(pr, estados, arestas)
        for s in estados:
            if s in hstar:                                   # estados sem saída: h* = inf
                assert pr.heuristica(s, nome) <= hstar[s]
        assert all(pr.heuristica(s, nome) == 0 for s in estados if pr.e_objectivo(s))


@pytest.mark.parametrize("nome", ["h1", "h2"])
def test_8_consistencia_e_dominancia(nome):
    for inst in [inst_conhecida()] + [gerador.gerar_instancia("pequena", i) for i in range(3)]:
        pr = ProblemaRede(inst)
        estados, arestas = heuristicas.grafo_completo(pr)
        for s, c, s2 in arestas:
            assert pr.heuristica(s, nome) <= c + pr.heuristica(s2, nome)
        for s in estados:                                     # h0 <= h1 <= h2
            assert pr.heuristica(s, "h0") <= pr.heuristica(s, "h1") <= pr.heuristica(s, "h2")


def test_9_astar_ponderado_e_gulosa():
    for pr in todas_pequenas(3) + [ProblemaRede(gerador.gerar_instancia("media", 0))]:
        otimo = resolver(ProblemaRede(pr.inst), "A*", "h2").custo
        for w in (1.5, 2.0, 3.0):
            r = resolver(ProblemaRede(pr.inst), "WA*", "h2", w)
            assert r.estado == "ok" and otimo <= r.custo <= w * otimo
            validar_plano(ProblemaRede(pr.inst), r.solucao)
        for h in ("h1", "h2"):
            r = resolver(ProblemaRede(pr.inst), "Gulosa", h)
            assert r.estado == "ok" and r.custo >= otimo


def test_10_gerador_reprodutivel_e_ramificacao_efectiva():
    a = gerador.gerar_instancia("media", 2, gerador.SEMENTE_BASE)
    b = gerador.gerar_instancia("media", 2, gerador.SEMENTE_BASE)
    assert a == b and gerador.SEMENTE_BASE == 202651
    assert a != gerador.gerar_instancia("media", 3, gerador.SEMENTE_BASE)
    assert all(inst["n_nos"] >= 20 for inst in gerador.gerar_todas(1))
    # b*: N+1 = 1 + b + b^2 + ... + b^d
    b_ = heuristicas.ramificacao_efectiva(N=30, d=4)
    assert sum(b_ ** i for i in range(5)) == pytest.approx(31, rel=1e-6)
    assert heuristicas.ramificacao_efectiva(N=4, d=4) == pytest.approx(1.0, abs=1e-6)
