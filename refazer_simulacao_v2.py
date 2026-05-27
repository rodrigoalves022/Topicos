# -*- coding: utf-8 -*-
"""Reescreve celulas 18+ do notebook com simulacao v2 corrigida."""
import json

NB_PATH = "analise_gap_win.ipynb"

# ═══════════════════════════════════════════════════════════════
# CELULA 18: Markdown introducao
# ═══════════════════════════════════════════════════════════════
md_cell = {
    "cell_type": "markdown",
    "id": "sim_v2_intro",
    "metadata": {},
    "source": [
        "## 8. Simulador Operacional de Gap (v2)\n",
        "\n",
        "**Objetivo:** Responder \"Se eu entrei no minuto X e sai no minuto Y, qual foi o resultado?\"\n",
        "\n",
        "### Estrutura\n",
        "- Separado por **faixa de gap** (0-100, 100-200, 200-300, 300+ pts)\n",
        "- Testa **compra** e **venda** separadamente para cada tipo de gap\n",
        "- Modo **tempo puro** (sem stop) e modo **com risco** (stop + alvo)\n",
        "- Valores em **pontos** e em **R$** (mini indice = R$ 0,20 por ponto)\n",
        "\n",
        "### Como usar\n",
        "1. Execute a celula de **definicao de funcoes** (abaixo)\n",
        "2. Na celula seguinte, **edite os parametros** e execute para ver os resultados\n",
    ]
}

