from pathlib import Path
import argparse

import numpy as np
import pandas as pd


def carregar_bases(pasta_saida: Path):
    intraday = pd.read_csv(pasta_saida / "intraday_limpo.csv")
    base_gap = pd.read_csv(pasta_saida / "base_gap.csv")

    intraday["datetime"] = pd.to_datetime(intraday["datetime"])
    intraday["session_date"] = pd.to_datetime(intraday["session_date"])
    base_gap["session_date"] = pd.to_datetime(base_gap["session_date"])
    intraday = intraday.sort_values(["session_date", "datetime"]).reset_index(drop=True)
    # Minuto relativo ao início do pregão (0, 1, 2, ...).
    intraday["minuto_sessao"] = intraday.groupby("session_date").cumcount()
    return intraday, base_gap


def lado_operacao_fechamento_gap(gap_abs: float):
    if gap_abs > 0:
        return "venda"
    if gap_abs < 0:
        return "compra"
    return "ignorar"


def calcular_alvo_fechamento_parcial(open_price: float, prev_close: float, gap_abs: float, alvo_fill_pct: float):
    gap_mod = abs(gap_abs)
    desloc = gap_mod * alvo_fill_pct
    if gap_abs > 0:
        return open_price - desloc
    if gap_abs < 0:
        return open_price + desloc
    return open_price


def calcular_stop_gap(open_price: float, gap_abs: float, stop_pct_gap: float):
    gap_mod = abs(gap_abs)
    desloc = gap_mod * stop_pct_gap
    if gap_abs > 0:
        return open_price + desloc
    if gap_abs < 0:
        return open_price - desloc
    return open_price


def obter_barra_entrada(dados_dia: pd.DataFrame, minuto_entrada: int):
    barra = dados_dia.loc[dados_dia["minuto_sessao"] >= minuto_entrada].head(1)
    if barra.empty:
        return None
    return barra.iloc[0]


def simular_trade_dia(
    dados_dia: pd.DataFrame,
    linha_gap: pd.Series,
    minuto_entrada: int,
    minuto_saida_max: int,
    alvo_fill_pct: float,
    stop_pct_gap: float,
    custo_round_trip_pts: float,
):
    lado = lado_operacao_fechamento_gap(float(linha_gap["gap_abs"]))
    if lado == "ignorar":
        return None

    entrada_barra = obter_barra_entrada(dados_dia, minuto_entrada)
    if entrada_barra is None:
        return None

    dt_entrada = entrada_barra["datetime"]
    preco_entrada = float(entrada_barra["open"])
    open_price = float(linha_gap["open"])
    prev_close = float(linha_gap["prev_close"])
    gap_abs = float(linha_gap["gap_abs"])

    alvo = calcular_alvo_fechamento_parcial(open_price, prev_close, gap_abs, alvo_fill_pct)
    stop = calcular_stop_gap(open_price, gap_abs, stop_pct_gap)

    janela = dados_dia.loc[dados_dia["minuto_sessao"] >= minuto_entrada].copy()
    janela = janela.loc[janela["minuto_sessao"] <= minuto_saida_max]
    if janela.empty:
        return None

    motivo_saida = "tempo_max"
    dt_saida = janela.iloc[-1]["datetime"]
    preco_saida = float(janela.iloc[-1]["close"])

    for _, barra in janela.iterrows():
        low = float(barra["low"])
        high = float(barra["high"])

        if lado == "venda":
            bate_alvo = low <= alvo
            bate_stop = high >= stop
        else:
            bate_alvo = high >= alvo
            bate_stop = low <= stop

        if bate_alvo and bate_stop:
            dist_alvo = abs(preco_entrada - alvo)
            dist_stop = abs(preco_entrada - stop)
            if dist_alvo <= dist_stop:
                bate_stop = False
            else:
                bate_alvo = False

        if bate_alvo:
            motivo_saida = "alvo"
            dt_saida = barra["datetime"]
            preco_saida = float(alvo)
            break
        if bate_stop:
            motivo_saida = "stop"
            dt_saida = barra["datetime"]
            preco_saida = float(stop)
            break

    if lado == "venda":
        pnl_bruto = preco_entrada - preco_saida
    else:
        pnl_bruto = preco_saida - preco_entrada
    pnl_liquido = pnl_bruto - custo_round_trip_pts

    return {
        "session_date": linha_gap["session_date"],
        "gap_direction": linha_gap["gap_direction"],
        "gap_abs": gap_abs,
        "lado_operacao": lado,
        "minuto_entrada": minuto_entrada,
        "minuto_saida_max": minuto_saida_max,
        "alvo_fill_pct": alvo_fill_pct,
        "stop_pct_gap": stop_pct_gap,
        "preco_entrada": preco_entrada,
        "preco_alvo": alvo,
        "preco_stop": stop,
        "preco_saida": preco_saida,
        "dt_entrada": dt_entrada,
        "dt_saida": dt_saida,
        "motivo_saida": motivo_saida,
        "pnl_bruto_pts": pnl_bruto,
        "pnl_liquido_pts": pnl_liquido,
        "retorno_rel_gap": pnl_bruto / abs(gap_abs) if abs(gap_abs) > 0 else np.nan,
    }


