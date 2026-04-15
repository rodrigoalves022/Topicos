# Guia de Estudo dos Resultados

Este arquivo resume o que o notebook `analise_gap_win.ipynb` gerou, como ler cada base exportada e quais foram os principais achados do estudo.

O foco aqui é prático: entender o comportamento do gap no WIN para análise intraday, principalmente nas janelas de 5, 10, 20 e 30 minutos após a abertura.

## 1. Objetivo do estudo

O notebook foi montado para responder perguntas como:

- o tamanho do gap influencia a chance de fechamento rápido?
- o contexto do dia anterior ajuda a entender o que acontece na abertura?
- os últimos 15 minutos do pregão anterior ajudam a prever rejeição ou aceitação do gap?
- existe sinal útil para machine learning ou os resultados ainda estão fracos?

## 2. Ideia central do gap

No estudo:

- `gap` é a diferença entre a abertura de hoje e o fechamento do dia anterior;
- `fill` é quando o preço volta ao nível do fechamento do dia anterior;
- como o foco é day trade, o principal não é "fechou em algum momento do dia", mas sim:
  - fechou até 5 minutos;
  - fechou até 10 minutos;
  - fechou até 20 minutos;
  - fechou até 30 minutos.

## 3. Fórmulas principais

### Gap

`gap_em_pontos = abertura_de_hoje - fechamento_de_ontem`

`gap_percentual = (abertura_de_hoje - fechamento_de_ontem) / fechamento_de_ontem`

`gap_normalizado_pelo_atr = gap_em_pontos / atr_14`

Leitura:

- gap positivo: abertura acima do fechamento anterior;
- gap negativo: abertura abaixo do fechamento anterior.

### Fill

Para gap positivo:

- houve fill se a mínima tocar o fechamento anterior.

Para gap negativo:

- houve fill se a máxima tocar o fechamento anterior.

Fill temporal:

- `fill_ate_5m = 1` se o fill aconteceu até 5 minutos após a abertura;
- `fill_ate_10m = 1` se o fill aconteceu até 10 minutos após a abertura;
- `fill_ate_20m = 1` se o fill aconteceu até 20 minutos após a abertura;
- `fill_ate_30m = 1` se o fill aconteceu até 30 minutos após a abertura.

### Retornos

`retorno_abertura_ate_fechamento = fechamento_do_dia / abertura_do_dia - 1`

`retorno_5m_desde_abertura = fechamento_5m / abertura - 1`

`retorno_15m_desde_abertura = fechamento_15m / abertura - 1`

`retorno_30m_desde_abertura = fechamento_30m / abertura - 1`

### ATR

`true_range = max( maxima_do_dia - minima_do_dia ; |maxima_do_dia - fechamento_anterior| ; |minima_do_dia - fechamento_anterior| )`

`atr_14 = média móvel de 14 períodos do true_range`

## 4. Bases geradas e como ler

### `intraday_limpo.csv`

Base minuto a minuto já tratada.

Colunas principais:

- `date`, `time`: data e hora originais;
- `open`, `high`, `low`, `close`: OHLC de 1 minuto;
- `tick_volume`, `volume`, `spread`;
- `datetime`: data e hora completas;
- `session_date`: dia do pregão;
- `clock_time`: horário da barra;
- `minute`: minuto do dia em formato numérico.

Uso:

- é a matéria-prima de todo o estudo.

### `base_diaria.csv`

Cada linha representa um pregão.

Colunas principais:

- `open`, `high`, `low`, `close`;
- `tick_volume`, `volume`;
- `spread_mean`;
- `first_bar`, `last_bar`, `n_bars`;
- `range`: amplitude do dia;
- `return_close_to_close`;
- `return_open_to_close`;
- `prev_close`, `prev_high`, `prev_low`, `prev_range`;
- `tr`, `atr_14`;
- `day_direction`.

Uso:

- resume o comportamento diário;
- fornece o contexto do dia anterior para o estudo do gap.

### `agenda_diaria.csv`

Mostra a estrutura temporal de cada dia.

Colunas principais:

