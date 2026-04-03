# 2026-04-03 — Candidato selecionado oficial na decision_platform

## Contexto

A plataforma já gerava catálogo, ranking, exports e UI, mas ainda havia uma inconsistência importante:

- o pipeline calculava perfis ranqueados, porém não formalizava um único candidato selecionado
- o CLI usava `next(iter(...))`
- a UI montava o estado inicial localmente
- os exports finais existiam, mas não eram amarrados explicitamente ao mesmo candidato por contrato

Isso dificultava auditoria e podia fazer CLI, UI e artefatos apontarem para seleções diferentes.

## Decisão

O conceito oficial passa a ser:

- `default_profile_id`: perfil padrão definido pelo cenário
- `selected_candidate_id`: primeiro candidato do ranking do perfil padrão, já calculado pelo pipeline
- `selected_candidate`: objeto completo correspondente a `selected_candidate_id`

Esse trio é calculado no pipeline e consumido por:

- CLI
- UI
- `summary.json`
- `selected_candidate.json`
- `selected_candidate_routes.json`
- `selected_candidate_bom.csv`
- `selected_candidate_score_breakdown.json`
- `selected_candidate_render.json`

## Regras práticas

### Pipeline

- o pipeline retorna explicitamente `default_profile_id`
- o pipeline retorna explicitamente `selected_candidate_id`
- o pipeline retorna explicitamente `selected_candidate`
- a exportação final usa esse candidato como fonte única

### CLI

- o CLI não decide mais o perfil por ordem implícita
- o CLI reporta `default_profile_id`
- o CLI reporta `selected_candidate_id`

### UI

- a UI abre com o `selected_candidate_id` oficial
- ao trocar perfil, filtros ou pesos, ela recalcula o conjunto visível
- se o selecionado atual sair do conjunto visível, a UI escolhe explicitamente outro candidato visível
- o painel de circuito e o painel de breakdown usam sempre o mesmo candidato atual

## Trade-offs

- o “candidato selecionado” continua sendo uma escolha determinística do ranking, não uma aprovação humana persistida
- a UI mantém estado local de seleção visível, mas o default inicial continua vindo do pipeline
- os testes lentos seguem necessários para validar export e coerência com Julia real

## Resultado

A plataforma passa a ter uma noção única, explícita e auditável de candidato selecionado, sem reabrir arquitetura nem expandir escopo funcional.
