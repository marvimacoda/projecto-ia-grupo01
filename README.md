
========================================================================================
RESOLUÇÃO DE PROBLEMAS DE BUSCA EM PYTHON — P8: REPARAÇÃO DA REDE ELÉCTRICA APÓS CICLONE
========================================================================================

Grupo 1 · Pós-Laboral — Macoda, Marvin · Buce, Ilan Da Costa
Problema: P8, equipa de reparação da rede eléctrica após um ciclone (Beira)
Algoritmo avançado: A* Ponderado (w = 1,5; 2; 3)
Semente das instâncias: 2026 × 100 + 50 + 1 = 202651

Este repositório modela o problema P8 como problema de busca e compara sete algoritmos
(BFS, DFS, IDS, Custo Uniforme, Gulosa, A* e A* Ponderado) com duas heurísticas (h1 e
h2). Este ficheiro explica como executar tudo: o menu, os testes, as instâncias e as
experiências. A formulação, as provas e a análise dos resultados estão no relatório.


________________________________________________________________________________________



1. O QUE ESTÁ NO REPOSITÓRIO
----------------------------

  - problema.py: classe abstracta Problema e classe No
  - dominio.py: o problema P8 (ProblemaRede) e o estado imutável (EstadoRede)
  - buscas.py: os 7 algoritmos de busca e a função resolver (limites de tempo e memória)
  - heuristicas.py: heurísticas h0, h1, h2, cálculo exacto de h* e factor de ramificação
    efectivo b*
  - gerador.py: gera as instâncias aleatórias a partir da semente
  - main.py: menu interactivo e linha de comandos
  - experiencias.py: corre a bateria de experiências e gera CSV e gráficos
  - tabelas_relatorio.py: escreve as tabelas do relatório a partir dos CSV
  - instancias/: 15 ficheiros JSON (5 pequenas, 5 médias, 5 grandes)
  - tests/ e pytest.ini: testes automáticos (pytest)
  - resultados/: CSV e gráficos das experiências


________________________________________________________________________________________



2. REQUISITOS E INSTALAÇÃO
--------------------------

É preciso Python 3.10 ou superior (o código usa int.bit_count e dataclass(slots=True);
com o 3.9 dá erro).

Confirma a versão:


    python --version

No Windows, se python mostrar uma versão antiga, usa o lançador py -3.12 em todos os
comandos deste ficheiro (por exemplo py -3.12 main.py). Para instalar o Python 3.12 pelo
terminal: winget install --id Python.Python.3.12 -e (fecha e volta a abrir o terminal
depois).

Instala as bibliotecas (só servem para os testes, as experiências e os gráficos; os
algoritmos usam apenas a biblioteca padrão):


    py -3.12 -m pip install pytest matplotlib pandas

  NOTA: Nota: o main.py importa o experiencias.py, que usa pandas. Por isso o pandas tem
  de estar instalado mesmo que só queiras usar o menu.


Obter o código
~~~~~~~~~~~~~~

  - Com o Git: git clone https://github.com/marvimacoda/projecto-ia-grupo01.git
  - Sem Git: no GitHub, Code → Download ZIP, e descompacta.

Todos os comandos abaixo correm dentro da pasta do projecto (a que tem o main.py). Para
abrir um terminal já nessa pasta no Windows: abre-a no Explorador de Ficheiros, clica na
barra de endereço, escreve cmd e carrega em Enter.


________________________________________________________________________________________



3. EXECUTAR O PROGRAMA (MENU INTERACTIVO)
-----------------------------------------


    py -3.12 main.py

Aparece o menu:


    === P8: reparação da rede eléctrica após ciclone ===
     instância: (nenhuma) | algoritmo: A* h=h2 w=1.0 | limites: 60s, 2GB, prof.=60
     1) escolher instância (ficheiro)   2) gerar instância (nível/índice)
     3) escolher algoritmo / heurística / limites
     4) resolver e mostrar solução passo a passo
     5) mostrar estado inicial          6) comparar com a regra 'maior carga'
     0) sair
    opção:

