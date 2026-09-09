# SolInPy — Mapeamento do Projeto, Problemas e Regras de GitFlow

> Documento gerado em auditoria do repositório `carcaras/solinpy` (branch `main`, commit `5ee9f50`).
> Cobre: propósito do projeto, estado atual, branches, PRs, issues abertas/fechadas e recomendações.
> Ver também [CLAUDE.md](CLAUDE.md) (regras de trabalho neste repo) e [SKILLS.md](SKILLS.md) (skills do Claude Code relevantes para este projeto).
> Itens marcados com ✅ já foram resolvidos nesta sessão — ver histórico de commits/PRs para o branch correspondente.

---

## 1. O que o projeto propõe

**SolInPy** é um SDK Python para Solana (`pip install solinpy`), focado em três pilares (ver [README.md](README.md)):

- Cliente JSON-RPC (sync `SolanaRPCClient` e async `AsyncSolanaRPCClient`) com retries, timeout e tratamento de erro amigável.
- Gestão de carteiras (`WalletManager`): geração de keypair, import de JSON de CLI e import de seed BIP39/SLIP-0010.
- Helpers de alto nível: airdrop (`request_airdrop`/`create_airdrop`), transferência de SPL Token (`send_token_transfer`, com criação automática de ATA), decodificação binária de contas (`account_decoder`) e um runtime dinâmico de Anchor (`solinpy.anchor.program.Program`, IDL → Borsh).

O [TODO.md](TODO.md) declara o MVP como "completo" (RPC sync/async, wallets, airdrop, SPL transfer, account decoder, módulo Anchor) e projeta um roadmap: CLI `solinpy-gen` para IDL→stubs tipados, SPL Token-2022, NFTs/cNFTs, wallet adapter web, Solana Pay, templates de dApp.

## 2. O que já foi feito (estado real na `main`)

Confirmado por leitura do código-fonte (`solinpy/`):

