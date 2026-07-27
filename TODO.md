# Roadmap SolInPy 🚀

Este arquivo mapeia a direção que o SDK **SolInPy** está tomando. Nosso objetivo principal é consolidar o SolInPy como o framework Python de alto nível definitivo para Solana, reduzindo a complexidade de desenvolvimento (DX) ao mínimo e integrando todas as ferramentas necessárias em um único produto.

---

## 🛠️ Status Atual (MVP Completo)

- [x] **Cliente RPC Síncrono e Assíncrono (`httpx` / `urllib`):**
  - Métodos core com suporte a timeouts, retries exponenciais e tratamento amigável de erros de RPC (como saldo insuficiente ou blockhash expirado).
- [x] **Gerenciamento de Carteiras:**
  - Geração de chaves públicas/privadas, importação de chaves CLI JSON e importação segura de seed phrases BIP39 com derivação SLIP-0010 (Ed25519).
- [x] **Utilitários e Auxiliares:**
  - Airdrops fáceis em redes de testes (devnet/testnet) com confirmação automática na blockchain.
- [x] **Operações SPL Token simplificadas:**
  - Função de transferência rápida que descobre, deriva e cria dinamicamente e de forma atômica a conta de token associada (ATA) do receptor caso ela não exista.
- [x] **Decodificador Binário de Contas (`account_decoder`):**
  - Módulo utilitário para converter os bytes de dados das contas Solana para dicionários legíveis (suporta contas normais e Token Accounts/Mints).
- [x] **Módulo Anchor (Runtime Dinâmico):**
  - Classe `Program` capaz de ler arquivos de IDL JSON do Anchor em tempo de execução, calcular discriminadores de instruções via hash sha256 e serializar os parâmetros automaticamente via Borsh nativo.

---

## 📅 Roadmap Futuro

### Curto Prazo (Pós-Hackathon & Polimento)
- [ ] **CLI de Geração de Código (`solinpy-gen`):**
  - Desenvolver uma ferramenta de terminal que lê uma IDL JSON do Anchor e gera classes Python com tipagem estática e stubs (`.pyi`). Isso habilitará autocomplete perfeito nas IDEs (VS Code/PyCharm) para os métodos do smart contract (Abordagem 2 do design).
- [ ] **Suporte a SPL Token 2022:**
  - Estender o módulo de transações para suportar as extensões do novo padrão de tokens da Solana (transfer fees, confidential transfers, etc.).
- [ ] **Suporte a NFTs e cNFTs (Compressed NFTs):**
  - Facilitar a criação e transferência de coleções digitais e NFTs comprimidos utilizando a API de compressão de estado.

### Médio Prazo (Integrações & Infraestrutura)
- [ ] **Adapter de Carteiras Web (Wallet Adapter Python):**
  - Permitir a assinatura de transações e conexão direta com carteiras populares de navegador (como Phantom, Backpack ou Solflare) em aplicações Python/React (ex: via web sockets ou pontes RPC).
- [ ] **Integração com Solana Pay:**
  - Módulos auxiliares para gerar QRCodes de pagamento padrão Solana Pay e verificar transações de forma simples.

### Longo Prazo (Ecossistema)
- [ ] **Templates Prontos para DApps:**
  - Criar "boilerplates" de bots de arbitragem, pipelines de dados on-chain de alta performance e dashboards DeFi completos construídos 100% sobre SolInPy (integrado com o site oficial).
