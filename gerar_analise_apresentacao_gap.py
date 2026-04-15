from pathlib import Path
import argparse

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


def minutos_entre(inicio, fim):
    if pd.isna(inicio) or pd.isna(fim):
        return np.nan
    return (fim - inicio).total_seconds() / 60.0


def classificar_faixa_modulo(gaps, passo=100):
    gaps_abs = pd.Series(gaps).abs().astype(float)
    topo = int(np.ceil(gaps_abs.max() / passo) * passo) if len(gaps_abs.dropna()) else passo
    topo = max(topo, passo)
    bins = np.arange(0, topo + passo, passo, dtype=float)
    bins = np.insert(bins, 0, -0.001)
    bins = np.unique(bins)
    return pd.cut(gaps_abs, bins=bins, include_lowest=True)


def primeiro_movimento_no_sentido_do_gap(dados_dia, direcao_gap, abertura, deslocamento_minimo=5):
    if direcao_gap == "positive":
        candidatos = dados_dia.loc[dados_dia["low"] <= abertura - deslocamento_minimo, "datetime"]
    elif direcao_gap == "negative":
        candidatos = dados_dia.loc[dados_dia["high"] >= abertura + deslocamento_minimo, "datetime"]
    else:
        return pd.NaT
    return candidatos.iloc[0] if not candidatos.empty else pd.NaT


def medir_picos(dados_dia, abertura, direcao_gap, prev_close, movimento_minimo_inicio_gap=5):
    dados_dia = dados_dia.sort_values("datetime").reset_index(drop=True)
    inicio = dados_dia["datetime"].iloc[0]

    idx_max = int(dados_dia["high"].idxmax())
    idx_min = int(dados_dia["low"].idxmin())

    horario_max = dados_dia.loc[idx_max, "datetime"]
    horario_min = dados_dia.loc[idx_min, "datetime"]
    preco_max = float(dados_dia.loc[idx_max, "high"])
    preco_min = float(dados_dia.loc[idx_min, "low"])

    tempo_max = minutos_entre(inicio, horario_max)
    tempo_min = minutos_entre(inicio, horario_min)
    duracao_picos = abs(tempo_max - tempo_min)

    amp_max = preco_max - abertura
    amp_min = abertura - preco_min

    if direcao_gap == "positive":
        pico_contra, tempo_contra = amp_min, tempo_min
        pico_favor, tempo_favor = amp_max, tempo_max
    elif direcao_gap == "negative":
        pico_contra, tempo_contra = amp_max, tempo_max
        pico_favor, tempo_favor = amp_min, tempo_min
    else:
        pico_contra, tempo_contra = max(amp_max, amp_min), min(tempo_max, tempo_min)
        pico_favor, tempo_favor = np.nan, np.nan

    horario_inicio_fechamento = primeiro_movimento_no_sentido_do_gap(
        dados_dia=dados_dia,
        direcao_gap=direcao_gap,
        abertura=abertura,
        deslocamento_minimo=movimento_minimo_inicio_gap,
    )

    return {
        "tempo_ate_pico_max_min": tempo_max,
        "tempo_ate_pico_min_min": tempo_min,
        "duracao_entre_picos_min": duracao_picos,
        "pico_contra_gap_pts": pico_contra,
        "tempo_pico_contra_gap_min": tempo_contra,
        "pico_favor_gap_pts": pico_favor,
        "tempo_pico_favor_gap_min": tempo_favor,
        "horario_inicio_fechamento_gap": horario_inicio_fechamento,
        "tempo_inicio_fechamento_gap_min": minutos_entre(inicio, horario_inicio_fechamento),
        "amplitude_ate_pico_max_pts": amp_max,
        "amplitude_ate_pico_min_pts": amp_min,
        "dist_pico_max_ao_prev_close_pts": preco_max - prev_close,
        "dist_pico_min_ao_prev_close_pts": preco_min - prev_close,
    }


