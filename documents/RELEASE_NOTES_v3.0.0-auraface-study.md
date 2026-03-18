# Release Notes - v3.0.0-auraface-study

Data: 2026-03-18

## Objetivo
Versionar o baseline de estudos do AuraFace em pipeline independente do software principal.

## Entregas principais
- Pipeline limpo de avaliacao 1:1 com AuraFace via InsightFace.
- Barra de progresso e heartbeat em execucoes longas para evitar duvida de travamento.
- Geracao de artefatos de estudo:
  - raw_scores.csv
  - threshold_sweep.csv
  - summary.json
  - report.md
- Suporte a pares genuinos (doc x cam) e pares impostores.
- Sweep de threshold para apoiar calibracao de decisao.

## Parametros base usados nos estudos
- detector: SCRFD (pack do InsightFace)
- det_thresh: 0.50
- det_size: 640x640
- limiar verificado: 70.0% (equivalente a cos >= 0.4)
- limiar atencao: 65.0%

## Resultado inicial registrado (recorte de 2k pares)
- pares genuinos: 2000
- pares impostores: 2000
- comparacoes avaliadas: 4000 linhas
- taxa ambos detectados: ~51.28%
- threshold atual 70.0%: FAR 0.00%, FRR 15.63%
- EER aproximado: 12.43% em threshold ~58.5%

## Observacoes de versionamento
- Arquivos de dados e artefatos volumosos estao excluidos do versionamento via .gitignore.
- Esta tag marca baseline tecnico para proximas comparacoes de detector/threshold.