Escreve o número da opção e carrega em Enter. A segunda linha mostra sempre o estado
actual: que instância está carregada e que algoritmo será usado. No início diz
(nenhuma); por omissão o algoritmo é o A* com a heurística h2.

Para resolver um problema precisas sempre de duas coisas: uma instância (opção 1 ou 2) e
depois resolver (opção 4). A opção 3 só serve para mudar de algoritmo.

Quando o programa pergunta algo com um valor entre parêntesis rectos, por exemplo índice
[0]:, carregar só em Enter aceita esse valor.


Opção 1: escolher uma instância (ficheiro)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Lista os ficheiros de instancias/ com um número cada: grande_00 a grande_04, media_00 a
media_04 e pequena_00 a pequena_04. Escreve o número do ficheiro que queres. A segunda
linha do menu passa a mostrar o nome da instância.


Opção 2: gerar uma instância
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Faz três perguntas:

  1. nível: pequena, media (sem acento) ou grande.
  2. índice: Enter para 0. Os índices 0 a 4 são as 5 instâncias oficiais (iguais aos
     ficheiros de instancias/); outro número cria uma instância nova, diferente das
     oficiais.
  3. semente: Enter para usar a do grupo, 202651.

A instância fica só na memória do programa (não é gravada em ficheiro). Gerar de novo
com os mesmos três valores dá sempre a mesma instância.


Opção 3: escolher o algoritmo, a heurística e os limites
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

O programa pergunta, um de cada vez:

  - algoritmo  ->  Valores: BFS, DFS, IDS, UCS, Gulosa, A*, WA* (escreve exactamente
    assim, com maiúsculas) | Quando aparece: sempre
  - heurística  ->  Valores: h0, h1, h2 | Quando aparece: só para Gulosa, A* e WA*
  - peso w  ->  Valores: por exemplo 1.5, 2, 3 | Quando aparece: só para WA*
  - limite de tempo (s)  ->  Valores: Enter para 60 | Quando aparece: sempre
  - limite de memória (GB)  ->  Valores: Enter para 2 | Quando aparece: sempre
  - profundidade máxima  ->  Valores: Enter para 60 | Quando aparece: sempre (só afecta
    DFS e IDS)


Opção 4: resolver e mostrar a solução
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Resolve a instância carregada com o algoritmo escolhido e escreve, por esta ordem:

  1. Uma linha de resumo, por exemplo >> A*: solução com 10 acções, custo 1653 MW.min.
  2. O plano, acção a acção (ver a secção 4 abaixo).
  3. O estado final: a rede desenhada, toda [OK] se o objectivo foi atingido.
  4. As métricas: custo, comprimento (nº de acções), nós expandidos, nós gerados,
     tamanho máximo da fronteira, reexpandidos (só o IDS), tempo e memória de pico.

Se o algoritmo exceder o tempo ou a memória, escreve FALHOU (tempo) ou FALHOU (memoria)
e os nós expandidos até desistir.


Opção 5: mostrar o estado inicial
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Desenha a rede antes de qualquer reparação. Não muda nada. Ver a secção 5 para a
interpretar.


Opção 6: comparar com a regra "maior carga"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Resolve a instância com o A* h2 (o óptimo) e compara com a regra simples "reparar
primeiro a avaria com maior carga a jusante". Escreve uma linha, por exemplo:


    regra 'maior carga': 1660 | óptimo (A*-h2): 1653 | regra é 0.4% pior


Opção 0: sair
~~~~~~~~~~~~~


Uma sessão de teste (copia e executa)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Escreve estas linhas, uma de cada vez, com Enter:


    2          (gerar instância)
    pequena
    1
    (só Enter)
    5          (ver a rede)
    4          (resolver com A* h2)
    3          (mudar de algoritmo)
    BFS
    (Enter) (Enter) (Enter)
    4          (resolver com BFS: o custo sai maior)
    6          (comparar com a regra)
    0