# ═══════════════════════════════════════════════════════════════
# CELULA 19: Definicao de funcoes (executar uma vez)
# ═══════════════════════════════════════════════════════════════
funcoes_src = r'''# ════════════════════════════════════════════════════════════════
# DEFINICAO DE FUNCOES DO SIMULADOR (execute esta celula primeiro)
# ════════════════════════════════════════════════════════════════
import warnings
warnings.filterwarnings('ignore')

VALOR_PONTO_MINI = 0.20  # R$ por ponto por minicontrato

def classificar_faixa_gap(gap_abs):
    """Classifica o gap em faixas de pontos."""
    g = abs(gap_abs)
    if g <= 100:
        return '0 a 100'
    elif g <= 200:
        return '100 a 200'
    elif g <= 300:
        return '200 a 300'
    else:
        return '300+'


def preparar_dados_simulacao(base_intraday_orig, base_gap_orig, gap_min, gap_max):
    """Prepara os dados intraday e gap para simulacao."""
    intra = base_intraday_orig.sort_values(['session_date', 'datetime']).copy()
    intra['minuto_sessao'] = intra.groupby('session_date').cumcount()
    intra['session_date'] = pd.to_datetime(intra['session_date'])

    gap = base_gap_orig.copy()
    if 'session_date' not in gap.columns:
        gap = gap.reset_index()
    gap['session_date'] = pd.to_datetime(gap['session_date'])
    gap = gap[gap['gap_abs'].abs() >= gap_min]
    gap = gap[gap['gap_abs'].abs() <= gap_max]
    gap['faixa_gap'] = gap['gap_abs'].apply(classificar_faixa_gap)

    intra_dict = {d: df for d, df in intra.groupby('session_date', sort=False)}
    gap_alta = gap[gap['gap_abs'] > 0].copy()
    gap_baixa = gap[gap['gap_abs'] < 0].copy()

    return intra_dict, gap_alta, gap_baixa


def simular_tempo_puro(gap_df, intra_dict, lado, entradas, saidas, custo):
    """Simula operacoes de tempo puro (sem stop/alvo)."""
    trades = []
    for _, lg in gap_df.iterrows():
        dd = intra_dict.get(pd.to_datetime(lg['session_date']))
        if dd is None or dd.empty:
            continue
        faixa = lg['faixa_gap']
        gap_pts = float(lg['gap_abs'])
        for m_in in entradas:
            ent = dd[dd['minuto_sessao'] >= m_in].head(1)
            if ent.empty:
                continue
            pe = float(ent.iloc[0]['open'])
            for m_out in saidas:
                if m_out <= m_in:
                    continue
                janela = dd[(dd['minuto_sessao'] >= m_in) & (dd['minuto_sessao'] <= m_out)]
                if janela.empty:
                    continue
                ps = float(janela.iloc[-1]['close'])
                pnl = (ps - pe) if lado == 'compra' else (pe - ps)
                pnl_liq = pnl - custo
                trades.append({
                    'faixa_gap': faixa,
                    'gap_pts': gap_pts,
                    'lado': lado,
                    'entrada_min': m_in,
                    'saida_min': m_out,
                    'preco_entrada': pe,
                    'preco_saida': ps,
                    'pnl_bruto': pnl,
                    'pnl_liquido': pnl_liq,
                })
    return pd.DataFrame(trades)


def simular_com_risco(gap_df, intra_dict, lado, entradas, saidas, stops, alvos, custo):
    """Simula operacoes com stop (% do gap) e alvo (multiplo de R)."""
    trades = []
    for _, lg in gap_df.iterrows():
        dd = intra_dict.get(pd.to_datetime(lg['session_date']))
        if dd is None or dd.empty:
            continue
        faixa = lg['faixa_gap']
        gap_pts = float(lg['gap_abs'])
        for m_in in entradas:
            ent = dd[dd['minuto_sessao'] >= m_in].head(1)
            if ent.empty:
                continue
            pe = float(ent.iloc[0]['open'])
            for m_out in saidas:
                if m_out <= m_in:
                    continue
                janela = dd[(dd['minuto_sessao'] >= m_in) & (dd['minuto_sessao'] <= m_out)]
                if janela.empty:
                    continue
                for stop_pct in stops:
                    risco = abs(gap_pts) * stop_pct
                    if risco <= 0:
                        continue
                    for alvo_rr in alvos:
                        if lado == 'compra':
                            p_stop = pe - risco
                            p_alvo = pe + risco * alvo_rr
                        else:
                            p_stop = pe + risco
                            p_alvo = pe - risco * alvo_rr

                        ps = float(janela.iloc[-1]['close'])
                        motivo = 'tempo'
                        for _, b in janela.iterrows():
                            lo, hi = float(b['low']), float(b['high'])
                            if lado == 'compra':
                                bat_s = lo <= p_stop
                                bat_a = hi >= p_alvo
                            else:
                                bat_s = hi >= p_stop
                                bat_a = lo <= p_alvo
                            if bat_s and bat_a:
                                bat_s = abs(pe - p_stop) < abs(pe - p_alvo)
                                bat_a = not bat_s
                            if bat_s:
                                ps = p_stop
                                motivo = 'stop'
                                break
                            if bat_a:
                                ps = p_alvo
                                motivo = 'alvo'
                                break

                        pnl = (ps - pe) if lado == 'compra' else (pe - ps)
                        pnl_liq = pnl - custo
                        trades.append({
                            'faixa_gap': faixa,
                            'gap_pts': gap_pts,
                            'lado': lado,
                            'entrada_min': m_in,
                            'saida_min': m_out,
                            'stop_pct': stop_pct,
                            'alvo_rr': alvo_rr,
                            'risco_pts': risco,
                            'motivo_saida': motivo,
                            'preco_entrada': pe,
                            'preco_saida': ps,
                            'pnl_bruto': pnl,
                            'pnl_liquido': pnl_liq,
                        })
    return pd.DataFrame(trades)


def calcular_metricas(df, n_contratos=1):
    """Calcula metricas de um grupo de trades."""
    if df.empty:
        return pd.Series(dtype=float)
    n = len(df)
    ganhos = df.loc[df['pnl_liquido'] > 0, 'pnl_liquido'].sum()
    perdas = df.loc[df['pnl_liquido'] < 0, 'pnl_liquido'].abs().sum()
    pnl_total = df['pnl_liquido'].sum()
    return pd.Series({
        'Trades': int(n),
        'Acerto (%)': round((df['pnl_liquido'] > 0).mean() * 100, 1),
        'Media (pts)': round(df['pnl_liquido'].mean(), 1),
        'Mediana (pts)': round(df['pnl_liquido'].median(), 1),
        'Total (pts)': round(pnl_total, 1),
        'Desvio (pts)': round(df['pnl_liquido'].std(), 1),
        'Ganhos (pts)': round(ganhos, 1),
        'Perdas (pts)': round(perdas, 1),
        'Fator Lucro': round(ganhos / perdas, 3) if perdas > 0 else np.inf,
        'Expect/Trade (pts)': round(df['pnl_liquido'].mean(), 1),
        'Total (R$)': round(pnl_total * VALOR_PONTO_MINI * n_contratos, 2),
        'Media (R$)': round(df['pnl_liquido'].mean() * VALOR_PONTO_MINI * n_contratos, 2),
    })


def gerar_tabela_resumo(df_trades, grupo_cols, n_contratos=1):
    """Gera tabela de resumo agrupada."""
    if df_trades.empty:
        return pd.DataFrame()
    resumo = df_trades.groupby(grupo_cols).apply(
        lambda x: calcular_metricas(x, n_contratos), include_groups=False
    ).reset_index()
    return resumo.sort_values('Total (pts)', ascending=False).reset_index(drop=True)


def plot_matriz_heatmap(resumo, tipo_gap, lado, valor_col, titulo_extra='', fmt='{:.0f}', cmap='RdYlGn'):
    """Plota heatmap de entrada x saida."""
    sub = resumo[(resumo.get('tipo_gap', resumo.columns[0]) if 'tipo_gap' in resumo.columns else True.__class__) != None]
    if 'tipo_gap' in resumo.columns:
        sub = resumo[(resumo['tipo_gap'] == tipo_gap) & (resumo['lado'] == lado)]
    else:
        sub = resumo[resumo['lado'] == lado]

    if sub.empty:
        return

    pivot = sub.pivot_table(
        index='entrada_min', columns='saida_min',
        values=valor_col, aggfunc='first'
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(pivot.values, cmap=cmap, aspect='auto')

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=11)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=11)
    ax.set_xlabel('Minuto Saida', fontsize=12)
    ax.set_ylabel('Minuto Entrada', fontsize=12)
    ax.set_title(f'{tipo_gap} | {lado.upper()} | {valor_col} {titulo_extra}', fontsize=13, fontweight='bold')

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > (pivot.values[~np.isnan(pivot.values)].max() * 0.6) else 'black'
                ax.text(j, i, fmt.format(val), ha='center', va='center', fontsize=10, color=color, fontweight='bold')

    plt.colorbar(im, ax=ax, shrink=0.8)
    plt.tight_layout()
    plt.show()


def plot_barras_por_faixa(resumo, valor_col, titulo):
    """Grafico de barras agrupado por faixa de gap."""
    if resumo.empty or 'faixa_gap' not in resumo.columns:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    faixas = sorted(resumo['faixa_gap'].unique())
    lados = resumo['lado'].unique()
    x = np.arange(len(faixas))
    largura = 0.35

    for i, lado in enumerate(lados):
        vals = []
        for f in faixas:
            sub = resumo[(resumo['faixa_gap'] == f) & (resumo['lado'] == lado)]
            vals.append(sub[valor_col].values[0] if not sub.empty else 0)
        cores = ['#2ecc71' if v >= 0 else '#e74c3c' for v in vals]
        bars = ax.bar(x + i * largura, vals, largura, label=lado.upper(), color=cores, edgecolor='white', alpha=0.85)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    f'{val:.0f}', ha='center', va='bottom' if val >= 0 else 'top', fontsize=9, fontweight='bold')

    ax.set_xticks(x + largura/2)
    ax.set_xticklabels(faixas, fontsize=11)
    ax.set_xlabel('Faixa do Gap (pontos)', fontsize=12)
    ax.set_ylabel(valor_col, fontsize=12)
    ax.set_title(titulo, fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.axhline(y=0, color='gray', linewidth=0.8)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_evolucao_acumulada(df_trades, tipo_gap, lado, entrada, saida, n_contratos=1):
    """Grafico de curva de capital acumulada (equity curve)."""
    sub = df_trades[
        (df_trades['lado'] == lado) &
        (df_trades['entrada_min'] == entrada) &
        (df_trades['saida_min'] == saida)
    ].copy()
    if sub.empty:
        print(f'  Sem trades para {tipo_gap} | {lado} | E{entrada} S{saida}')
        return

    sub = sub.sort_index()
    sub['acumulado_pts'] = sub['pnl_liquido'].cumsum()
    sub['acumulado_rs'] = sub['acumulado_pts'] * VALOR_PONTO_MINI * n_contratos
    sub['trade_num'] = range(1, len(sub)+1)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    cor = '#2ecc71' if sub['acumulado_pts'].iloc[-1] >= 0 else '#e74c3c'

    ax1.fill_between(sub['trade_num'], sub['acumulado_pts'], alpha=0.3, color=cor)
    ax1.plot(sub['trade_num'], sub['acumulado_pts'], color=cor, linewidth=2)
    ax1.set_title(f'{tipo_gap} | {lado.upper()} | E{entrada} S{saida} - Acumulado (pts)', fontweight='bold')
    ax1.set_xlabel('Numero do Trade')
    ax1.set_ylabel('Pontos Acumulados')
    ax1.axhline(y=0, color='gray', linewidth=0.8)
    ax1.grid(alpha=0.3)

    ax2.fill_between(sub['trade_num'], sub['acumulado_rs'], alpha=0.3, color=cor)
    ax2.plot(sub['trade_num'], sub['acumulado_rs'], color=cor, linewidth=2)
    ax2.set_title(f'{tipo_gap} | {lado.upper()} | E{entrada} S{saida} - Acumulado (R$)', fontweight='bold')
    ax2.set_xlabel('Numero do Trade')
    ax2.set_ylabel(f'R$ ({n_contratos} contrato(s))')
    ax2.axhline(y=0, color='gray', linewidth=0.8)
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()

    acerto = (sub['pnl_liquido'] > 0).mean() * 100
    print(f'  {len(sub)} trades | Acerto: {acerto:.1f}% | Total: {sub["acumulado_pts"].iloc[-1]:.0f} pts'
          f' = R$ {sub["acumulado_rs"].iloc[-1]:.2f}')


print('Funcoes do simulador carregadas com sucesso!')
print(f'Valor por ponto (mini indice): R$ {VALOR_PONTO_MINI:.2f}')
'''