| Área | Status | Evidência |
|---|---|---|
| Cliente RPC sync | ✅ Implementado | [solinpy/client/client.py](solinpy/client/client.py) |
| Cliente RPC async | ✅ Implementado, mas **sem docs no README** e **sem mock async** (issue #43) | [solinpy/client/async_client.py](solinpy/client/async_client.py) |
| WalletManager (gerar/importar) | ✅ Implementado | [solinpy/wallet/manager.py](solinpy/wallet/manager.py) |
| Seed BIP39/SLIP-0010 | ✅ Implementado | [solinpy/wallet/mnemonic.py](solinpy/wallet/mnemonic.py) |
| Airdrop | ✅ Implementado | [solinpy/utils/airdrop.py](solinpy/utils/airdrop.py) |
| SPL Token transfer + ATA | ✅ Implementado | [solinpy/transaction/token.py](solinpy/transaction/token.py) |
| Mint / InitializeMint / SetAuthority (usado em `examples/mint_nft.py`) | ✅ Implementado no código, mas **não documentado nem citado no README/TODO** | [solinpy/transaction/token.py](solinpy/transaction/token.py) |
| Account decoder | ✅ Implementado | [solinpy/utils/account_decoder.py](solinpy/utils/account_decoder.py) |
| Módulo Anchor (Program/Borsh) | ✅ Implementado, **sem referência de API** (issue #42, PR #47 aberto) | [solinpy/anchor/program.py](solinpy/anchor/program.py), [solinpy/anchor/borsh.py](solinpy/anchor/borsh.py) |
| WebSocket client (real-time) | ❌ **Não está na `main`**, apesar da issue #37 estar fechada como "Completed" | ver seção 5 |
| `export_to_json` no WalletManager | ❌ **Não está na `main`**, apesar da issue #31 estar fechada como "Completed" | ver seção 5 |
| `create_token_mint` wrapper nativo | ❌ **Não está na `main`**, apesar da issue #32 estar fechada como "Completed" | ver seção 5 |
| Decoder de metadata Metaplex/NFT | ❌ **Não está na `main`**, apesar da issue #33 estar fechada como "Completed" | ver seção 5 |
| CLI `solinpy-gen` (IDL → stubs) | ❌ Não implementado (roadmap) | — |
| SPL Token-2022 | ❌ Não implementado (roadmap) | — |

## 3. Problemas encontrados

### 🔴 Crítico

1. **Chave privada de carteira commitada em repositório público.**
   [my-wallet.json](my-wallet.json) está versionado na raiz do repo (`git ls-files` confirma que está rastreado) e contém um array de 64 bytes no formato de secret key da Solana CLI. O repositório é **público** (`gh repo view` → `visibility: PUBLIC`). Mesmo que seja uma wallet de teste/devnet, qualquer chave nesse formato deve ser tratada como comprometida assim que publicada.
   **Ação recomendada:** remover o arquivo, adicionar `*.json` de wallet (ou nome específico) ao `.gitignore`, e — o mais importante — **considerar a chave queimada**: se essa keypair já recebeu fundos em qualquer rede (inclusive mainnet), transferir os fundos antes de descartá-la. Reescrever o histórico do git (`git filter-repo`/BFG) para remover o blob, já que só apagar no HEAD não remove do histórico público.

2. ~~**CI está quebrada na `main`.**~~ ✅ **Corrigido** (branch `bugfix/fix-broken-ci-mypy-strict`, PR pendente de abertura contra `develop`).
   Causa raiz: 17 erros de `mypy --strict` em [solinpy/client/client.py](solinpy/client/client.py), [solinpy/client/async_client.py](solinpy/client/async_client.py), [solinpy/utils/account_decoder.py](solinpy/utils/account_decoder.py) e [solinpy/utils/airdrop.py](solinpy/utils/airdrop.py). Um deles era um bug real, não só de tipagem: `get_token_accounts_by_owner` chamava `address.strip()` num parâmetro tipado `str | Pubkey` — passar um `Pubkey` (permitido pela própria assinatura) quebrava em runtime com `AttributeError`; corrigido usando `_normalize_address()`. Os demais eram `Any` vazando de `json.loads`/`struct.unpack`/indexação de `dict[str, Any]` e tipos genéricos sem parâmetro (`dict`/`list`) — corrigidos com anotações explícitas e `cast`. `2**attempt` também foi trocado por `2.0**attempt` no cálculo de backoff (em ambos os clientes) porque o mypy não consegue provar o tipo de `int ** int` com expoente variável.
   CI também foi reestruturada (`.github/workflows/ci.yml`): jobs paralelos `lint` (ruff check + `ruff format --check`), `typecheck` (mypy) e `test` (matriz Python 3.10–3.13 com cobertura via `pytest-cov`, gate real em `.coveragerc` ajustado de `fail_under=100` — nunca cumprido, pois o CI nunca rodava com `--cov` — para `75`, refletindo a cobertura real de ~81%). Novo `.github/workflows/security.yml` com `bandit` (SAST) e `pip-audit` (dependências vulneráveis), rodando em push/PR para `main`/`develop` e semanalmente. `pip-audit` já pegou e corrigiu uma CVE real em `pytest==8.4.2` (PYSEC-2026-1845 → bump para `9.1.1`).
   Isso desbloqueia com segurança o pedido da issue #39 (cortar um novo release `0.1.8`/`0.1.7.post1`): antes, publicar seria repetir o mesmo padrão que gerou aquela issue (release cortado sem CI verde).

### 🟠 Alto

3. **Issues fechadas como "Completed" sem o código correspondente estar na `main`.** Trabalho real existe em branches que nunca foram mescladas:
   - #37 (WebSocket client) → código em `origin/feature/realtime-websocket` ([solinpy/client/websocket.py](solinpy/client/websocket.py)), não está em `main`.
   - #31 (`export_to_json`) e #32 (`create_token_mint`) → código em `origin/bugfix/updates`, não está em `main`.
   - #33 (decoder Metaplex/NFT) → não há nenhum código correspondente em nenhuma branch encontrada; parece fechada sem entrega.
   **Ação recomendada:** reabrir essas issues ou abrir PRs a partir dessas branches, revisar o código (inclusive a mistura de arquivos `.ai/` e `contexto_solinpy.json` de 1124 linhas dentro de `feature/realtime-websocket`, que parece lixo de sessão de agente e não deve ir para `main`), e só então fechá-las de fato.

4. **Release 0.1.7 no PyPI está obsoleto e quebrado (issue #39).** PR #40 já corrigiu a causa raiz na `main` (import de `Pubkey`, dependência `spl` perigosa), mas **nenhuma versão nova foi publicada** — e agora a CI quebrada (item 2) impede publicar com confiança. Existe um PR #45 (`chore: bump version to 0.1.7.post1`) parado, e uma branch órfã `release/v0.1.7.post1` idêntica a ele.

### 🟡 Médio

5. **Duplicação de dependências (`pyproject.toml` + `requirements.txt`)** — issue #41 aberta pedindo exatamente isso. Hoje `requirements.txt` mistura dependências de runtime e dev (`pytest`, `mypy`, `ruff`) enquanto `pyproject.toml` não tem `[project.optional-dependencies].dev`, então o critério de aceite da issue #41 ("`pip install .[dev]`") ainda não é possível.
6. **Mock assíncrono incompleto** — issue #43 aberta: `solinpy/client/rpc_mock.py` cobre só chamadas síncronas; `test_async_client.py` provavelmente depende de rede real hoje.
7. **Documentação incompleta** — issue #42 aberta (Anchor/Utils sem página em `docs/api/`), já endereçada pelo PR #47 (aberto, não mesclado).
8. **Branch `develop` está desatualizada e insegura.** Divergiu de `main` apenas em `pyproject.toml`/`requirements.txt`, mas a versão de `develop` ainda tem `solana>=0.36.11`, `requests>=2.31.0` e `spl` — exatamente as dependências perigosas que a issue #39 corrigiu na `main`. Se alguém abrir PR de `develop` para `main` sem cuidado, reintroduz o bug.
9. **Docs espalhadas dentro do pacote, duplicando `docs/`:** [solinpy/client/client.md](solinpy/client/client.md), [solinpy/utils/CLIENT.md](solinpy/utils/CLIENT.md), [solinpy/wallet/wallet.md](solinpy/wallet/wallet.md), [solinpy/utils/docs/RESUMO_AIRDROP.md](solinpy/utils/docs/RESUMO_AIRDROP.md) e [solinpy/tests/teste.md](solinpy/tests/teste.md) (nome de arquivo sugere rascunho/teste esquecido). Confunde qual é a fonte de verdade da documentação (deveria ser só `docs/`, servido pelo MkDocs).
10. **Relatórios de teste gerados versionados na raiz:** [tests_individual_report.md](tests_individual_report.md) (33 KB) e [tests_structured_report.md](tests_structured_report.md) (29 KB) parecem artefatos gerados automaticamente (não há script no repo que os produza) e não deveriam estar no controle de versão — deveriam ir para `.gitignore` ou para um artifact de CI.

### 🟢 Baixo

11. **Branch órfã com nome de projeto antigo:** `origin/feat/transactions` referencia um pacote `solpy/` (não `solinpy/`) — resíduo de quando o repo se chamava `solana-hackathon`. Está obsoleta e deve ser apagada.
12. **Branches já mescladas mas não apagadas:** `copilot/fix-attributeerror-solanarpclient`, `fix/critical`, `fix/stale-release-issue-39`, `release/v0.1.7.post1` têm diff zero contra `main` — são candidatas seguras para deleção.
13. **Histórico de merges desorganizado:** branches como `feature/mock` e `bugfix/bugs` geraram múltiplos PRs sucessivos (#12/#18/#19/#20 e #22/#23/#24) a partir do mesmo branch, sinal de que branches não foram encerradas após o merge — é exatamente o tipo de coisa que a convenção de GitFlow abaixo evita.
14. **Nomenclatura de branch inconsistente:** o repo mistura `feature/` e `feat/`, `bugfix/` e `fix/` para o mesmo propósito. Padronizar (ver seção 6).
15. **`examples/mint_nft.py`** usa API real do SDK (`initialize_mint`, `mint_to`, `set_authority`) mas não tem teste automatizado e não é citado no README nem no TODO — funcionalidade "escondida".
16. ~~**`.coveragerc` exige `fail_under = 100`**, mas o workflow de CI roda `pytest -q` sem `--cov`~~ ✅ **Corrigido**: `fail_under` ajustado para `75` (cobertura real ~81%) e o job `test` do CI agora roda com `--cov=solinpy --cov-report=term-missing`, tornando o gate real.

## 4. PRs abertos (precisam de ação)

| PR | Título | Diff | Observação |
|---|---|---|---|
| [#45](https://github.com/carcaras/solinpy/pull/45) | chore: bump version to 0.1.7.post1 | `pyproject.toml` (1 linha) | CI falhando (mesmo problema de mypy do item 2). Não fazer merge/publicar até CI ficar verde. |
| [#46](https://github.com/carcaras/solinpy/pull/46) | chore: consolidate dependencies in pyproject.toml | `ci.yml`, `README.md`, `pyproject.toml`, `requirements.txt`, doc solta | Resolve parte da issue #41; CI com status `action_required` (workflow aguardando aprovação, comum em PR de contribuidor externo). Revisar se remove `requirements.txt` por completo e resolve o item 5 (extras `dev`). |
| [#47](https://github.com/carcaras/solinpy/pull/47) | docs: add API reference for Anchor and Utils | `docs/api/anchor.md`, `docs/api/utils.md`, `mkdocs.yml` | Resolve a issue #42. CI também em `action_required`. |

## 5. Branches com trabalho não mesclado (revisar antes de descartar)

- **`origin/bugfix/updates`** — tem `export_to_json` (WalletManager) e `create_token_mint` nativo, com testes (`test(token): cover create_token_mint flow...`, `test(wallet): add export/import round-trip test`). Cobre as issues #31 e #32, fechadas indevidamente sem esse código estar na `main`.
- **`origin/feature/realtime-websocket`** — implementa `SolanaWebSocketClient` ([solinpy/client/websocket.py](solinpy/client/websocket.py)) e exemplo (`examples/realtime_balance_tracker.py`), cobrindo a issue #37. **Atenção:** o mesmo commit também traz `.ai/agents/`, `.ai/skills/*.md` e `contexto_solinpy.json` (1124 linhas) — isso parece configuração/contexto de agente de IA que vazou para o commit e não deveria ir para `main`; extrair só o código do cliente antes de mesclar.

## 6. Issues abertas mapeadas

| Issue | Título | Ação recomendada |
|---|---|---|
| [#38](https://github.com/carcaras/solinpy/issues/38) | Feature: Token Minting via Pure Python SDK | A proposta pede uma classe `SolinpyClient` que **não existe** no SDK atual (API real é `SolanaRPCClient` + `send_token_transfer`/`initialize_mint`/`mint_to`). Antes de implementar, alinhar se a issue deve ser reescrita para usar a API existente, já que boa parte do mint já existe em `transaction/token.py` e é usada em `examples/mint_nft.py`. |
| [#39](https://github.com/carcaras/solinpy/issues/39) | PyPI release 0.1.7 obsoleto/quebrado | Correção de código já está na `main` (PR #40). **Bloqueado** até a CI (item 2) ficar verde; só então mesclar #45 e publicar `0.1.8`/`0.1.7.post1`. |
| [#41](https://github.com/carcaras/solinpy/issues/41) | Consolidar dependências (remover `requirements.txt`) | Em progresso via PR #46 — validar que cobre extras `dev` e atualiza `ci.yml`. |
| [#42](https://github.com/carcaras/solinpy/issues/42) | Docs de Anchor e Utils | Em progresso via PR #47 — revisar e mesclar. |
| [#43](https://github.com/carcaras/solinpy/issues/43) | Mock async para RPC | Ainda sem PR. Prioridade média-alta: sem isso, `test_async_client.py` provavelmente bate em rede real. |
| [#44](https://github.com/carcaras/solinpy/issues/44) | Parser automático de IDL Anchor | Roadmap "curto prazo" do TODO.md (`solinpy-gen`). Sem PR ainda; depende do módulo Anchor atual, que já está funcional. |

## 7. Plano de ação priorizado

1. **Segurança imediata:** remover/rotacionar `my-wallet.json` e limpar o histórico do git (item 1). **Ainda pendente.**
2. ~~**Destravar CI:**~~ ✅ **Feito** — ver item 2 da seção 3. CI reestruturada com jobs de lint/type/test (matriz) + workflow de segurança (bandit + pip-audit) em `main`/`develop`.
3. **Fechar o ciclo da issue #39:** mesclar #45 (ou #46 se já incluir o bump) só depois do CI verde, publicar release no PyPI.
4. **Revisar `bugfix/updates` e `feature/realtime-websocket`**, extrair o código útil (sem os arquivos `.ai/`), abrir PRs formais, e só então fechar/reabrir #31, #32, #33, #37 de acordo com o resultado.
5. **Mesclar #46 e #47** (dependências e docs), já abertos e de baixo risco.
6. **Limpeza de repositório:** apagar branches já mescladas (item 12) e a branch obsoleta `feat/transactions` (item 11); mover ou remover os `.md` soltos dentro de `solinpy/` (item 9); tirar `tests_individual_report.md`/`tests_structured_report.md` do controle de versão (item 10).
7. **Endereçar #43** (mock async) antes de expandir mais o `async_client`.
8. Só depois seguir para features novas (#38, #44) e o roadmap de médio/longo prazo do `TODO.md`.

---

## 8. Regra de convenção: GitFlow

A partir de agora, este repositório segue **GitFlow** como convenção obrigatória de branches, commits e PRs.

### 8.1 Branches permanentes

- `main` — sempre reflete o **último release publicado** no PyPI. Só recebe merge de `release/*` ou `hotfix/*`. Nunca commit direto.
- `develop` — branch de integração; reflete o próximo release em preparação. Toda `feature/*` nasce daqui e volta para cá via PR.
  > Ação imediata: `develop` está desatualizada e ainda contém as dependências inseguras do `pyproject.toml` corrigidas na `main` (item 8). Antes de voltar a usá-la, resetar `develop` a partir da `main` atual.

### 8.2 Branches de apoio (nomenclatura obrigatória)

| Prefixo | Nasce de | Volta para | Uso |
|---|---|---|---|
| `feature/<slug>` | `develop` | `develop` | Nova funcionalidade (ex.: `feature/idl-parser` para a issue #44). Nunca usar `feat/`. |
| `bugfix/<slug>` | `develop` | `develop` | Correção de bug não urgente encontrado em `develop`. Nunca usar `fix/` para isso. |
| `hotfix/<slug>` | `main` | `main` **e** `develop` | Correção urgente em produção/release já publicado (ex.: o cenário da issue #39 seria `hotfix/pypi-release-stale`). |
| `release/<versão>` | `develop` | `main` **e** `develop` | Preparação de release (bump de versão, changelog, últimos ajustes). Ex.: `release/0.1.8`. |

Regras adicionais:

- **Um branch, um PR.** Depois do merge, apagar o branch remoto imediatamente (evita o padrão visto em `feature/mock`/`bugfix/bugs`, que geraram 3+ PRs cada a partir do mesmo branch reaproveitado).
- **Nunca commitar segredos** (chaves privadas, `.env`, wallets) — `*.json` de keypair deve estar no `.gitignore`; usar variável de ambiente ou arquivo local não versionado para wallets de teste.
- **CI obrigatoriamente verde antes do merge** em qualquer branch de apoio para `develop`/`main` — `ruff`, `mypy --strict` e `pytest` precisam passar (hoje isso está quebrado, ver item 2; é bloqueante para adotar a regra de verdade).
- **PR fecha a issue automaticamente**: usar `Closes #<n>` na descrição do PR; issues só se fecham quando o PR correspondente é mesclado — não fechar manualmente uma issue sem o código estar em `main`/`develop` (é o que gerou o problema do item 3).
- **Commits em Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`), como já vem sendo usado nos commits mais recentes (`fix:`, `chore:`, `feat(Transaction):`) — manter e exigir em todos os PRs.
- **Tags de versão** só na `main`, criadas a partir do merge de `release/*` ou `hotfix/*`, no formato `vX.Y.Z` (ex.: `v0.1.8`), e cada tag deve corresponder a uma publicação real no PyPI (evitar o cenário da issue #39, em que a tag existia mas ficou desatualizada em relação à `main`).

---

*Este documento é um retrato do repositório em 2026-09-09. Deve ser revisitado após a execução dos itens do plano de ação (seção 7).*