- `session_date`;
- `primeira_barra`, `ultima_barra`;
- `quantidade_barras`;
- `horario_abertura`, `horario_fechamento`.

Uso:

- validar se o número de barras e os horários estão consistentes ao longo da amostra.

### `base_preclose.csv`

Resume os últimos 15 minutos do pregão anterior.

Colunas principais:

- início da janela de pré-close (`preclose_start`);
- fim da janela de pré-close (`preclose_end`);
- abertura da janela (`preclose_open`);
- fechamento da janela (`preclose_close`);
- máxima da janela (`preclose_high`);
- mínima da janela (`preclose_low`);
- volume negociado na janela (`preclose_volume`);
- volume em ticks da janela (`preclose_tick_volume`);
- quantidade de barras usadas na janela (`preclose_bars_used`);
- retorno da janela de pré-close (`preclose_return`);
- amplitude da janela (`preclose_range`);
- amplitude percentual da janela (`preclose_range_pct`);
- volatilidade interna da janela (`preclose_volatility`);
- retorno do último minuto da janela (`preclose_last_min_return`);
- inclinação da janela em pontos por minuto (`preclose_slope_points_per_min`);
- posição do fechamento da janela dentro do range do dia (`preclose_close_position_day`);
- posição do fechamento dentro do range da própria janela (`preclose_close_position_window`);
- retorno do dia anterior inteiro (`preclose_day_return`);
- amplitude do dia anterior inteiro (`preclose_day_range`).

Uso:

- captar se o fechamento do dia anterior terminou forte, fraco, acelerando, exausto ou equilibrado.

### `base_gap.csv`

É a base principal do estudo.

Cada linha representa um dia comparado com o fechamento do dia anterior.

Colunas mais importantes:

- gap em pontos (`gap_abs`);
- gap em percentual (`gap_pct`);
- gap dividido pelo ATR (`gap_atr`);
- direção do gap (`gap_direction`): `positive`, `negative` ou `flat`;
- lado necessário para fechar o gap (`gap_side_to_fill`);
- fill em qualquer momento do dia (`gap_fill_no_dia`);
- minutos até o fill no dia inteiro (`time_to_fill_no_dia_min`);
- indicadores de fill até 5, 10, 20 e 30 minutos (`fill_ate_5m`, `fill_ate_10m`, `fill_ate_20m`, `fill_ate_30m`);
- minutos até o fill em cada janela (`tempo_fill_ate_5m`, `tempo_fill_ate_10m`, `tempo_fill_ate_20m`, `tempo_fill_ate_30m`);
- retorno da abertura até o fechamento (`close_vs_open_ret`);
- retorno do fechamento atual contra o fechamento anterior (`close_vs_prev_close_ret`);
- indicador de dia de alta e dia de baixa (`day_green`, `day_red`);
- excursão favorável e adversa para compra desde a abertura (`mfe_buy_from_open`, `mae_buy_from_open`);
- excursão favorável e adversa para venda desde a abertura (`mfe_sell_from_open`, `mae_sell_from_open`);
- retorno acumulado após 5, 15 e 30 minutos desde a abertura (`ret_5m_from_open`, `ret_15m_from_open`, `ret_30m_from_open`);
- indicadores de fill parcial em 30%, 50%, 70% e 100% (`fill_30pct`, `fill_50pct`, `fill_70pct`, `fill_100pct`);
- faixa do gap com sinal e faixa do gap em módulo (`gap_bin`, `abs_gap_bin`).

Uso:

- estudar o gap diretamente;
- medir fechamento rápido;
- medir continuação, reversão e excursão.

### `base_ml.csv`

Base preparada para machine learning.

Ela junta:

- variáveis do gap atual;
- variáveis do pré-close do dia anterior;
- variáveis da base diária do dia anterior;
- targets criados para previsão.

Targets principais:

- alvo de gap positivo (`target_gap_up`);
- alvo de fill até 5 minutos (`target_fill_5m`);
- alvo de fill até 10 minutos (`target_fill_10m`);
- alvo de fill até 20 minutos (`target_fill_20m`);
- alvo de fill até 30 minutos (`target_fill_30m`);
- alvo de fechamento acima da abertura (`target_day_green`);
- alvo de continuação na direção do gap (`target_continuation`).

