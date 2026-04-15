# Prompt para Codex — Projeto Quantitativo Mini Índice (WIN)

## Objetivo

Atuar como um **quant developer + analista matemático/estatístico**, construindo um notebook `.ipynb` completo para análise de:

- Gap de abertura
- Comportamento intraday
- Padrões dos últimos 15 minutos (pré-close)
- Criação de datasets derivados
- Formulação matemática de targets e labels
- Análise estatística robusta (sem achismo)

---

# 1. Requisitos do Notebook

- Linguagem: Python
- Bibliotecas:
  - pandas
  - numpy
  - matplotlib
  - scipy
  - sklearn (opcional)

- Estrutura:
  - Modular (células independentes)
  - Executável parcialmente
  - Comentado em português
  - Código limpo e reutilizável

- Saídas:
  - DataFrames derivados
  - CSV/Parquet
  - Gráficos
  - Tabelas estatísticas

---

# 2. Contexto Matemático

Modelar o problema como:

P(Yₜ₊₁ | Xₜ)

Onde:

- Xₜ = features do dia t (principalmente pré-close)
- Yₜ₊₁ = eventos do dia seguinte:
  - direção do gap
  - fill
  - retorno
  - green/loss

---

# 3. Fórmulas Fundamentais

## 3.1 Gap

GAPₜ = Openₜ - Closeₜ₋₁

GAP% = (Openₜ - Closeₜ₋₁) / Closeₜ₋₁

Opcional:

GAP_ATR = GAP / ATR

---

## 3.2 Direção do Dia

Green = Closeₜ > Openₜ  
Loss = Closeₜ < Openₜ

---

## 3.3 Gap Positivo / Negativo

GapPos = Openₜ > Closeₜ₋₁  
GapNeg = Openₜ < Closeₜ₋₁

---

## 3.4 Gap Fill

Gap positivo:

GapFill = Lowₜ ≤ Closeₜ₋₁

Gap negativo:

GapFill = Highₜ ≥ Closeₜ₋₁

---

## 3.5 Estrutura de Target

T = α \* |P_ref - P_entry|

α ∈ {0.3, 0.5, 0.7, 1.0}

---

## 3.6 Compra

Fechamento:

Fechou⁺ = (Closeₜ₊ₙ - Pc) > T

Trajetória:

Fechou⁺ = High ≥ Pc + T

---

## 3.7 Venda

Fechamento:

Fechou⁻ = (Pv - Closeₜ₊ₙ) > T

Trajetória:

Fechou⁻ = Low ≤ Pv - T

---

## 3.8 Tempo até alvo

τ = min(n: preço atinge target)

---

## 3.9 MFE / MAE

MFE = max(preço favorável - entrada)  
MAE = max(entrada - preço adverso)

---

# 4. Estrutura de Dados

## 4.1 Dataset Intraday

Campos esperados:

- datetime
- open
- high
- low
- close
- volume

---

## 4.2 Dataset Diário

- open
- high
- low
- close
- range
- retorno
- volume
- ATR

---

## 4.3 Dataset de Gap

- gap absoluto
- gap %
- gap ATR
- direção
- bins
- fill
- fill parcial
- tempo até fill
- retorno (5, 15, 30 min)
- retorno fechamento
- MFE / MAE

---

## 4.4 Dataset Pré-Close

Janela: últimos 15 min (parametrizável)

Features:

- retorno da janela
- range
- volatilidade
- volume
- posição no range do dia
- intensidade
- direção

Fórmula:

R_preclose = (Close_fim - Close_inicio) / Close_inicio

Posição no range:

Pos = (Close - Low) / (High - Low)

---

## 4.5 Dataset de Eventos

Cada linha representa uma operação:

- entrada
- referência
- target
- stop
- bateu target
- bateu stop
- pnl
- mfe
- mae
- tempo

---

# 5. Segmentações

## 5.1 Bins de Gap

- 0–50
- 50–100
- 100–150
- 150–200
- 200+

Ou usar quantis

---

## 5.2 Janelas

- 5 min
- 15 min
- 30 min
- fechamento

---

## 5.3 Targets

- 30%
- 50%
- 70%
- 100%

---

## 5.4 Referências

- open
- close anterior
- high
- low
- gap
- range anterior
- ATR

---

# 6. Formulações Importantes

## 6.1 Target baseado no Open

T = 0.7 \* |Open - entrada|

---

## 6.2 Compra

Fechou⁺ = (Close - Pc) > T  
Fechou⁺ = High ≥ Pc + T

---

## 6.3 Venda

Fechou⁻ = (Pv - Close) > T  
Fechou⁻ = Low ≤ Pv - T

---

## 6.4 Gap Fill Parcial

GAP = Open - Closeₜ₋₁

TargetFill = α \* |GAP|

Gap positivo:

Nível = Open - TargetFill

Gap negativo:

Nível = Open + TargetFill

---

# 7. Análises Estatísticas

## 7.1 Descritiva

- média
- mediana
- std
- quartis
- skewness
- curtose

---

## 7.2 Probabilidades

Exemplos:

- P(gap+ | preclose alto)
- P(fill | gap grande)
- P(continuação | preclose extremo)

---

## 7.3 Agrupamentos

Por:

- gap bin
- direção
- preclose
- posição no range

---

## 7.4 Testes

- t-test
- Mann-Whitney
- Pearson
- Spearman

---

# 8. Visualizações

- histograma de gaps
- histograma de retornos
- boxplots
- curvas de fill
- heatmaps simples
- barras de probabilidade

(NÃO usar seaborn)

---

# 9. Estrutura do Notebook

1. Configuração
2. Importação
3. Limpeza
4. Base intraday
5. Base diária
6. Base gap
7. Base preclose
8. Targets e labels
9. Eventos
10. Estatística
11. Probabilidades
12. Testes
13. Gráficos
14. Exportação
15. Conclusões

---

# 10. Robustez

- evitar lookahead bias
- validar ordenação temporal
- tratar dados faltantes
- parametrizar tudo
- documentar premissas

---

# 11. Parâmetros Iniciais

- path do dataset
- nomes das colunas
- horário do pregão
- janela preclose
- bins de gap
- targets
- referências

---

# 12. Resultado Esperado

Gerar um `.ipynb` completo que:

- cria datasets derivados
- aplica fórmulas matemáticas
- permite análise estatística real
- organiza o estudo de forma profissional
- seja flexível para testes e exploração

---

# Instrução Final

Gerar o notebook completo, modular, comentado e matematicamente consistente para análise do mini índice.