funcoes_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": "sim_v2_funcoes",
    "metadata": {},
    "outputs": [],
    "source": [line + "\n" for line in funcoes_src.strip().split('\n')]
}
funcoes_cell["source"][-1] = funcoes_cell["source"][-1].rstrip("\n")

# ═══════════════════════════════════════════════════════════════
# CELULA 20: Execucao com parametros editaveis
# ═══════════════════════════════════════════════════════════════
exec_src = r'''# ════════════════════════════════════════════════════════════════
# PARAMETROS EDITAVEIS - altere e reexecute esta celula
# ════════════════════════════════════════════════════════════════

ENTRADAS = [1, 2, 3, 5, 10]          # minutos apos abertura
SAIDAS = [5, 10, 15, 20, 30]         # minutos apos abertura
CUSTO_POR_TRADE = 0.0                # custo round trip em pontos
GAP_MINIMO = 0                       # filtro: gap minimo em pontos
GAP_MAXIMO = 999999                  # filtro: gap maximo em pontos
N_CONTRATOS = 1                      # quantidade de minicontratos
STOPS_PCT = [0.2, 0.3, 0.5]          # stop em % do gap (20%, 30%, 50%)
ALVOS_RR = [1.0, 1.5, 2.0, 3.0]     # alvo em multiplos de R

# ════════════════════════════════════════════════════════════════
# EXECUCAO (nao precisa alterar abaixo)
# ════════════════════════════════════════════════════════════════

intra_dict, gap_alta, gap_baixa = preparar_dados_simulacao(
    base_intraday, base_gap, GAP_MINIMO, GAP_MAXIMO
)

print(f'Dias com Gap de Alta: {len(gap_alta)}')
print(f'Dias com Gap de Baixa: {len(gap_baixa)}')
print(f'Custo por trade: {CUSTO_POR_TRADE} pts')
print(f'Contratos: {N_CONTRATOS} | Valor ponto: R$ {VALOR_PONTO_MINI}')
print(f'Filtro gap: {GAP_MINIMO} a {GAP_MAXIMO} pts')

# ── MODO TEMPO PURO ───────────────────────────────────────────
print('\n' + '='*70)
print('MODO TEMPO PURO (entra em X, sai em Y, sem stop/alvo)')
print('='*70)

todos_tp = []
for label, gdf in [('Gap de Alta', gap_alta), ('Gap de Baixa', gap_baixa)]:
    for lado in ['compra', 'venda']:
        df_t = simular_tempo_puro(gdf, intra_dict, lado, ENTRADAS, SAIDAS, CUSTO_POR_TRADE)
        if not df_t.empty:
            df_t['tipo_gap'] = label
            todos_tp.append(df_t)

if todos_tp:
    trades_tp = pd.concat(todos_tp, ignore_index=True)
else:
    trades_tp = pd.DataFrame()

# ── Resumo GERAL (todos os gaps juntos) ───────────────────────
resumo_geral = gerar_tabela_resumo(trades_tp, ['tipo_gap', 'lado', 'entrada_min', 'saida_min'], N_CONTRATOS)

# ── Resumo POR FAIXA de gap ──────────────────────────────────
resumo_faixa = gerar_tabela_resumo(trades_tp, ['tipo_gap', 'faixa_gap', 'lado', 'entrada_min', 'saida_min'], N_CONTRATOS)

# ═══════════════════════════════════════════════════
# TABELAS - GAP DE ALTA
# ═══════════════════════════════════════════════════
print('\n' + '='*70)
print('GAP DE ALTA - TOP 10 CENARIOS (TEMPO PURO)')
print('='*70)
top_alta = resumo_geral[resumo_geral['tipo_gap'] == 'Gap de Alta'].head(10)
display(top_alta)

# ── Matrizes heatmap - Gap de Alta ────────────────────────────
for lado in ['compra', 'venda']:
    plot_matriz_heatmap(resumo_geral, 'Gap de Alta', lado, 'Total (pts)', '', '{:.0f}')
    plot_matriz_heatmap(resumo_geral, 'Gap de Alta', lado, 'Acerto (%)', '', '{:.1f}%')

# ═══════════════════════════════════════════════════
# TABELAS - GAP DE BAIXA
# ═══════════════════════════════════════════════════
print('\n' + '='*70)
print('GAP DE BAIXA - TOP 10 CENARIOS (TEMPO PURO)')
print('='*70)
top_baixa = resumo_geral[resumo_geral['tipo_gap'] == 'Gap de Baixa'].head(10)
display(top_baixa)

for lado in ['compra', 'venda']:
    plot_matriz_heatmap(resumo_geral, 'Gap de Baixa', lado, 'Total (pts)', '', '{:.0f}')
    plot_matriz_heatmap(resumo_geral, 'Gap de Baixa', lado, 'Acerto (%)', '', '{:.1f}%')

# ═══════════════════════════════════════════════════
# TABELAS POR FAIXA DE GAP
# ═══════════════════════════════════════════════════
print('\n' + '='*70)
print('RESULTADO POR FAIXA DE GAP (melhor cenario por faixa)')
print('='*70)

for tipo in ['Gap de Alta', 'Gap de Baixa']:
    print(f'\n── {tipo} ──')
    sub_faixa = resumo_faixa[resumo_faixa['tipo_gap'] == tipo]
    if sub_faixa.empty:
        print('  Sem dados')
        continue
    # Melhor cenario por faixa
    melhor = sub_faixa.loc[sub_faixa.groupby('faixa_gap')['Total (pts)'].idxmax()]
    display(melhor[['faixa_gap', 'lado', 'entrada_min', 'saida_min',
                    'Trades', 'Acerto (%)', 'Total (pts)', 'Total (R$)',
                    'Fator Lucro', 'Media (pts)']].reset_index(drop=True))

# ── Grafico de barras por faixa ───────────────────────────────
for tipo in ['Gap de Alta', 'Gap de Baixa']:
    # Pega melhor cenario (entrada/saida) por faixa e lado
    sub = resumo_faixa[resumo_faixa['tipo_gap'] == tipo]
    if sub.empty:
        continue
    melhor_por_fl = sub.loc[sub.groupby(['faixa_gap', 'lado'])['Total (pts)'].idxmax()]
    plot_barras_por_faixa(melhor_por_fl, 'Total (pts)', f'{tipo} - Melhor Resultado por Faixa de Gap')

# ═══════════════════════════════════════════════════
# EQUITY CURVES (curva de capital acumulada)
# ═══════════════════════════════════════════════════
print('\n' + '='*70)
print('EQUITY CURVES - MELHORES CENARIOS')
print('='*70)

for tipo, df_gap_trades in [('Gap de Alta', trades_tp[trades_tp['tipo_gap']=='Gap de Alta']),
                             ('Gap de Baixa', trades_tp[trades_tp['tipo_gap']=='Gap de Baixa'])]:
    if df_gap_trades.empty:
        continue
    # Pega o melhor cenario
    melhor_row = resumo_geral[resumo_geral['tipo_gap'] == tipo].head(1)
    if melhor_row.empty:
        continue
    mr = melhor_row.iloc[0]
    print(f'\n{tipo} - Melhor: {mr["lado"].upper()} E{int(mr["entrada_min"])} S{int(mr["saida_min"])}')
    plot_evolucao_acumulada(df_gap_trades, tipo, mr['lado'],
                           int(mr['entrada_min']), int(mr['saida_min']), N_CONTRATOS)

# ═══════════════════════════════════════════════════
# MODO COM RISCO (stop + alvo)
# ═══════════════════════════════════════════════════
print('\n' + '='*70)
print('MODO COM RISCO (stop em % do gap + alvo em R)')
print('='*70)

todos_risco = []
for label, gdf in [('Gap de Alta', gap_alta), ('Gap de Baixa', gap_baixa)]:
    for lado in ['compra', 'venda']:
        df_r = simular_com_risco(gdf, intra_dict, lado, ENTRADAS, SAIDAS,
                                 STOPS_PCT, ALVOS_RR, CUSTO_POR_TRADE)
        if not df_r.empty:
            df_r['tipo_gap'] = label
            todos_risco.append(df_r)

if todos_risco:
    trades_risco = pd.concat(todos_risco, ignore_index=True)
    resumo_risco = gerar_tabela_resumo(
        trades_risco,
        ['tipo_gap', 'lado', 'entrada_min', 'saida_min', 'stop_pct', 'alvo_rr'],
        N_CONTRATOS
    )
    resumo_risco['stop_pct'] = (resumo_risco['stop_pct'] * 100).astype(int).astype(str) + '%'
    resumo_risco['alvo_rr'] = resumo_risco['alvo_rr'].apply(lambda x: f'{x:.1f}R')

    for tipo in ['Gap de Alta', 'Gap de Baixa']:
        print(f'\n── TOP 10 COM RISCO - {tipo.upper()} ──')
        top_r = resumo_risco[resumo_risco['tipo_gap'] == tipo].head(10)
        display(top_r)
else:
    trades_risco = pd.DataFrame()
    resumo_risco = pd.DataFrame()

# ═══════════════════════════════════════════════════
# DIAGNOSTICO
# ═══════════════════════════════════════════════════
print('\n' + '='*70)
print('DIAGNOSTICO - 10 PIORES CENARIOS (TEMPO PURO)')
print('='*70)
piores = resumo_geral.sort_values('Total (pts)', ascending=True).head(10).copy()

def diagnosticar(row):
    motivos = []
    if row['Acerto (%)'] < 45:
        motivos.append('taxa de acerto baixa')
    if row.get('Fator Lucro', 1) < 0.8:
        motivos.append('fator de lucro fraco')
    if row['Media (pts)'] < -50:
        motivos.append('prejuizo medio alto')
    saida = int(row['saida_min'])
    entrada = int(row['entrada_min'])
    if saida - entrada <= 3:
        motivos.append('janela muito curta')
    return '; '.join(motivos) if motivos else 'distribuicao desfavoravel'

piores['Motivo'] = piores.apply(diagnosticar, axis=1)
display(piores)

# ═══════════════════════════════════════════════════
# INTERPRETACAO FINAL
# ═══════════════════════════════════════════════════
print('\n' + '='*70)
print('RESUMO: ONDE ENTRAR E ONDE SAIR?')
print('='*70)

for tipo in ['Gap de Alta', 'Gap de Baixa']:
    print(f'\n{tipo}:')
    for lado in ['compra', 'venda']:
        sub = resumo_geral[(resumo_geral['tipo_gap'] == tipo) & (resumo_geral['lado'] == lado)]
        if sub.empty:
            continue
        best = sub.iloc[0]
        print(f'  {lado.upper():7s}: E{int(best["entrada_min"])} S{int(best["saida_min"])} '
              f'-> {best["Total (pts)"]:.0f} pts (R$ {best["Total (R$)"]:.2f}) | '
              f'Acerto: {best["Acerto (%)"]:.1f}% | Fator Lucro: {best["Fator Lucro"]:.2f} | '
              f'{int(best["Trades"])} trades')

# ═══════════════════════════════════════════════════
# EXPORTAR CSVs
# ═══════════════════════════════════════════════════
resumo_geral.to_csv(PASTA_SAIDA / 'simulador_tempo_puro_resumo.csv', index=False, encoding='utf-8-sig')
resumo_faixa.to_csv(PASTA_SAIDA / 'simulador_tempo_puro_por_faixa.csv', index=False, encoding='utf-8-sig')
if not resumo_risco.empty:
    resumo_risco.to_csv(PASTA_SAIDA / 'simulador_com_risco_resumo.csv', index=False, encoding='utf-8-sig')
piores.to_csv(PASTA_SAIDA / 'simulador_diagnostico_piores.csv', index=False, encoding='utf-8-sig')
print(f'\nCSVs exportados em: {PASTA_SAIDA.resolve()}')
'''

exec_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": "sim_v2_execucao",
    "metadata": {},
    "outputs": [],
    "source": [line + "\n" for line in exec_src.strip().split('\n')]
}
exec_cell["source"][-1] = exec_cell["source"][-1].rstrip("\n")

# ═══════════════════════════════════════════════════════════════
# Aplica no notebook
# ═══════════════════════════════════════════════════════════════
with open(NB_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Substitui celulas 18+ por 3 novas celulas
nb["cells"] = nb["cells"][:18] + [md_cell, funcoes_cell, exec_cell]

with open(NB_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook reescrito! Total de celulas: {len(nb['cells'])}")
print("Celula 18: Markdown intro")
print("Celula 19: Funcoes (executar primeiro)")
print("Celula 20: Parametros + execucao (editavel)")