Uso:

- testar se existe poder preditivo nas variáveis disponíveis até o fechamento de `t-1`.

### `resumo_gap_por_faixa.csv`

Resume o comportamento do gap por tamanho.

Colunas principais:

- direção do gap (`gap_direction`);
- faixa do gap em valor absoluto (`abs_gap_bin`);
- quantidade de ocorrências (`n`);
- taxa de fill até 5 minutos (`taxa_fill_5m`);
- taxa de fill até 10 minutos (`taxa_fill_10m`);
- taxa de fill até 20 minutos (`taxa_fill_20m`);
- taxa de fill até 30 minutos (`taxa_fill_30m`);
- taxa de fill no dia inteiro (`taxa_fill_no_dia`);
- média do gap na faixa (`avg_gap`);
- mediana do gap na faixa (`median_gap`).

Uso:

- descobrir em quais faixas o fill rápido é realmente frequente.

### `eventos_gap_alvos.csv`

Base operacional para alvos parciais.

Colunas principais:

- percentual usado no alvo parcial (`alpha`);
- referência usada para a entrada (`entry_reference`);
- preço de referência da operação (`reference_price`);
- preço efetivo de entrada considerado (`entry_price`);
- nível de preço do alvo (`target_level`);
- indicador de alvo atingido no dia (`hit_target_no_dia`);
- minutos até o alvo ser atingido no dia (`time_to_target_no_dia_min`);
- lado da operação para buscar o fechamento do gap (`trade_side_to_fill`);
- indicadores de fill até 5, 10, 20 e 30 minutos (`fill_ate_5m`, `fill_ate_10m`, `fill_ate_20m`, `fill_ate_30m`).

Uso:

- estudar setups com alvo parcial, em vez de exigir fill total sempre.

### `tabela_estatisticas.csv`

Resumo estatístico das colunas principais.

Linhas:

- `count`, `mean`, `median`, `std`, `q25`, `q75`, `skew`, `kurtosis`, `min`, `max`.

Uso:

- entender dispersão, assimetria e presença de extremos.

## 5. Resultado geral da amostra

A amostra final analisada tem:

- `602` pregões com gap analisável.

Principais números:

- `fill_ate_5m`: `24,92%`;
- `fill_ate_10m`: `28,57%`;
- `fill_ate_20m`: `32,23%`;
- `fill_ate_30m`: `35,05%`;
- `fill no dia inteiro`: `416 / 602 = 69,10%`.

Leitura:

- o gap costuma fechar ao longo do dia com frequência razoável;
- mas fill rápido é bem menos comum;
- então usar "fill no dia" como regra de day trade seria otimista demais.

Tempo até o fill no dia inteiro:

- média: `76,0` minutos;
- mediana: `30,0` minutos.

Leitura:

- quando o fill acontece, muitas vezes ele acontece cedo;
- mas há também vários casos demorados, puxando a média para cima.

## 6. Principal achado: tamanho do gap importa muito

O arquivo `resumo_gap_por_faixa.csv` mostra o sinal mais forte do estudo.

### Gaps pequenos

Gap positivo entre `0 e 50` pontos:

- fill até 30m: `93,33%`.

Gap negativo entre `0 e 50` pontos:

- fill até 30m: `92,31%`.

Gap positivo entre `50 e 100` pontos:

- fill até 30m: `86,67%`.

Gap negativo entre `50 e 100` pontos:

- fill até 30m: `85,71%`.

Leitura:

- gaps pequenos têm comportamento fortíssimo de fechamento rápido;
- esse é o sinal mais consistente do estudo.

### Gaps médios

Gap positivo entre `100 e 150` pontos:

- fill até 30m: `78,95%`.

Gap negativo entre `100 e 150` pontos:

- fill até 30m: `73,33%`.

Gap positivo entre `150 e 200` pontos:

- fill até 30m: `57,69%`.

Gap negativo entre `150 e 200` pontos:

- fill até 30m: `55,00%`.

