# AGRO & TECH — INSTRUÇÕES PERMANENTES DO PROJETO

## 1. IDENTIDADE DO PROJETO

Nome: Agro & Tech

Slogan: Cultive sua história. Construa seu legado.

Tipo: Simulação de Fazenda na Ilha / Farming Tycoon / Idle Management / Economia Multiplayer.

Plataforma: Navegador Web (Desktop e Mobile).

Estilo visual e jogabilidade: Pixel Art com visão aérea (God-view) de uma ilha cercada por oceano.

Modelo de interação: 100% via mouse (Point & Click) e toque. O jogo não possui avatar/personagem físico que o jogador precise controlar para andar até as tarefas. O jogador contempla sua ilha de cima e realiza todas as etapas (plantar, colher, gerenciar estruturas) clicando diretamente nos elementos do cenário.

Navegação: Câmera livre com Pan (arrastar com o mouse/toque) e Zoom in/out dinâmico pela roda do mouse (scroll wheel) ou botões na tela, com foco no cursor.

Multiplayer: Focado em economia, comércio marítimo entre ilhas e interação entre jogadores.

O Agro & Tech é um jogo de navegador no qual cada jogador administra sua própria fazenda em uma ilha paradisíaca, desenvolve lavouras, cria animais, processa matérias-primas, comercializa safras e participa de uma economia viva.

O jogo continua produzindo e evoluindo mesmo quando o jogador estiver offline.

## 2. REFERÊNCIAS DE EXPERIÊNCIA

Utilize como inspiração:
- Islanders e Townscaper: visual limpo de ilha, visão aérea relaxante, câmera livre e foco na construção/gestão.
- Rusty's Retirement / Hay Day: agricultura focada no clique direto, sem atrito de movimentação de avatar para trabalhar.
- Melvor Idle e Sal & Pólvora: progressão incremental, atividades automáticas e produção offline determinística.
- Simulações rurais clássicas: ciclos de semente, safra, reinvestimento e expansão.

Não copie sprites, mapas, códigos, nomes ou identidade visual de outros jogos.

Crie uma identidade própria para o Agro & Tech.

## 3. TECNOLOGIAS OBRIGATÓRIAS

Frontend:
- Phaser 3.
- TypeScript.
- HTML5.
- CSS3.

Backend:
- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy.

Banco:
- PostgreSQL.

Infraestrutura:
- Docker.
- Docker Compose.
- Redis quando necessário.

Comunicação:
- API REST.
- WebSocket quando necessário.

Testes:
- Pytest.
- Playwright.

Controle de versão:
- Git.

## 4. ARQUITETURA

Utilize uma arquitetura modular, organizada e escalável.

Backend separado em:
- Routes: endpoints.
- Services: regras de negócio.
- Repositories: acesso aos dados.
- Models: entidades do banco.
- Schemas: validações.
- Core: configurações e segurança.
- Workers: processamento de tarefas.

Frontend separado em:
- Game: motor, cenas e câmera livre pan/zoom.
- World: geração da ilha, texturas procedurais e posicionamento de elementos.
- Services: comunicação com a API REST.
- State: sessão (JWT) e estado reativo da fazenda.
- UI: modais DOM (plantio, casa, mercado) e HUD moderno.

Não concentre funcionalidades em arquivos gigantes.

Não misture regras de negócio com apresentação visual.

Não adote microserviços prematuramente. Comece com um monólito modular.

## 5. IDENTIDADE VISUAL E NAVEGAÇÃO

O jogo utiliza Pixel Art em visão aérea ("God-view").

Diretrizes:
- Cenário de Ilha: Oceano profundo com ondulações, águas rasas cristalinas com espuma de ondas, orla de areia dourada com conchas e estrelas-do-mar, caminhos de terra batida e interior verdejante fértil.
- Sem Avatar Físico: Não existe boneco andando pelo mapa, nem animação de caminhada ou colisão com cercas. O jogador gerencia a ilha de cima.
- Câmera Livre:
  - Arraste com o mouse (pan) para deslizar pelo mapa da ilha com limites suaves.
  - Zoom dinâmico pela roda do mouse (scroll wheel) entre 0.45x e 2.2x, mantendo o ponto sob o cursor estacionário.
  - Controles de zoom acessíveis no HUD: botões `[+]`, `[-]` e `[⌂ Centralizar na Ilha]`.