def montar_tabela_direcao(base, direcao):
    bloco = base.loc[base["gap_direction"] == direcao].copy()

    tabela = (
        bloco.groupby("faixa_gap_modulo", dropna=False)
        .agg(
            ocorrencias=("gap_abs", "size"),
            gap_medio_modulo_pts=("gap_modulo_pts", "mean"),
            gap_mediano_modulo_pts=("gap_modulo_pts", "median"),
            fechamento_gap_5m_pct=("fechamento_gap_ate_5m", "mean"),
            fechamento_gap_10m_pct=("fechamento_gap_ate_10m", "mean"),
            fechamento_gap_20m_pct=("fechamento_gap_ate_20m", "mean"),
            fechamento_gap_30m_pct=("fechamento_gap_ate_30m", "mean"),
            fechamento_gap_60m_pct=("fechamento_gap_ate_60m", "mean"),
            fechamento_gap_no_dia_pct=("fechamento_gap_no_dia", "mean"),
            tempo_mediano_fechamento_gap_min=("time_to_fill_no_dia_min", "median"),
            tempo_medio_inicio_fechamento_gap_min=("tempo_inicio_fechamento_gap_min", "mean"),
            tempo_medio_pico_contra_gap_min=("tempo_pico_contra_gap_min", "mean"),
            pico_contra_gap_medio_pts=("pico_contra_gap_pts", "mean"),
            tempo_medio_pico_favor_gap_min=("tempo_pico_favor_gap_min", "mean"),
            pico_favor_gap_medio_pts=("pico_favor_gap_pts", "mean"),
            duracao_media_entre_picos_min=("duracao_entre_picos_min", "mean"),
            curtose_tempo_fechamento_gap=("time_to_fill_no_dia_min", lambda s: s.dropna().kurtosis()),
            curtose_gap_modulo_pts=("gap_modulo_pts", lambda s: s.dropna().kurtosis()),
            desvio_padrao_gap_modulo_pts=("gap_modulo_pts", "std"),
            assimetria_gap_modulo=("gap_modulo_pts", lambda s: s.dropna().skew()),
        )
        .reset_index()
        .rename(columns={"faixa_gap_modulo": "Faixa do Gap (Módulo pts)"})
    )

    colunas_pct = [
        "fechamento_gap_5m_pct",
        "fechamento_gap_10m_pct",
        "fechamento_gap_20m_pct",
        "fechamento_gap_30m_pct",
        "fechamento_gap_60m_pct",
        "fechamento_gap_no_dia_pct",
    ]
    tabela[colunas_pct] = (tabela[colunas_pct] * 100).round(2)

    renomear = {
        "ocorrencias": "Ocorrências",
        "gap_medio_modulo_pts": "Gap Médio (Módulo pts)",
        "gap_mediano_modulo_pts": "Gap Mediano (Módulo pts)",
        "fechamento_gap_5m_pct": "Fechamento Gap até 5m (%)",
        "fechamento_gap_10m_pct": "Fechamento Gap até 10m (%)",
        "fechamento_gap_20m_pct": "Fechamento Gap até 20m (%)",
        "fechamento_gap_30m_pct": "Fechamento Gap até 30m (%)",
        "fechamento_gap_60m_pct": "Fechamento Gap até 60m (%)",
        "fechamento_gap_no_dia_pct": "Fechamento Gap no Dia (%)",
        "tempo_mediano_fechamento_gap_min": "Tempo Mediano Fechamento Gap (min)",
        "tempo_medio_inicio_fechamento_gap_min": "Tempo Médio Início Fechamento (min)",
        "tempo_medio_pico_contra_gap_min": "Tempo Médio Pico Contra (min)",
        "pico_contra_gap_medio_pts": "Pico Contra Médio (pts)",
        "tempo_medio_pico_favor_gap_min": "Tempo Médio Pico Favor (min)",
        "pico_favor_gap_medio_pts": "Pico Favor Médio (pts)",
        "duracao_media_entre_picos_min": "Duração Média entre Picos (min)",
        "curtose_tempo_fechamento_gap": "Curtose Tempo Fechamento",
        "curtose_gap_modulo_pts": "Curtose Gap Módulo",
        "desvio_padrao_gap_modulo_pts": "Desvio Padrão Gap Módulo",
        "assimetria_gap_modulo": "Assimetria Gap Módulo",
    }
    tabela = tabela.rename(columns=renomear)

    for col in tabela.columns:
        if col not in ["Faixa do Gap (Módulo pts)", "Ocorrências"]:
            tabela[col] = pd.to_numeric(tabela[col], errors="coerce").round(3)
    return tabela