Leitura:

- ainda existe chance relevante de fill;
- mas o sinal já fica menos forte;
- acima de 150 pontos o comportamento muda bastante.

### Gaps grandes

Gap positivo acima de `200` pontos:

- fill até 5m: `12,90%`;
- fill até 10m: `16,53%`;
- fill até 20m: `20,97%`;
- fill até 30m: `24,19%`;
- fill no dia inteiro: `58,06%`.

Gap negativo acima de `200` pontos:

- fill até 5m: `9,80%`;
- fill até 10m: `12,75%`;
- fill até 20m: `16,18%`;
- fill até 30m: `17,65%`;
- fill no dia inteiro: `62,75%`.

Leitura:

- gaps grandes raramente fecham rápido;
- mesmo quando fecham no dia, isso muitas vezes demora demais para um setup de abertura;
- para day trade, tratar gap grande como "provável fill imediato" é uma má leitura.

## 7. Leitura por tipo de gap normalizado

O arquivo `resumo_tipo_gap.csv` reforça essa ideia.

### Gaps pequenos normalizados pelo ATR

- `gap_up_small`: taxa de fechamento do gap `82,13%`, fill até 30m `55,07%`;
- `gap_down_small`: taxa de fechamento do gap `83,52%`, fill até 30m `48,30%`.

### Gaps médios

- `gap_up_medium`: taxa de fechamento do gap `41,94%`, fill até 30m `0,00%`;
- `gap_down_medium`: taxa de fechamento do gap `53,95%`, fill até 30m `1,32%`.

### Gaps grandes

- `gap_up_large`: taxa de fechamento do gap `12,50%`, fill até 30m `0,00%`;
- `gap_down_large`: taxa de fechamento do gap `12,50%`, fill até 30m `0,00%`.

Leitura:

- quando o gap cresce muito em relação ao ATR, o comportamento muda de regime;
- o mercado deixa de se comportar como simples "volta ao fechamento anterior";
- nesses casos, continuação e deslocamento tendem a ganhar importância.

## 8. Resultado dos 15 minutos iniciais

O arquivo `resumo_gap_opening15.csv` é um dos mais úteis para leitura operacional.

Ele separa os casos em:

- `aceitou`: os primeiros 15 minutos confirmaram o sentido do gap;
- `rejeitou`: os primeiros 15 minutos andaram contra o gap.

### Quando o gap foi aceito nos 15 minutos

`gap_up` com `aceitou`:

- taxa de fechamento até 30m: `13,73%`;
- taxa de fechamento até 60m: `20,26%`;
- média de `open_close`: `316,01`.

`gap_down` com `aceitou`:

- taxa de fechamento até 30m: `14,18%`;
- taxa de fechamento até 60m: `21,28%`;
- média de `open_close`: `-326,70`.

Leitura:

- se o mercado aceitou o gap logo no início, a chance de fill rápido caiu bastante;
- em média, o dia continuou na direção do gap.

### Quando o gap foi rejeitado nos 15 minutos

`gap_up` com `rejeitou`:

- taxa de fechamento até 30m: `56,47%`;
- taxa de fechamento até 60m: `62,94%`;
- média de `open_close`: `-293,26`.

`gap_down` com `rejeitou`:

- taxa de fechamento até 30m: `51,52%`;
- taxa de fechamento até 60m: `56,06%`;
- média de `open_close`: `255,91`.

Leitura:

- a rejeição inicial foi um sinal forte de reversão;
- isso parece muito mais útil operacionalmente do que olhar só o tamanho bruto do gap.

## 9. Resultado do contexto do dia anterior

O arquivo `resumo_gap_contexto_prevday.csv` cruza:

- direção do candle anterior;
- regime de range do dia anterior;
- posição do fechamento anterior dentro do range.

O sinal existe, mas é mais contextual do que dominante.

Exemplos:

- `gap_up` após dia anterior comprador, range baixo e fechamento perto da máxima:
  - fill até 30m: `52,94%`.
- `gap_up` após dia anterior vendedor, range alto e fechamento perto da mínima:
  - fill até 30m: `18,18%`.