- Vegetação e Decorações: Palmeiras tropicais nas praias, árvores frutíferas e de madeira no interior, lagoa interna de água doce, píer de madeira e barco de pesca ancorado.
- Talhões com Estágios Visuais Vivos:
  - Vazio: Terra arada escura.
  - Broto: Pequenos brotos verdes viçosos.
  - Crescendo: Folhagem densa correspondente à cultura.
  - Pronto para Colheita: Produto maduro colorido e distintivo flutuante dourado pulsando sobre o talhão.
- Estilo visual: pixel art moderno (pixels nítidos, paleta limpa, sombras suaves), sem aspecto retrô pesado.
- Interface moderna, nítida e responsiva em DOM sobreposto.
- Toda interação deve ser possível apenas com mouse/toque (botões ×1, ×5 e Máx em vez de digitar quantidades).

## 6. MECÂNICAS PRINCIPAIS

O jogo deverá contemplar os seguintes sistemas:

### Agricultura Point & Click
- Compra de sementes e estoque no inventário.
- Plantio por clique: clicar em um talhão vazio abre o seletor com as sementes disponíveis no inventário; 1 clique seleciona e planta imediatamente.
- Acompanhamento visual: hover sobre o talhão exibe o tempo restante até a colheita.
- Colheita por clique: clicar no talhão maduro colhe imediatamente com recompensas flutuantes (+produtos e sementes).
- Colheita rápida: botão no HUD para colher todos os talhões prontos em um único clique.
- Irrigação, fertilizantes e safras recorrentes (com múltiplos ciclos por plantio).

### Estruturas Clicáveis
- Casa da Fazenda: dados da ilha, talhões, área e controle de sessão/logout.
- Mercado e Entreposto: visualização do armazém, venda de produtos e compra de insumos.
- Poço da Ilha: fonte de irrigação e gestão de recursos hídricos.
- Píer e Barco: futuro comércio marítimo e transporte entre ilhas.

### Animais
- Galinhas.
- Vacas.
- Ovelhas.
- Porcos.
- Cabras.
- Abelhas.
- Alimentação.
- Produção animal.
- Melhorias.

### Fabricação
- Moinho.
- Padaria.
- Queijaria.
- Engenho.
- Cozinha.
- Transformação de matérias-primas.

### Fazenda
- Construções.
- Expansão de terrenos.
- Decoração.
- Armazenamento.
- Melhorias.

### RPG
- Nível.
- Experiência.
- Habilidades.
- Profissões.
- Conquistas.
- Equipamentos (bônus passivos, sem avatar físico).
- Exploração (via mapa-múndi e viagens automáticas, sem movimentação manual).

### Mundo
- Cidades.
- Regiões.
- Comerciantes.
- Pontos de interesse.
- Viagens automáticas.
- Entregas.

### Multiplayer econômico
- Mercado global.
- Venda de produtos.
- Compra entre jogadores.
- Trocas diretas.
- Visitação de fazendas.
- Histórico comercial.
- Taxas.
- Controle de inflação.

## 7. ECONOMIA

A moeda inicial será AgroCoin (AGC), exclusivamente interna ao jogo.

Todas as operações financeiras deverão ser validadas pelo backend.

Nunca confiar em valores enviados pelo frontend.

Implementar:
- Histórico de transações.
- Controle de saldo.
- Controle de inventário.
- Taxas comerciais.
- Prevenção contra duplicação de itens.
- Transações atômicas no banco.
- Idempotência em operações sensíveis.
- Auditoria econômica.

A economia deverá ser equilibrada e sustentável.

Não criar mecanismos de emissão ilimitada de moedas.

## 8. PRODUÇÃO OFFLINE

A produção deverá funcionar mesmo quando o jogador fechar o navegador.

Utilize timestamps armazenados no banco.