________________________________________________________________________________________



4. COMO LER A SOLUÇÃO (OPÇÃO 4)
-------------------------------

Cada acção ocupa duas linhas:


      1. t=   2 min | carregar 1 poste em Armazem A (2 min)  | custo   106 | acum.    106
           -> local=Armazem A | carrinha(p,i,t)=(1, 0, 0) | reparadas=- | sem energia=53 MW

  - t=   2 min: tempo acumulado desde o início
  - carregar 1 poste em Armazem A (2 min): a acção e a sua duração
  - custo 106: custo do passo = duração × MW sem energia antes da acção (2 min × 53 MW)
  - acum. 106: soma dos custos até este passo
  - local=...: onde a equipa está depois da acção
  - carrinha(p,i,t)=(1, 0, 0): peças na carrinha: (postes, isoladores, transformadores)
  - reparadas=-: avarias já reparadas (- = nenhuma)
  - sem energia=53 MW: carga que ainda está sem energia

Há três tipos de acção: ir para <local>, carregar 1 <peça> em <armazém> e reparar
<avaria>.


________________________________________________________________________________________



5. COMO INTERPRETAR A ÁRVORE ASCII E DESENHÁ-LA NO PAPEL
--------------------------------------------------------

A opção 5 (e o fim da opção 4) desenha a rede em texto. Exemplo, da instância
pequena_01:


    local=Armazem A | carrinha(p,i,t)=(0, 0, 0) | reparadas=- | sem energia=53 MW
    Subestacao (no 0)
    +-- [OK] no 1 (2 MW)
        |-- [OK] no 2 (7 MW)
        |   +-- [OK] no 7 (6 MW)
        |       +-- [OK] no 8 (2 MW)
        +-- [OK] no 3 (2 MW)
            |-- [OK] no 4 (1 MW)
            |   +-- [OK] no 9 (6 MW)
            |-- [OK] no 5 (5 MW)
            +-- [--] no 6 (6 MW)  XX AVARIA F1 (poste, 12 min, local Local F1)
                |-- [--] no 10 (9 MW)
                +-- [--] no 11 (2 MW)
                    |-- [--] no 12 (2 MW)
                    |   +-- [--] no 13 (9 MW)
                    |       +-- [--] no 16 (2 MW)  XX AVARIA F2 (transformador, 36 min, local Local F2)
                    |           |-- [--] no 17 (1 MW)  XX AVARIA F3 (isolador, 38 min, local Local F3)
                    |           +-- [--] no 19 (4 MW)
                    |-- [--] no 14 (3 MW)
                    |   +-- [--] no 18 (6 MW)
                    +-- [--] no 15 (9 MW)


5.1 O que diz cada linha
~~~~~~~~~~~~~~~~~~~~~~~~

  - no 16: o número do nó
  - (2 MW): a carga do nó
  - [OK]: o nó tem energia
  - [--]: o nó não tem energia
  - XX AVARIA F2 (transformador, 36 min, local Local F2): a linha entre este nó e o nó
    de cima (o pai) está avariada. Entre parêntesis: a peça que o reparo exige (ou sem
    peca), o tempo de reparo e o local onde a equipa tem de ir

A primeira linha (local=...) é o resumo do estado: onde a equipa está, as peças na
carrinha, as avarias já reparadas e os MW sem energia.


5.2 Como descobrir o pai de cada nó (pela indentação)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

O pai não vem escrito: tira-se do recuo à esquerda.

  1. Conta em que coluna começa o símbolo +-- ou |--. Cada nível de recuo são 4 colunas:
     coluna 0 = nível 1, coluna 4 = nível 2, coluna 8 = nível 3, e assim por diante.
  2. O pai é a linha mais próxima acima com um nível a menos. Os nós do nível 1 são
     filhos da subestação (nó 0).

