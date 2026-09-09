# Skills do Claude Code relevantes para o SolInPy

Levantamento das skills disponíveis no catálogo do Claude Code que se aplicam a este projeto (SDK Python cliente para Solana — não um programa on-chain), com a razão de cada uma e quando invocar. Objetivo: não redescobrir isso a cada sessão nova.

> Nota importante de escopo: a maioria das skills de "vulnerability scanner" do catálogo (`solana-vulnerability-scanner`, `cairo-vulnerability-scanner`, `cosmos-vulnerability-scanner`, `substrate-vulnerability-scanner`, `algorand-vulnerability-scanner`, `ton-vulnerability-scanner`, etc.) audita **programas on-chain** (Rust/Anchor, Move, Cairo...). O SolInPy **não escreve programas on-chain**, é um SDK cliente Python que fala JSON-RPC — essas skills não se aplicam aqui. O que se aplica é segurança de **cliente Python**, gestão de chaves privadas local e supply chain de dependências.

## Já aplicadas nesta auditoria (2026-09-09)

| Skill/ferramenta | Uso feito | Resultado |
|---|---|---|
| `security-review` (conceito aplicado manualmente com `bandit`) | Scan estático em `solinpy/` | Sem achados médios/altos; falsos positivos de baixo risco documentados (ver [ISSUES_MAPEAMENTO.md](ISSUES_MAPEAMENTO.md)) |
| Auditoria de supply chain (conceito de `supply-chain-risk-auditor` aplicado com `pip-audit`) | Rodado localmente e agora contínuo via `.github/workflows/security.yml` | Achou `pytest==8.4.2` vulnerável (PYSEC-2026-1845) → corrigido para `9.1.1` |
| `code-review` (built-in) | Base para a auditoria de PRs/issues em [ISSUES_MAPEAMENTO.md](ISSUES_MAPEAMENTO.md) | — |

## Recomendadas para próximos passos (ainda não executadas — invocar quando chegar a hora)

| Skill | Quando usar aqui |
|---|---|
| **`supply-chain-risk-auditor`** | Antes de aceitar PR #46 (consolidação de dependências, issue #41) — reavaliar `solders`, `mnemonic`, `httpx` e qualquer dependência nova antes de fixar versões definitivas no `pyproject.toml`. |
| **`modern-python`** | Ao resolver a issue #41 de verdade: orienta migração de `pip`/`requirements.txt` para `pyproject.toml` com extras (`[project.optional-dependencies].dev`), e uso de `uv`/`ruff`/`ty` como stack moderna. Ler antes de revisar/reescrever PR #46. |
| **`property-based-testing`** | `solinpy/anchor/borsh.py` (53% de cobertura) e `solinpy/transaction/token.py` (62%) fazem serialização binária — bom candidato a testes baseados em propriedade (roundtrip serialize/deserialize) em vez de só exemplos fixos. Relacionado à issue #43 (cobertura de testes). |
| **`security-review`** (execução completa da skill, não só bandit) | Revisão dedicada de `solinpy/wallet/manager.py` e `solinpy/wallet/mnemonic.py` (geração/import de chave privada, derivação BIP39/SLIP-0010) antes de qualquer release — é o código mais sensível do SDK. |
| **`constant-time-analysis`** | Mesmo alvo (`mnemonic.py`, derivação Ed25519). Prioridade baixa/média: é derivação local one-shot, não um oráculo de rede, mas vale uma checagem pontual antes de um release maior. |
| **`wycheproof`** | Validar a derivação SLIP-0010/Ed25519 em `mnemonic.py` contra vetores de teste conhecidos — ajudaria a fechar a issue #43/qualidade geral de testes de carteira. |
| **`differential-review`** | Usar em todo PR de `develop` → `main` (release) daqui pra frente — é o ponto de maior risco no fluxo GitFlow definido em [ISSUES_MAPEAMENTO.md](ISSUES_MAPEAMENTO.md#8-regra-de-convenção-gitflow). |
| **`python-project-structure`** | Ao executar a limpeza do item 9 do plano de ação (`.md` soltos dentro de `solinpy/client`, `solinpy/wallet`, `solinpy/utils/docs`, `solinpy/tests/teste.md`) — orienta onde cada tipo de arquivo deveria morar. |
| **`technical-writing`** | Ao revisar/mesclar PR #47 (docs de Anchor/Utils, issue #42) e ao atualizar o README para citar o módulo Anchor e o fluxo de mint/NFT hoje "escondidos" (achado 15 do audit). |
| **`init`** | Se o código mudar substancialmente (novos módulos, reestruturação), rodar para regenerar/expandir o [CLAUDE.md](CLAUDE.md) — hoje ele foi escrito manualmente a partir do contexto já levantado nesta auditoria. |
| **`semgrep`** | Complemento ao `bandit` se o projeto crescer (taint tracking cross-file); não adicionado ao CI agora para não duplicar cobertura sem necessidade — reavaliar se `bandit` começar a passar despercebido algo relevante. |

## Não aplicáveis / fora de escopo

- Todas as `*-vulnerability-scanner` de smart contracts (Solana/Anchor Rust, Cairo, Cosmos, Substrate, Algorand, TON, Solidity) — este projeto não escreve/audita programas on-chain.
- Fuzzing de C/C++ (`libfuzzer`, `aflpp`, `cargo-fuzz`, `atheris` p/ CPython nativo) — SolInPy é Python puro sobre `solders`/`httpx`; não há superfície de memória insegura própria para fuzzar.
- Skills de frontend/design (`impeccable`, `design`, `dataviz`, Figma) — sem interface visual no projeto.
- Skills de outras linguagens/frameworks (`golang-*`, `node`, `fastapi-python`, `spring-boot-engineer`, `websocket-engineer` genérico) — a não ser que o roadmap do `TODO.md` (wallet adapter web, Solana Pay) traga um componente nessas stacks no futuro.

---

*Atualize esta lista quando uma skill listada aqui for de fato executada, ou quando surgir uma necessidade nova (ex.: se o SDK ganhar um componente web/CLI, revisitar as skills de frontend/CLI).*
