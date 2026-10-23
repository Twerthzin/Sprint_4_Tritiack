"""
Cálculo de métricas de desempenho a partir dos dados de geração e consumo.

As funções aqui são agnósticas à origem dos dados: funcionam tanto com o
DataFrame gerado por `src.simulator` quanto com dados reais lidos de um
inversor GoodWe via biblioteca `goodwe`.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict

import pandas as pd


# ---------------------------------------------------------------------------
# Parâmetros energéticos e econômicos
# ---------------------------------------------------------------------------

# Fator médio de emissão da rede elétrica brasileira (SIN), em kg CO2/kWh.
# Referência: Ministério da Ciência, Tecnologia e Inovação (MCTI), 2023.
FATOR_CO2_KG_POR_KWH: float = 0.0385

# Tarifa residencial média no Brasil (R$/kWh). Ajustável por região.
TARIFA_RS_POR_KWH: float = 0.85


@dataclass
class Metricas:
    """Resultado consolidado da análise de um período."""

    energia_gerada_kwh: float
    energia_consumida_kwh: float
    autoconsumo_kwh: float
    injecao_rede_kwh: float
    importacao_rede_kwh: float
    eficiencia_autoconsumo_pct: float
    co2_evitado_kg: float
    economia_estimada_rs: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


def calcular_metricas(
    df: pd.DataFrame,
    intervalo_min: int = 60,
    fator_co2: float = FATOR_CO2_KG_POR_KWH,
    tarifa: float = TARIFA_RS_POR_KWH,
) -> Metricas:
    """
    Calcula métricas de desempenho a partir de um DataFrame com as colunas
    `potencia_gerada_kw` e `potencia_consumo_kw`.

    Parâmetros
    ----------
    df : pd.DataFrame
        Dados de geração e consumo. Deve conter as colunas
        `potencia_gerada_kw` e `potencia_consumo_kw`.
    intervalo_min : int
        Intervalo entre leituras, em minutos. Usado para converter
        potência (kW) em energia (kWh).
    fator_co2 : float
        Fator de emissão em kg CO2/kWh.
    tarifa : float
        Tarifa em R$/kWh para estimativa de economia.

    Retorna
    -------
    Metricas
        Objeto com todas as métricas calculadas.
    """
    if df.empty:
        raise ValueError("DataFrame vazio: não há dados para analisar.")

    colunas_necessarias = {"potencia_gerada_kw", "potencia_consumo_kw"}
    if not colunas_necessarias.issubset(df.columns):
        faltando = colunas_necessarias - set(df.columns)
        raise ValueError(f"Colunas ausentes no DataFrame: {faltando}")

    fator_hora = intervalo_min / 60.0

    geracao = df["potencia_gerada_kw"].clip(lower=0)
    consumo = df["potencia_consumo_kw"].clip(lower=0)

    energia_gerada = float((geracao * fator_hora).sum())
    energia_consumida = float((consumo * fator_hora).sum())

    # Autoconsumo = o que foi gerado e consumido no mesmo instante
    autoconsumo = float((geracao.combine(consumo, min) * fator_hora).sum())

    # Excedente injetado na rede
    injecao = float(((geracao - consumo).clip(lower=0) * fator_hora).sum())

    # Déficit importado da rede
    importacao = float(((consumo - geracao).clip(lower=0) * fator_hora).sum())

    eficiencia = (autoconsumo / energia_gerada * 100) if energia_gerada > 0 else 0.0

    co2_evitado = energia_gerada * fator_co2
    economia = (autoconsumo + injecao) * tarifa

    return Metricas(
        energia_gerada_kwh=round(energia_gerada, 3),
        energia_consumida_kwh=round(energia_consumida, 3),
        autoconsumo_kwh=round(autoconsumo, 3),
        injecao_rede_kwh=round(injecao, 3),
        importacao_rede_kwh=round(importacao, 3),
        eficiencia_autoconsumo_pct=round(eficiencia, 2),
        co2_evitado_kg=round(co2_evitado, 3),
        economia_estimada_rs=round(economia, 2),
    )

def enriquecer_dataframe(df: pd.DataFrame, intervalo_min: int = 60) -> pd.DataFrame:
    """
    Adiciona colunas derivadas ao DataFrame para uso em gráficos e no dashboard.

    Colunas adicionadas: autoconsumo_kw, excedente_kw, deficit_kw.
    """
    fator_hora = intervalo_min / 60.0
    df = df.copy()

    geracao = df["potencia_gerada_kw"].clip(lower=0)
    consumo = df["potencia_consumo_kw"].clip(lower=0)

    df["autoconsumo_kw"] = geracao.combine(consumo, min).round(3)
    df["excedente_kw"] = (geracao - consumo).clip(lower=0).round(3)
    df["deficit_kw"] = (consumo - geracao).clip(lower=0).round(3)
    df["energia_intervalo_kwh"] = (geracao * fator_hora).round(3)

    return df


if __name__ == "__main__":
    from src.simulator import gerar_dados_simulados

    df = gerar_dados_simulados()
    metricas = calcular_metricas(df)

    print("=== Métricas do período simulado ===")
    for chave, valor in metricas.to_dict().items():
        print(f"{chave:.<35} {valor}")