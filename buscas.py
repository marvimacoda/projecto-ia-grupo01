

























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





