# Estratégia de branch

## Recomendação
Manter o repositório atual e abrir um **novo branch de grande mudança arquitetural**.

## Razões
1. O baseline atual continua valioso como referência.
2. A comparação antes/depois fica objetiva.
3. A auditoria posterior fica muito mais simples.
4. O time não precisa redistribuir infra e permissões agora.

## Regras para o branch novo
- não quebrar o baseline legado;
- nova arquitetura entra em módulos/pastas próprias;
- cenários antigos continuam rodando;
- a nova plataforma nasce paralela;
- o README principal deve passar a apontar:
  - baseline legado;
  - nova arquitetura;
  - status da migração.

## Nome sugerido
`feature/new-architecture-watermodels-decision-platform`