- `gap_down` após dia anterior comprador, range baixo e fechamento perto da máxima:
  - fill até 30m: `45,95%`.
- `gap_down` após dia anterior comprador, range baixo e fechamento em meio de faixa:
  - fill até 30m: `17,65%`.

Leitura:

- o contexto do dia anterior ajuda a segmentar;
- mas sozinho ele não parece ser o melhor preditor;
- faz mais sentido usá-lo como filtro complementar.

## 10. Hipóteses operacionais testadas

O arquivo `resumo_hipoteses_gap.csv` traz dois testes de hipótese operacional.

### Hipótese A

`A_fade_gap_pequeno_dentro_faixa`

Resultado:

- `n = 0`.

Leitura:

- com as regras atuais, não houve casos suficientes;
- então essa hipótese não foi validada.

### Hipótese B

`B_cont_gap_grande_fora_faixa`

Resultado:

- `n = 12`;
- `win_rate = 66,67%`;
- `expectancy = 261,67`;
- `profit_factor = 2,37`;
- `max_drawdown = -1005`.

Leitura:

- é um resultado interessante, mas com amostra muito pequena;
- ainda não dá para tratar isso como evidência forte;
- serve mais como pista para aprofundar depois.

## 11. Como interpretar a parte de machine learning

Os resultados que você obteve na execução mostram que o ML ainda está fraco para uso prático.

### `target_gap_up`

- Accuracy: `0,5083`
- ROC AUC: `0,5704`

Leitura:

- a acurácia ficou perto de aleatório;
- o ROC AUC ficou só um pouco acima de `0,50`;
- existe algum sinal fraco, mas ainda insuficiente para confiar.

### `target_fill_5m`

- Accuracy: `0,7293`
- ROC AUC: `0,5130`

Leitura:

- a accuracy parece boa à primeira vista;
- mas o recall da classe `1` foi `0,0204`;
- isso significa que o modelo quase nunca identifica os fills de 5 minutos;
- na prática, ele está acertando muito porque prevê a classe dominante.

### `target_fill_10m`

- Accuracy: `0,6796`
- ROC AUC: `0,5113`

Leitura:

- mesmo problema do alvo de 5 minutos;
- a classe positiva quase não está sendo capturada.

### `target_fill_20m`

- Accuracy: `0,6298`
- ROC AUC: `0,5541`

Leitura:

- houve melhora pequena no ranqueamento;
- ainda assim o modelo segue fraco para separar bem os casos.

### `target_fill_30m`

- Accuracy: `0,5967`
- ROC AUC: `0,5464`

Leitura:

- continua abaixo do que seria desejável para um modelo operacional;
- ainda parece mais forte usar regra estatística e segmentação do que confiar no classificador.

## 12. Conclusão prática do estudo

Os sinais mais úteis encontrados até agora foram:

- gaps pequenos têm alta taxa de fill rápido;
- gaps grandes raramente fecham rápido;
- a reação dos primeiros 15 minutos é um filtro muito forte:
  - aceitou o gap, aumenta chance de continuação;
  - rejeitou o gap, aumenta chance de reversão e fill;
- o contexto do dia anterior ajuda, mas mais como filtro complementar;
- o machine learning ainda não encontrou vantagem suficiente.

## 13. O que parece válido estudar mais

- segmentar setups por tamanho do gap;
- usar os 15 primeiros minutos como filtro obrigatório;
- separar regras para gap pequeno, médio e grande;
- testar alvos parciais em vez de exigir fill total;
- estudar stop, alvo e expectativa por faixa de gap;
- recalibrar o ML com menos targets e mais foco operacional.

## 14. Resumo curto

Se você quiser guardar a leitura mais importante em poucas linhas:

- o gap não deve ser analisado como um único fenômeno;
- o tamanho do gap muda completamente o comportamento do mercado;
- para day trade, o que importa é fill rápido, não fill "em qualquer momento do dia";
- os primeiros 15 minutos parecem mais úteis do que o classificador de machine learning;
- o melhor sinal atual está em regras estatísticas segmentadas, não em previsão automática.