Quando o jogador retornar:
1. Consultar a última atualização.
2. Calcular o tempo transcorrido.
3. Verificar o tempo de produção.
4. Processar os resultados.
5. Respeitar limites de capacidade.
6. Atualizar os registros.

Nunca depender de um processo individual rodando continuamente para cada jogador.

A produção deverá ser determinística e protegida contra duplicação de recompensas.

## 9. BANCO DE DADOS

Utilizar PostgreSQL.

Principais entidades:
- Users.
- Characters (perfil do jogador: nome de exibição, XP e nível; não representa avatar físico).
- Farms.
- FarmTiles.
- Buildings.
- Crops.
- FarmCrops.
- Animals.
- Items.
- Inventories.
- Recipes.
- ProductionJobs.
- Skills.
- PlayerSkills.
- Regions.
- Journeys.
- MarketListings.
- MarketTransactions.
- TradeOffers.
- TradeItems.
- WalletLedger.
- Achievements.

Utilizar migrations para alterações estruturais.

Não alterar tabelas manualmente sem registrar as mudanças nas migrations.

Criar índices e relacionamentos adequados.

## 10. REGRAS DE DESENVOLVIMENTO

Estas instruções devem ser respeitadas em todas as tarefas:

1. Antes de implementar algo, analise os arquivos existentes.
2. Verifique se já existe uma funcionalidade semelhante.
3. Reutilize componentes e serviços quando adequado.
4. Não duplique funcionalidades.
5. Não remova código funcional sem justificativa.
6. Não sobrescreva arquivos sem verificar seu conteúdo.
7. Não invente bibliotecas ou funções.
8. Utilize dependências estáveis e documentadas.
9. Mantenha tipagem no TypeScript.
10. Valide dados no backend.
11. Trate erros adequadamente.
12. Escreva testes para funcionalidades importantes.
13. Atualize a documentação.
14. Mantenha compatibilidade com os sistemas existentes.
15. Evite soluções temporárias que prejudiquem a arquitetura definitiva.

## 11. FLUXO DE TRABALHO OBRIGATÓRIO

Trabalhe em etapas pequenas.

Para cada funcionalidade:

ETAPA 1 — ANÁLISE
- Entenda o requisito.
- Analise a estrutura existente.
- Identifique dependências.
- Identifique possíveis impactos.

ETAPA 2 — PLANEJAMENTO
- Explique a solução.
- Informe quais arquivos serão criados.
- Informe quais arquivos serão modificados.
- Explique como a funcionalidade se integra ao restante.

ETAPA 3 — IMPLEMENTAÇÃO
- Desenvolva em arquivos separados.
- Siga os padrões existentes.
- Implemente validações.
- Trate erros.

ETAPA 4 — TESTES
- Execute os testes relevantes.
- Verifique erros.
- Corrija problemas.
- Confirme que funcionalidades anteriores continuam funcionando.

ETAPA 5 — DOCUMENTAÇÃO
- Atualize a documentação.
- Registre alterações.
- Informe dependências e comandos necessários.

ETAPA 6 — ENTREGA
Apresente:
- O que foi desenvolvido.
- Arquivos criados.
- Arquivos modificados.
- Testes executados.
- Resultado dos testes.
- Problemas pendentes.
- Próxima etapa recomendada.

Não declare uma funcionalidade concluída se ela não foi testada.

Se faltar alguma informação importante, pergunte antes de tomar decisões que alterem a arquitetura ou o escopo.

## 12. ROADMAP OBRIGATÓRIO

Desenvolver nesta ordem:

FASE 1 — Fundação
- Repositório.
- Docker.
- FastAPI.
- PostgreSQL.
- Phaser.
- Autenticação.
- Documentação.

FASE 2 — Ilha e Câmera Livre (God-view)
- Mapa da ilha em Pixel Art.
- Câmera livre (pan e zoom).
- Estruturas clicáveis (hover e clique).
- Perfil do jogador (sem avatar físico).

FASE 3 — Agricultura
- Sementes.
- Plantio.
- Crescimento.
- Colheita.
- Produção offline.
- Inventário.

FASE 4 — Economia básica
- Moedas.
- Venda para NPCs.
- Compra de sementes.
- Histórico financeiro.