def resumir_resultados(df_trades: pd.DataFrame):
    if df_trades.empty:
        return pd.DataFrame()

    grupo = ["minuto_entrada", "minuto_saida_max", "alvo_fill_pct", "stop_pct_gap"]
    resumo = (
        df_trades.groupby(grupo, dropna=False)
        .agg(
            trades=("pnl_liquido_pts", "size"),
            taxa_acerto=("pnl_liquido_pts", lambda s: (s > 0).mean()),
            pnl_medio_pts=("pnl_liquido_pts", "mean"),
            pnl_mediano_pts=("pnl_liquido_pts", "median"),
            pnl_total_pts=("pnl_liquido_pts", "sum"),
            pnl_std_pts=("pnl_liquido_pts", "std"),
            media_retorno_rel_gap=("retorno_rel_gap", "mean"),
            pct_alvo=("motivo_saida", lambda s: (s == "alvo").mean()),
            pct_stop=("motivo_saida", lambda s: (s == "stop").mean()),
            pct_tempo=("motivo_saida", lambda s: (s == "tempo_max").mean()),
        )
        .reset_index()
    )

    resumo["taxa_acerto"] = (resumo["taxa_acerto"] * 100).round(2)
    resumo["pct_alvo"] = (resumo["pct_alvo"] * 100).round(2)
    resumo["pct_stop"] = (resumo["pct_stop"] * 100).round(2)
    resumo["pct_tempo"] = (resumo["pct_tempo"] * 100).round(2)
    for c in ["pnl_medio_pts", "pnl_mediano_pts", "pnl_total_pts", "pnl_std_pts", "media_retorno_rel_gap"]:
        resumo[c] = resumo[c].round(4)
    return resumo


def parse_lista_int(txt: str):
    return [int(x.strip()) for x in txt.split(",") if x.strip()]


def parse_lista_float(txt: str):
    return [float(x.strip()) for x in txt.split(",") if x.strip()]


def main():
    parser = argparse.ArgumentParser(description="Simulador de estratégia de fechamento parcial do gap por minuto.")
    parser.add_argument("--pasta-saida", default="outputs_gap_win")
    # Defaults mais leves para execução rápida sem travar notebook.
    parser.add_argument("--entradas", default="2,5")
    parser.add_argument("--saidas-max", default="10,20,30")
    parser.add_argument("--alvos-fill", default="0.8,1.0")
    parser.add_argument("--stops-gap", default="0.5,1.0")
    parser.add_argument("--custo-pts", type=float, default=20.0)
    parser.add_argument("--direcao", default="ambos", choices=["ambos", "positive", "negative"])
    args = parser.parse_args()

    pasta_saida = Path(args.pasta_saida)
    intraday, base_gap = carregar_bases(pasta_saida)

    entradas = parse_lista_int(args.entradas)
    saidas = parse_lista_int(args.saidas_max)
    alvos = parse_lista_float(args.alvos_fill)
    stops = parse_lista_float(args.stops_gap)

    if args.direcao != "ambos":
        base_gap = base_gap.loc[base_gap["gap_direction"] == args.direcao].copy()

    trades = []
    for _, linha_gap in base_gap.iterrows():
        dados_dia = intraday.loc[intraday["session_date"] == linha_gap["session_date"]].sort_values("datetime")
        if dados_dia.empty:
            continue
        for minuto_entrada in entradas:
            for minuto_saida_max in saidas:
                if minuto_saida_max < minuto_entrada:
                    continue
                for alvo_fill_pct in alvos:
                    for stop_pct_gap in stops:
                        trade = simular_trade_dia(
                            dados_dia=dados_dia,
                            linha_gap=linha_gap,
                            minuto_entrada=minuto_entrada,
                            minuto_saida_max=minuto_saida_max,
                            alvo_fill_pct=alvo_fill_pct,
                            stop_pct_gap=stop_pct_gap,
                            custo_round_trip_pts=args.custo_pts,
                        )
                        if trade is not None:
                            trades.append(trade)

    df_trades = pd.DataFrame(trades)
    resumo = resumir_resultados(df_trades)
    if not resumo.empty:
        resumo = resumo.sort_values(["pnl_medio_pts", "taxa_acerto"], ascending=False).reset_index(drop=True)

    arq_trades = pasta_saida / "simulador_gap_trades.csv"
    arq_resumo = pasta_saida / "simulador_gap_resumo.csv"
    df_trades.to_csv(arq_trades, index=False, encoding="utf-8-sig")
    resumo.to_csv(arq_resumo, index=False, encoding="utf-8-sig")

    print("Simulação finalizada.")
    print("Trades:", arq_trades.resolve())
    print("Resumo:", arq_resumo.resolve())
    if not resumo.empty:
        print("\nTop 10 configurações:")
        print(resumo.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
