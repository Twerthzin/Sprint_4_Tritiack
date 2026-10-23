"""
Simulador de dados de um inversor GoodWe.

Os campos simulados espelham os sensores que a biblioteca `goodwe`
expõe ao ler um inversor real (potência CA, potência CC, tensão,
corrente, temperatura e energia diária). Dessa forma, o restante do
sistema pode trocar o simulador pelo leitor real sem alterações.

Referência dos sensores: https://pypi.org/project/goodwe/
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Constantes de configuração do cenário simulado
# ---------------------------------------------------------------------------

POTENCIA_PICO_KW: float = 5.0          # potência máxima do sistema fotovoltaico
CONSUMO_BASE_KW: float = 0.4           # consumo mínimo da residência
CONSUMO_PICO_KW: float = 1.8           # pico de consumo residencial
TENSAO_CA_NOMINAL_V: float = 220.0     # tensão da rede (fase)
TENSAO_CC_NOMINAL_V: float = 380.0     # tensão do string fotovoltaico
SEED_PADRAO: int = 42                  # semente para reprodutibilidade


def _fator_solar(hora: float) -> float:
    """Curva senoidal de geração solar entre 6h e 18h."""
    if hora < 6 or hora > 18:
        return 0.0
    return float(np.sin((hora - 6) / 12 * np.pi))


def _perfil_consumo(hora: float) -> float:
    """Perfil residencial: pico de manhã (7-9h) e à noite (18-22h)."""
    manha = np.exp(-((hora - 8) ** 2) / 2.0)
    noite = np.exp(-((hora - 20) ** 2) / 2.0)
    return CONSUMO_BASE_KW + CONSUMO_PICO_KW * float(manha + noite)


def gerar_dados_simulados(
    horas: int = 24,
    intervalo_min: int = 60,
    seed: Optional[int] = SEED_PADRAO,
) -> pd.DataFrame:
    """
    Gera um DataFrame com leituras simuladas de um inversor GoodWe.

    Parâmetros
    ----------
    horas : int
        Quantidade de horas a simular (padrão: 24).
    intervalo_min : int
        Intervalo entre leituras em minutos (padrão: 60).
    seed : int | None
        Semente do gerador aleatório. Use None para dados diferentes a
        cada execução.

    Retorna
    -------
    pd.DataFrame
        Colunas: timestamp, potencia_gerada_kw, potencia_consumo_kw,
        tensao_ca_v, tensao_cc_v, corrente_cc_a, temperatura_inversor_c,
        energia_dia_kwh.
    """
    if seed is not None:
        np.random.seed(seed)

    hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    agora = hoje
    passo = timedelta(minutes=intervalo_min)
    total_leituras = int(horas * 60 / intervalo_min)

    registros = []
    energia_acumulada = 0.0

    for i in range(total_leituras):
        ts = agora + i * passo
        hora_decimal = ts.hour + ts.minute / 60.0

        # Geração fotovoltaica (com ruído realista)
        fator = _fator_solar(hora_decimal)
        potencia_gerada = max(
            0.0, fator * POTENCIA_PICO_KW + np.random.normal(0, 0.15)
        )

        # Consumo residencial (com ruído)
        potencia_consumo = max(
            0.1, _perfil_consumo(hora_decimal) + np.random.normal(0, 0.1)
        )

        # Tensões e correntes derivadas
        tensao_cc = (
            TENSAO_CC_NOMINAL_V * (0.6 + 0.4 * fator)
            if potencia_gerada > 0
            else 0.0
        )
        corrente_cc = (
            (potencia_gerada * 1000) / tensao_cc if tensao_cc > 0 else 0.0
        )
        tensao_ca = TENSAO_CA_NOMINAL_V + np.random.normal(0, 2.0)

        # Temperatura do inversor: sobe com a potência e com o calor do dia
        temperatura = 25 + 0.6 * potencia_gerada + np.random.normal(0, 1.0)

        # Energia acumulada no dia (kWh)
        energia_acumulada += potencia_gerada * (intervalo_min / 60.0)

        registros.append(
            {
                "timestamp": ts,
                "potencia_gerada_kw": round(potencia_gerada, 3),
                "potencia_consumo_kw": round(potencia_consumo, 3),
                "tensao_ca_v": round(float(tensao_ca), 1),
                "tensao_cc_v": round(float(tensao_cc), 1),
                "corrente_cc_a": round(float(corrente_cc), 2),
                "temperatura_inversor_c": round(float(temperatura), 1),
                "energia_dia_kwh": round(energia_acumulada, 3),
            }
        )

    return pd.DataFrame(registros)


if __name__ == "__main__":
    df = gerar_dados_simulados()
    print(df.head(10).to_string(index=False))
    print("\nResumo:")
    print(df.describe().T[["mean", "min", "max"]].round(2))