Exemplo: no 16 começa na coluna 24 (nível 7). Subindo, a linha mais próxima de nível 6 é
o no 13. Logo o pai do nó 16 é o nó 13. Os nós 17 e 19 começam ambos na coluna 28 (nível
8) e a linha de nível 7 mais próxima acima é o nó 16: são irmãos, filhos do 16.

|-- quer dizer "ainda há irmãos mais abaixo" e +-- quer dizer "este é o último filho".
Servem para ajudar a ver, não mudam a ligação.


5.3 Tabela de apoio (a preencher linha a linha)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Percorre o texto de cima para baixo e escreve uma linha por nó:

  Nó | Carga (MW) | Coluna → nível | Pai | Estado      | Avaria na linha pai–nó
  ---+------------+----------------+-----+-------------+---------------------------
  1  | 2          | 0 → 1          | 0   | OK          |
  2  | 7          | 4 → 2          | 1   | OK          |
  7  | 6          | 8 → 3          | 2   | OK          |
  8  | 2          | 12 → 4         | 7   | OK          |
  3  | 2          | 4 → 2          | 1   | OK          |
  4  | 1          | 8 → 3          | 3   | OK          |
  9  | 6          | 12 → 4         | 4   | OK          |
  5  | 5          | 8 → 3          | 3   | OK          |
  6  | 6          | 8 → 3          | 3   | sem energia | F1 (poste, 12 min)
  10 | 9          | 12 → 4         | 6   | sem energia |
  11 | 2          | 12 → 4         | 6   | sem energia |
  12 | 2          | 16 → 5         | 11  | sem energia |
  13 | 9          | 20 → 6         | 12  | sem energia |
  16 | 2          | 24 → 7         | 13  | sem energia | F2 (transformador, 36 min)
  17 | 1          | 28 → 8         | 16  | sem energia | F3 (isolador, 38 min)
  19 | 4          | 28 → 8         | 16  | sem energia |
  14 | 3          | 16 → 5         | 11  | sem energia |
  18 | 6          | 20 → 6         | 14  | sem energia |
  15 | 9          | 16 → 5         | 11  | sem energia |


5.4 Desenhar no papel
~~~~~~~~~~~~~~~~~~~~~

  1. Escreve n0 (subestação) no topo.
  2. Desenha por baixo os nós cujo pai é 0 (aqui só o n1) e liga-os.
  3. Nível a nível, desenha os filhos de cada nó, usando a coluna "Pai" da tabela: os
     filhos do 1 são o 2 e o 3; os do 2 são só o 7; os do 3 são o 4, o 5 e o 6; e assim
     por diante.
  4. Escreve a carga ao lado de cada nó.
  5. Onde a tabela tem uma avaria (F1, F2, F3), pinta a linha entre o nó e o pai (a de
     cima do nó) e escreve o nome da avaria. Não é uma avaria "dentro" do nó: é a
     ligação ao pai que está cortada.
  6. Pinta os nós sem energia: o nó que tem a avaria e todos os que estão por baixo
     dele.

Nesta instância, a F1 (linha 3–6) deixa sem energia toda a subárvore do nó 6 (53 MW). As
avarias F2 (linha 13–16) e F3 (linha 16–17) estão em cadeia por baixo dela.

  NOTA: Os armazéns e as ruas não aparecem no desenho: estão no ficheiro JSON da
  instância (secção 7).


________________________________________________________________________________________



6. LINHA DE COMANDOS (SEM MENU)
-------------------------------