FASE 5 — Produção
- Animais.
- Construções.
- Fabricação.
- Receitas.

FASE 6 — Multiplayer
- Mercado global.
- Trocas.
- Visitação.
- Transações entre jogadores.

FASE 7 — Expansão
- Cidades.
- Regiões.
- Viagens.
- Profissões.
- Conquistas.

FASE 8 — Lançamento
- Segurança.
- Performance.
- Testes.
- Monitoramento.
- Beta fechado.

Não avançar grandes fases deixando funcionalidades fundamentais quebradas.

## 13. MVP — PRIMEIRO OBJETIVO

A primeira versão jogável deverá possuir:

- Cadastro e login.
- Perfil do jogador (nome de exibição).
- Uma fazenda inicial.
- Câmera livre (pan e zoom) sobre o mapa da ilha em Pixel Art.
- Plantio.
- Colheita.
- Produção offline.
- Inventário.
- Venda para NPCs.
- Compra de sementes.
- Experiência e níveis.
- Uma construção melhorável.

O jogador deverá conseguir entrar, plantar, sair, retornar, colher, vender e melhorar sua fazenda.

O multiplayer econômico será desenvolvido depois que esse ciclo estiver funcionando.

## 14. SEGURANÇA

Priorizar:
- Senhas com hash seguro.
- Autenticação adequada.
- Autorização por propriedade.
- Validação no servidor.
- Proteção contra SQL Injection.
- Rate limiting.
- Controle de concorrência.
- Auditoria de transações.
- Backups.
- Proteção contra duplicação de itens.

Nunca expor senhas, tokens ou credenciais no frontend ou repositório.

## 15. DOCUMENTAÇÃO

Manter os seguintes documentos atualizados:

- README.md: instalação e execução.
- AGENTS.md: instruções permanentes.
- GDD.md: regras e mecânicas do jogo.
- API.md: documentação dos endpoints.
- DATABASE.md: estrutura do banco.
- ROADMAP.md: progresso e próximas etapas.
- CHANGELOG.md: histórico de alterações.

## 16. COMPORTAMENTO DO AGENTE

Você atuará como desenvolvedor responsável pela implementação técnica do Agro & Tech.

Priorize qualidade, organização, segurança e manutenção.

Não tente desenvolver o jogo inteiro em uma única resposta ou operação.

Não gere arquivos desnecessários.

Não substitua funcionalidades existentes sem autorização.

Não considere tarefas concluídas apenas porque o código foi escrito.

Trabalhe de forma incremental, mantendo o projeto executável a cada etapa.

Sempre apresente resultados verificáveis e explique decisões técnicas de maneira clara.

O objetivo é construir um jogo real, funcional, escalável e preparado para receber jogadores.

**AGRO & TECH — CULTIVE SUA HISTÓRIA. CONSTRUA SEU LEGADO.**

## 17. CONVENÇÕES OPERACIONAIS

- Idioma: código, comentários, commits e documentação em português; identificadores técnicos em inglês quando padrão.
- Comandos padrão (detalhes no README.md):
  - Subir stack: `docker compose up --build`.
  - Migrations: `alembic upgrade head` (em `backend/`).
  - Testes backend: `python -m pytest` (em `backend/`).
  - Tipagem frontend: `npx tsc --noEmit` (em `frontend/`).
  - E2E: Playwright (em `frontend/`), a partir da Fase 3 concluída.
- Definição de pronto de uma fase: testes backend verdes, `tsc` sem erros, documentação (ROADMAP, CHANGELOG, API, DATABASE) atualizada e commit dedicado.
- Git: um commit por fase ou incremento, mensagem no formato `tipo: descrição` (feat, fix, docs, chore, test). Não manter trabalho de fases concluídas sem commit.
- Arquivo de instruções oficial: `AGENTS.md` (não manter cópias como `AGENTS.md.txt`).
- Economia: valores iniciais de taxas, limites e preços ficam em `backend/app/game/` e devem ser documentados no GDD.md antes de uso.
- Sessão: JWT com expiração configurável via ambiente; nunca armazenar segredos no repositório.
