# CLAUDE.md

Orientação para trabalhar neste repositório (`carcaras/solinpy`) com Claude Code.

## O que é o projeto

SolInPy é um SDK Python para Solana (`pip install solinpy`): cliente JSON-RPC (sync/async), gestão de carteiras, airdrop, transferências SPL Token e um runtime dinâmico de Anchor. Ver [README.md](README.md) para a API pública e [TODO.md](TODO.md) para o roadmap.

## Comandos

```bash
pip install -r requirements.txt && pip install -e .   # setup
ruff check .                                           # lint
ruff format --check .                                  # formatação (PEP 8)
mypy solinpy                                            # type check (strict)
pytest -q                                               # testes (integration tests exigem SOLINPY_RUN_DEVNET_INTEGRATION=1, senão são puladas)
pytest -q --cov=solinpy --cov-report=term-missing       # testes com cobertura (gate em .coveragerc, fail_under=75)
bandit -r solinpy -x "*/tests/*,*/test_*.py" -ll        # SAST
pip-audit                                               # vulnerabilidades de dependências
```

CI roda os mesmos checks em `.github/workflows/ci.yml` (lint/typecheck/test em matriz Python 3.10–3.13) e `.github/workflows/security.yml` (bandit + pip-audit), disparados em push/PR para `main` e `develop`.

## Regra de Git — obrigatória, sem exceção

Este repositório segue **GitFlow**, com uma regra adicional definida pelo mantenedor:

- **Nunca commitar ou dar push diretamente na `main`.** A `main` só recebe merge via **Pull Request de `develop` para `main`**, depois de revisão/aceite.
- Todo trabalho (fix, feature, doc, chore) nasce de um branch a partir de `develop` (ou de `main`, quando `develop` estiver desatualizada — deixe isso explícito na descrição do PR) e abre PR **contra `develop`**, nunca contra `main`.
- Nomenclatura de branch: `feature/<slug>`, `bugfix/<slug>`, `hotfix/<slug>`, `release/<versão>` — ver detalhes e regras completas em [ISSUES_MAPEAMENTO.md](ISSUES_MAPEAMENTO.md#8-regra-de-convenção-gitflow).
- Não feche issues do GitHub manualmente ao terminar um PR — referencie com `Closes #<n>` na descrição e deixe o merge fechar automaticamente. Isso evita repetir o problema encontrado na auditoria (issues #31, #32, #33, #37 foram fechadas como "Completed" sem o código correspondente nunca ter chegado à `main`).
- CI (lint + mypy strict + pytest em matriz + bandit + pip-audit) precisa estar verde antes de qualquer merge.

## Contexto útil

- [ISSUES_MAPEAMENTO.md](ISSUES_MAPEAMENTO.md) — auditoria completa do projeto: o que está implementado, problemas encontrados (segurança, CI, branches órfãs, issues fechadas sem código), PRs abertos e plano de ação priorizado. Consulte antes de assumir o estado do repo.
- [SKILLS.md](SKILLS.md) — skills do Claude Code relevantes para este projeto e quando usá-las.