Para resolver de uma só vez, sem perguntas:


    py -3.12 main.py --instancia instancias/pequena_01.json --algoritmo "A*" --h h2 --passos
    py -3.12 main.py --nivel media --indice 1 --algoritmo WA* --w 2 --passos
    py -3.12 main.py --nivel pequena --indice 0 --algoritmo BFS

  - --instancia <ficheiro>: usa um ficheiro JSON de instancias/
  - --nivel <nivel> e --indice <n>: gera a instância (em alternativa a --instancia)
  - --algoritmo: BFS, DFS, IDS, UCS, Gulosa, A* ou WA* (põe "A*" entre aspas)
  - --h: h0, h1 ou h2 (por omissão h2)
  - --w: peso do A* Ponderado
  - --limite-tempo: segundos (por omissão 60)
  - --passos: mostra a rede e a solução passo a passo

Se não indicares --algoritmo, abre o menu.


________________________________________________________________________________________



7. INSTÂNCIAS
-------------


    py -3.12 gerador.py

Escreve os 15 ficheiros em instancias/ (3 níveis × 5) com a semente 202651. Correr de
novo dá ficheiros idênticos. Opções: --n (instâncias por nível), --semente e --saida
(pasta).

  Nível   | Nós | Avarias (configurado) | O que se espera
  --------+-----+-----------------------+--------------------------------------
  pequena | 20  | 2–3                   | todos os algoritmos terminam
  media   | 22  | 6–8                   | IDS falha; BFS e DFS começam a sofrer
  grande  | 26  | 12–13                 | só as buscas informadas terminam

Cada ficheiro JSON tem estes campos:

  - nome, nivel, indice, semente: identificação
  - n_nos, pai, carga_mw: a árvore: pai[n] é o pai do nó n; carga_mw[n] a carga (MW)
  - avarias: lista com id, no (a linha pai–nó avariada), local, reparo_min e peca
    (poste, isolador, transformador ou nulo)
  - locais, ruas: os locais (0 e 1 são os armazéns A e B) e as ruas [local1, local2,
    minutos]
  - armazens: stock de peças em cada armazém
  - capacidade, t_carga, inicio: peças que a carrinha leva (3), minutos a carregar uma
    peça (2) e local inicial (0 = armazém A)


________________________________________________________________________________________



8. TESTES AUTOMÁTICOS
---------------------


    py -3.12 -m pytest -q

Deve acabar com 12 passed in ...s (10 funções de teste; as de admissibilidade e
consistência correm duas vezes, uma com h1 e outra com h2). Para ver cada teste, usa o
modo detalhado:


    py -3.12 -m pytest -v

  - 1  ->  Teste: estado inicial e objectivo | O que verifica: estado inicial esperado,
    teste de objectivo, estado imutável e hashable
  - 2  ->  Teste: sucessores de estado conhecido | O que verifica: acções aplicáveis
    numa rede de 6 nós feita à mão
  - 3  ->  Teste: resultado e custo | O que verifica: efeito de carregar e reparar; o
    custo depende do que já foi reparado
  - 4  ->  Teste: instância sem solução | O que verifica: BFS, UCS e A* devolvem
    sem_solucao quando falta uma peça
  - 5  ->  Teste: BFS, DFS e IDS | O que verifica: devolvem planos válidos; o IDS
    re-expande nós
  - 6  ->  Teste: A* e UCS | O que verifica: mesmo custo (h0, h1, h2); a BFS nunca é
    melhor do que o óptimo
  - 7  ->  Teste: admissibilidade (h1, h2) | O que verifica: h(s) ≤ h*(s) em todos os
    estados
  - 8  ->  Teste: consistência e dominância (h1, h2) | O que verifica: h(s) ≤ c + h(s′)
    e h0 ≤ h1 ≤ h2
  - 9  ->  Teste: A* Ponderado e Gulosa | O que verifica: custo do WA* entre o óptimo e
    w vezes o óptimo
  - 10  ->  Teste: gerador e b* | O que verifica: instâncias reproduzíveis (semente
    202651) e factor de ramificação efectivo


________________________________________________________________________________________



9. EXPERIÊNCIAS
---------------


    py -3.12 experiencias.py

