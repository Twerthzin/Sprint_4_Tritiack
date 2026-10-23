"""
Motor de recomendações baseado em regras de decisão.

Analisa os dados de geração, consumo e temperatura do inversor e produz
uma lista de recomendações acionáveis, com prioridade e justificativa.
É a camada de "inteligência" que complementa o monitoramento passivo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


# ---------------------------------------------------------------------------
# Limiares de decisão
# ---------------------------------------------------------------------------

EXCEDENTE_RELEVANTE_KW: float = 1.0       # geração - consumo acima disso é "excedente"
DEFICIT_RELEVANTE_KW: float = 0.8         # consumo - geração acima disso é "déficit"
TEMP_ALERTA_C: float = 55.0               # temperatura de atenção do inversor
TEMP_CRITICA_C: float = 65.0              # temperatura crítica (derating)
HORARIO_PICO_TARIFARIO: tuple = (18, 21)  # faixa típica de ponta


@dataclass
class Recomendacao:
    """Uma ação sugerida pelo motor de recomendações."""

    timestamp: pd.Timestamp
    prioridade: str          # "alta", "media", "baixa"
    categoria: str           # "excedente", "deficit", "temperatura", "economia"
    acao: str                # texto curto e acionável
    justificativa: str       # por que essa recomendação foi gerada


def _em_horario_pico(hora: int) -> bool:
    inicio, fim = HORARIO_PICO_TARIFARIO
    return inicio <= hora < fim


def gerar_recomendacoes(df: pd.DataFrame) -> List[Recomendacao]:
    """
    Percorre o DataFrame e gera recomendações pontuais.

    Parâmetros
    ----------
    df : pd.DataFrame
        Deve conter as colunas `timestamp`, `potencia_gerada_kw`,
        `potencia_consumo_kw` e `temperatura_inversor_c`.

    Retorna
    -------
    list[Recomendacao]
        Lista ordenada por prioridade (alta → baixa) e horário.
    """
    colunas_necessarias = {
        "timestamp",
        "potencia_gerada_kw",
        "potencia_consumo_kw",
        "temperatura_inversor_c",
    }
    if not colunas_necessarias.issubset(df.columns):
        faltando = colunas_necessarias - set(df.columns)
        raise ValueError(f"Colunas ausentes no DataFrame: {faltando}")

    recomendacoes: List[Recomendacao] = []

    for _, linha in df.iterrows():
        geracao = linha["potencia_gerada_kw"]
        consumo = linha["potencia_consumo_kw"]
        temperatura = linha["temperatura_inversor_c"]
        ts = linha["timestamp"]
        hora = ts.hour

        # 1. Excedente de geração → oportunidade de uso ou armazenamento
        if geracao - consumo >= EXCEDENTE_RELEVANTE_KW:
            recomendacoes.append(
                Recomendacao(
                    timestamp=ts,
                    prioridade="media",
                    categoria="excedente",
                    acao="Ligar cargas pesadas (máquina de lavar, ar-condicionado) ou carregar bateria",
                    justificativa=(
                        f"Geração de {geracao:.2f} kW supera consumo de "
                        f"{consumo:.2f} kW em {geracao - consumo:.2f} kW."
                    ),
                )
            )

        # 2. Déficit em horário de pico tarifário → evitar consumo
        if consumo - geracao >= DEFICIT_RELEVANTE_KW and _em_horario_pico(hora):
            recomendacoes.append(
                Recomendacao(
                    timestamp=ts,
                    prioridade="alta",
                    categoria="economia",
                    acao="Postergar uso de equipamentos de alto consumo para após as 21h",
                    justificativa=(
                        f"Déficit de {consumo - geracao:.2f} kW durante horário de "
                        f"ponta ({HORARIO_PICO_TARIFARIO[0]}h–{HORARIO_PICO_TARIFARIO[1]}h)."
                    ),
                )
            )

        # 3. Temperatura elevada → atenção operacional
        if temperatura >= TEMP_CRITICA_C:
            recomendacoes.append(
                Recomendacao(
                    timestamp=ts,
                    prioridade="alta",
                    categoria="temperatura",
                    acao="Verificar ventilação do inversor imediatamente",
                    justificativa=(
                        f"Temperatura de {temperatura:.1f} °C acima do limite crítico "
                        f"({TEMP_CRITICA_C} °C). Risco de derating."
                    ),
                )
            )
        elif temperatura >= TEMP_ALERTA_C:
            recomendacoes.append(
                Recomendacao(
                    timestamp=ts,
                    prioridade="media",
                    categoria="temperatura",
                    acao="Monitorar temperatura do inversor",
                    justificativa=(
                        f"Temperatura de {temperatura:.1f} °C acima do limiar de "
                        f"atenção ({TEMP_ALERTA_C} °C)."
                    ),
                )
            )

    # Ordenar: prioridade alta primeiro, depois por horário
    ordem_prioridade = {"alta": 0, "media": 1, "baixa": 2}
    recomendacoes.sort(
        key=lambda r: (ordem_prioridade.get(r.prioridade, 3), r.timestamp)
    )
    return recomendacoes


def resumo_recomendacoes(recomendacoes: List[Recomendacao]) -> dict:
    """Conta recomendações por categoria e prioridade."""
    resumo = {"total": len(recomendacoes), "por_prioridade": {}, "por_categoria": {}}
    for r in recomendacoes:
        resumo["por_prioridade"][r.prioridade] = (
            resumo["por_prioridade"].get(r.prioridade, 0) + 1
        )
        resumo["por_categoria"][r.categoria] = (
            resumo["por_categoria"].get(r.categoria, 0) + 1
        )
    return resumo


if __name__ == "__main__":
    from src.simulator import gerar_dados_simulados

    df = gerar_dados_simulados()
    recomendacoes = gerar_recomendacoes(df)

    print(f"Total de recomendações geradas: {len(recomendacoes)}\n")
    for r in recomendacoes[:10]:
        print(
            f"[{r.prioridade.upper():5}] {r.timestamp:%H:%M} "
            f"({r.categoria}) → {r.acao}"
        )
        print(f"         Justificativa: {r.justificativa}\n")

    print("Resumo:", resumo_recomendacoes(recomendacoes))