def plotar_candles_estilo_corretora(base_intraday_minuto, dias_filtrados, titulo="Candles intraday por dia"):
    dias_filtrados = [pd.to_datetime(d) for d in dias_filtrados]
    blocos = []
    for dia in dias_filtrados:
        bloco = (
            base_intraday_minuto.loc[base_intraday_minuto["session_date"] == dia]
            .sort_values("datetime")
            .reset_index(drop=True)
            .copy()
        )
        if not bloco.empty:
            blocos.append((dia, bloco))

    if not blocos:
        return

    n = len(blocos)
    fig, axes = plt.subplots(n, 2, figsize=(19, 4.8 * n), gridspec_kw={"width_ratios": [8, 2]})
    if n == 1:
        axes = np.array([axes])
    fig.patch.set_facecolor("#0f1117")

    volume_col = "volume" if "volume" in base_intraday_minuto.columns else "tick_volume"

    for row, (dia, bloco) in enumerate(blocos):
        ax = axes[row, 0]
        ax_vol = axes[row, 1]

        bloco["x"] = mdates.date2num(bloco["datetime"])
        width = (1 / (24 * 60)) * 0.78

        ax.set_facecolor("#0f1117")
        ax_vol.set_facecolor("#0f1117")

        for _, linha in bloco.iterrows():
            cor = "#00c897" if linha["close"] >= linha["open"] else "#ff5a76"
            ax.vlines(linha["x"], linha["low"], linha["high"], color=cor, linewidth=0.8, alpha=0.95)

            corpo_min = min(linha["open"], linha["close"])
            corpo_altura = max(abs(linha["close"] - linha["open"]), 0.7)
            candle = plt.Rectangle((linha["x"] - width / 2, corpo_min), width, corpo_altura, facecolor=cor, edgecolor=cor, alpha=0.92)
            ax.add_patch(candle)

            ax_vol.bar(linha["x"], linha.get(volume_col, np.nan), width=width, color=cor, alpha=0.65)

        ax.axhline(bloco["close"].iloc[0], color="#6ea8fe", linewidth=0.9, alpha=0.6, linestyle="--")
        ax.set_title(f"{dia.strftime('%Y-%m-%d')} - Preço", color="white", fontsize=10)
        ax.set_ylabel("Preço", color="white")
        ax.tick_params(axis="x", colors="white")
        ax.tick_params(axis="y", colors="white")
        ax.grid(alpha=0.18, color="#6c757d")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))

        ax_vol.set_title("Volume", color="white", fontsize=10)
        ax_vol.tick_params(axis="x", colors="white")
        ax_vol.tick_params(axis="y", colors="white")
        ax_vol.grid(alpha=0.12, color="#6c757d")
        ax_vol.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        ax_vol.xaxis.set_major_locator(mdates.HourLocator(interval=2))

    axes[-1, 0].set_xlabel("Horário", color="white")
    axes[-1, 1].set_xlabel("Horário", color="white")
    fig.suptitle(titulo, fontsize=13, color="white")
    plt.tight_layout()
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Gera tabelas e grafico de apresentacao de gaps.")
    parser.add_argument("--passo-faixa", type=int, default=100)
    parser.add_argument("--limiar-sem-gap", type=float, default=20)
    parser.add_argument("--limiar-overshoot", type=float, default=120)
    parser.add_argument("--mov-inicio-gap", type=float, default=5)
    parser.add_argument("--dias", nargs="*", default=[])
    parser.add_argument("--mostrar-grafico", action="store_true")
    args = parser.parse_args()

    pasta_saida = Path("outputs_gap_win")
    caminho_intraday = pasta_saida / "intraday_limpo.csv"
    caminho_base_gap = pasta_saida / "base_gap.csv"
    caminho_raw = Path("WIN$N_M1.csv")

    if caminho_intraday.exists() and caminho_base_gap.exists():
        intraday = pd.read_csv(caminho_intraday)
        base_gap = pd.read_csv(caminho_base_gap)
        intraday["datetime"] = pd.to_datetime(intraday["datetime"])
        intraday["session_date"] = pd.to_datetime(intraday["session_date"])
        base_gap["session_date"] = pd.to_datetime(base_gap["session_date"])
    else:
        if not caminho_raw.exists():
            raise FileNotFoundError(
                "Não encontrei outputs nem o arquivo bruto WIN$N_M1.csv para fallback."
            )

        raw = pd.read_csv(caminho_raw, sep="\t", decimal=".")
        raw.columns = [c.strip().lower().replace("<", "").replace(">", "") for c in raw.columns]
        raw["datetime"] = pd.to_datetime(
            raw["date"].astype(str) + " " + raw["time"].astype(str),
            format="%Y.%m.%d %H:%M:%S",
            errors="coerce",
        )
        raw["session_date"] = raw["datetime"].dt.normalize()
        intraday = raw.sort_values("datetime").reset_index(drop=True)

        base_diaria = (
            intraday.groupby("session_date")
            .agg(
                open=("open", "first"),
                high=("high", "max"),
                low=("low", "min"),
                close=("close", "last"),
            )
            .sort_index()
        )
        base_diaria["prev_close"] = base_diaria["close"].shift(1)

        linhas = []
        datas = base_diaria.index.tolist()
        for i, dia in enumerate(datas):
            if i == 0:
                continue
            prev = datas[i - 1]
            dados_dia = intraday.loc[intraday["session_date"] == dia].sort_values("datetime").reset_index(drop=True)
            if dados_dia.empty:
                continue
            prev_close = float(base_diaria.loc[prev, "close"])
            abertura = float(base_diaria.loc[dia, "open"])
            maxima = float(base_diaria.loc[dia, "high"])
            minima = float(base_diaria.loc[dia, "low"])
            fechamento = float(base_diaria.loc[dia, "close"])
            gap = abertura - prev_close
            direcao = "positive" if gap > 0 else "negative" if gap < 0 else "flat"

            if direcao == "positive":
                hits = dados_dia.loc[dados_dia["low"] <= prev_close, "datetime"]
            elif direcao == "negative":
                hits = dados_dia.loc[dados_dia["high"] >= prev_close, "datetime"]
            else:
                hits = pd.Series([dados_dia["datetime"].iloc[0]])

            t_fill = np.nan
            fill_no_dia = 0
            if len(hits) > 0:
                fill_no_dia = 1
                t_fill = minutos_entre(dados_dia["datetime"].iloc[0], hits.iloc[0])

            rec = {
                "session_date": dia,
                "prev_close": prev_close,
                "open": abertura,
                "high": maxima,
                "low": minima,
                "close": fechamento,
                "gap_abs": gap,
                "gap_pct": (gap / prev_close) if prev_close else np.nan,
                "gap_direction": direcao,
                "gap_fill_no_dia": fill_no_dia,
                "time_to_fill_no_dia_min": t_fill,
                "fill_ate_5m": int(pd.notna(t_fill) and t_fill <= 5),
                "fill_ate_10m": int(pd.notna(t_fill) and t_fill <= 10),
                "fill_ate_20m": int(pd.notna(t_fill) and t_fill <= 20),
                "fill_ate_30m": int(pd.notna(t_fill) and t_fill <= 30),
                "close_vs_open_ret": fechamento / abertura - 1,
            }
            linhas.append(rec)

        base_gap = pd.DataFrame(linhas)
        base_gap["session_date"] = pd.to_datetime(base_gap["session_date"])

    linhas_metricas = []
    for _, linha in base_gap.iterrows():
        dados_dia = intraday.loc[intraday["session_date"] == linha["session_date"]].sort_values("datetime").reset_index(drop=True)
        if dados_dia.empty:
            continue
        linhas_metricas.append(
            {"session_date": linha["session_date"]}
            | medir_picos(
                dados_dia=dados_dia,
                abertura=float(linha["open"]),
                direcao_gap=linha["gap_direction"],
                prev_close=float(linha["prev_close"]),
                movimento_minimo_inicio_gap=args.mov_inicio_gap,
            )
        )

    base_metricas = pd.DataFrame(linhas_metricas)
    base = base_gap.merge(base_metricas, on="session_date", how="left")

    if "fill_ate_60m" not in base.columns:
        base["fill_ate_60m"] = np.where(
            base["time_to_fill_no_dia_min"].notna() & (base["time_to_fill_no_dia_min"] <= 60),
            1,
            0,
        )

    base["direcao_gap_ptbr"] = base["gap_direction"].map({"positive": "Gap de Alta", "negative": "Gap de Baixa", "flat": "Sem Gap"})
    base["gap_modulo_pts"] = base["gap_abs"].abs()
    base["faixa_gap_modulo"] = classificar_faixa_modulo(base["gap_abs"], passo=args.passo_faixa)

    base["fechamento_gap_ate_5m"] = base["fill_ate_5m"]
    base["fechamento_gap_ate_10m"] = base["fill_ate_10m"]
    base["fechamento_gap_ate_20m"] = base["fill_ate_20m"]
    base["fechamento_gap_ate_30m"] = base["fill_ate_30m"]
    base["fechamento_gap_ate_60m"] = base["fill_ate_60m"]
    base["fechamento_gap_no_dia"] = base["gap_fill_no_dia"]

    tabela_alta = montar_tabela_direcao(base, "positive")
    tabela_baixa = montar_tabela_direcao(base, "negative")

    tabela_fechada = base[
        [
            "session_date",
            "direcao_gap_ptbr",
            "gap_abs",
            "gap_modulo_pts",
            "faixa_gap_modulo",
            "tempo_inicio_fechamento_gap_min",
            "time_to_fill_no_dia_min",
            "tempo_ate_pico_max_min",
            "tempo_ate_pico_min_min",
            "pico_contra_gap_pts",
            "pico_favor_gap_pts",
            "duracao_entre_picos_min",
            "fechamento_gap_ate_30m",
            "fechamento_gap_no_dia",
        ]
    ].copy()
    tabela_fechada = tabela_fechada.rename(
        columns={
            "session_date": "Data",
            "direcao_gap_ptbr": "Direção do Gap",
            "gap_abs": "Gap (pts)",
            "gap_modulo_pts": "Gap |Módulo| (pts)",
            "faixa_gap_modulo": "Faixa do Gap |Módulo|",
            "tempo_inicio_fechamento_gap_min": "Tempo até Início do Fechamento (min)",
            "time_to_fill_no_dia_min": "Tempo até Fechar no Dia (min)",
            "tempo_ate_pico_max_min": "Tempo até Pico Máximo (min)",
            "tempo_ate_pico_min_min": "Tempo até Pico Mínimo (min)",
            "pico_contra_gap_pts": "Pico Contra o Gap (pts)",
            "pico_favor_gap_pts": "Pico a Favor do Gap (pts)",
            "duracao_entre_picos_min": "Duração entre Picos (min)",
            "fechamento_gap_ate_30m": "Fechou em até 30 min",
            "fechamento_gap_no_dia": "Fechou no Dia",
        }
    )
    tabela_fechada["Data"] = pd.to_datetime(tabela_fechada["Data"]).dt.strftime("%Y-%m-%d")
    tabela_fechada["Fechou em até 30 min"] = tabela_fechada["Fechou em até 30 min"].map({1: "Sim", 0: "Não"})
    tabela_fechada["Fechou no Dia"] = tabela_fechada["Fechou no Dia"].map({1: "Sim", 0: "Não"})

    overshoot = base.loc[base["gap_modulo_pts"] <= args.limiar_sem_gap].copy()
    overshoot["Maior Deslocamento Intraday (pts)"] = overshoot[["amplitude_ate_pico_max_pts", "amplitude_ate_pico_min_pts"]].max(axis=1)
    overshoot["Overshoot Relevante"] = (overshoot["Maior Deslocamento Intraday (pts)"] >= args.limiar_overshoot).astype(int)

    estat = (
        base.groupby("direcao_gap_ptbr")
        .agg(
            ocorrencias=("gap_abs", "size"),
            media_gap_modulo_pts=("gap_modulo_pts", "mean"),
            mediana_gap_modulo_pts=("gap_modulo_pts", "median"),
            desvio_padrao_gap_modulo_pts=("gap_modulo_pts", "std"),
            curtose_gap_modulo_pts=("gap_modulo_pts", lambda s: s.dropna().kurtosis()),
            assimetria_gap_modulo=("gap_modulo_pts", lambda s: s.dropna().skew()),
            media_tempo_fechamento_gap_min=("time_to_fill_no_dia_min", "mean"),
            mediana_tempo_fechamento_gap_min=("time_to_fill_no_dia_min", "median"),
            desvio_padrao_tempo_fechamento_gap=("time_to_fill_no_dia_min", "std"),
            curtose_tempo_fechamento_gap=("time_to_fill_no_dia_min", lambda s: s.dropna().kurtosis()),
        )
        .reset_index()
    )

    tabela_alta.to_csv(pasta_saida / "tabela_gap_alta_apresentacao.csv", index=False)
    tabela_baixa.to_csv(pasta_saida / "tabela_gap_baixa_apresentacao.csv", index=False)
    tabela_fechada.to_csv(pasta_saida / "tabela_unica_gap_apresentacao.csv", index=False)
    overshoot.to_csv(pasta_saida / "tabela_overshoot_sem_gap.csv", index=False)
    estat.to_csv(pasta_saida / "estatisticas_gap_direcao_apresentacao.csv", index=False)

    if args.dias:
        dias_plot = [pd.to_datetime(d) for d in args.dias]
    else:
        dias_plot = (
            base.assign(gap_mod=base["gap_abs"].abs())
            .sort_values("gap_mod", ascending=False)
            .head(3)["session_date"]
            .tolist()
        )
    if args.mostrar_grafico:
        plotar_candles_estilo_corretora(intraday, dias_plot)

    print("Arquivos gerados em:", pasta_saida.resolve())
    print("Dias do grafico:", [pd.to_datetime(d).strftime("%Y-%m-%d") for d in dias_plot])


if __name__ == "__main__":
    main()