Corre a bateria completa: 3 níveis × 5 instâncias × 12 configurações (BFS, DFS, IDS,
UCS, Gulosa h1 e h2, A* h0, h1 e h2, A* Ponderado com h2 e w = 1,5, 2 e 3), cada uma com
o limite de 60 s e 2 GB. Demora cerca de 1 hora, porque as execuções que falham gastam
os 60 s completos. Deixa o computador ligado à corrente e sem outros programas pesados,
para o tempo medido ser fiável. Para interromper: Ctrl + C (o que já correu fica em
resultados/resultados_parcial.csv).

Para uma corrida rápida, só para experimentar (3 a 4 minutos):


    py -3.12 experiencias.py --limite-tempo 10 --niveis pequena media --saida resultados_teste

Opções: --limite-tempo, --limite-mem-gb, --n (instâncias por nível), --niveis, --saida
(pasta) e --de-csv <ficheiro> (reconstrói os resumos e gráficos a partir de um CSV, sem
voltar a correr).

No ecrã aparece uma linha por execução, por exemplo:


      pequena_01  3f A* (h2)          ok                 custo=1653 exp=24 t=0.003s mem=0.02MB

(instância, nº de avarias, configuração, estado, custo, nós expandidos, tempo e
memória). Uma execução que excede o limite aparece como falhou com o motivo (tempo ou
memoria) e fica registada.


Ficheiros que saem em resultados/
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

  - resultados.csv: uma linha por execução, com as falhas registadas
  - resumo_por_nivel.csv: médias por nível e algoritmo
  - regra_maior_carga.csv: a regra simples contra o óptimo, por instância
  - grafico_nos_expandidos.png: nós expandidos vs tamanho da instância
  - grafico_tempo.png: tempo vs tamanho da instância
  - grafico_custo_vs_optimo.png: custo obtido vs custo óptimo


Tabelas para o relatório
~~~~~~~~~~~~~~~~~~~~~~~~


    py -3.12 tabelas_relatorio.py

Lê resultados/resultados.csv e escreve (no ecrã e em resultados/tabelas_relatorio.txt)
as tabelas de resultados por nível, a comparação das heurísticas, o A* Ponderado contra
a regra simples e os números citados no texto. As colunas vêm separadas por TAB.


________________________________________________________________________________________



10. PROBLEMAS FREQUENTES
------------------------

  - python --version mostra 3.9 ou inferior: instala o Python 3.12 e usa py -3.12
    (secção 2)
  - No module named 'pandas' (ou pytest, matplotlib): py -3.12 -m pip install pytest
    matplotlib pandas
  - can't open file ... main.py: o terminal não está na pasta do projecto; entra na
    pasta que tem o main.py
  - a lista da opção 1 aparece vazia: estás fora da pasta do projecto (a pasta
    instancias não é encontrada)
  - opção inválida: escreveste algo fora da lista; escreve só o número da opção, ou o
    nome do algoritmo exactamente como aparece
  - o programa fechou com ValueError: escreveste letras onde o programa esperava um
    número (por exemplo no índice); volta a arrancar
  - IDS, BFS ou UCS demoram muito nas instâncias médias e grandes: é esperado: vão
    falhar por tempo. Baixa o limite na opção 3 (por exemplo 10 s)
  - pytest diz 0 tests ou não encontra módulos: corre-o a partir da pasta principal: py
    -3.12 -m pytest -q


________________________________________________________________________________________



11. AUTORES
-----------

Grupo 1 (Pós-Laboral): Macoda, Marvin · Buce, Ilan Da Costa

  - Macoda: README.md, problema.py, dominio.py, heuristicas.py, main.py, e os
    algoritmos UCS, Gulosa e A* (incluindo o A* Ponderado), resultados/.
  - Buce: gerador.py, instancias/, tests/, pytest.ini, experiencias.py,
    e os algoritmos BFS, DFS e IDS.
