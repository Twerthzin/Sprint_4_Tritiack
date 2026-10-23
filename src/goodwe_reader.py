"""
Leitor de dados de inversores GoodWe.

Tenta conectar a um inversor real via biblioteca `goodwe` (UDP 8899 ou
Modbus/TCP 502). Se não houver inversor acessível ou se a leitura falhar,
retorna `None` e o chamador pode usar o simulador como fallback.

A função `carregar_dados` é o ponto único de entrada: o restante do
sistema (analyzer, recommender, dashboard) não precisa saber se os dados
vêm de hardware real ou de simulação.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Configuração de conexão
# ---------------------------------------------------------------------------

# IP do inversor na rede local. Pode ser sobrescrito por variável de ambiente
# GOODWE_IP. Sem IP configurado, o leitor cai automaticamente no simulador.
IP_PADRAO: Optional[str] = None
TIMEOUT_SEGUNDOS: float = 5.0


@dataclass
class LeituraInversor:
    """Uma leitura pontual de um inversor GoodWe."""

    timestamp: datetime
    potencia_gerada_kw: float
    tensao_cc_v: float
    corrente_cc_a: float
    tensao_ca_v: float
    temperatura_inversor_c: float
    energia_dia_kwh: float


# ---------------------------------------------------------------------------
# Leitura real via biblioteca goodwe
# ---------------------------------------------------------------------------

async def _ler_inversor_async(ip: str) -> Optional[LeituraInversor]:
    """Conecta ao inversor e retorna uma leitura, ou None em caso de falha."""
    try:
        import goodwe
    except ImportError:
        return None

    try:
        inverter = await asyncio.wait_for(
            goodwe.connect(ip), timeout=TIMEOUT_SEGUNDOS
        )
        dados = await asyncio.wait_for(
            inverter.read_runtime_data(), timeout=TIMEOUT_SEGUNDOS
        )
    except Exception:
        # Rede indisponível, IP errado, inversor desligado, timeout etc.
        return None

    # A biblioteca expõe os sensores via inverter.sensors() e os valores
    # via dicionário indexado por sensor.id_. Mapeamos apenas os que usamos.
    sensores = {s.id_: s for s in inverter.sensors()}

    def valor(*ids: str) -> float:
        for sid in ids:
            if sid in dados and dados[sid] is not None:
                try:
                    return float(dados[sid])
                except (TypeError, ValueError):
                    continue
        return 0.0

    return LeituraInversor(
        timestamp=datetime.now(),
        potencia_gerada_kw=valor("ppv", "pac") / 1000.0,  # W → kW
        tensao_cc_v=valor("vpv1", "vpv"),
        corrente_cc_a=valor("ipv1", "ipv"),
        tensao_ca_v=valor("vgrid1", "vac1"),
        temperatura_inversor_c=valor("tempperature", "temperature"),
        energia_dia_kwh=valor("e_day", "eday"),
    )


def ler_inversor_real(ip: Optional[str] = None) -> Optional[LeituraInversor]:
    """
    Lê um inversor GoodWe de forma síncrona.

    Retorna `None` se não houver IP configurado ou se a leitura falhar.
    """
    if ip is None:
        import os

        ip = os.environ.get("GOODWE_IP") or IP_PADRAO
    if not ip:
        return None
    return asyncio.run(_ler_inversor_async(ip))


# ---------------------------------------------------------------------------
# Ponto único de entrada
# ---------------------------------------------------------------------------

def carregar_dados(ip: Optional[str] = None) -> tuple[pd.DataFrame, str]:
    """
    Carrega dados de geração e consumo.

    Tenta primeiro o inversor real. Se falhar, usa o simulador.

    Retorna
    -------
    (pd.DataFrame, str)
        O DataFrame com os dados e a origem usada ("real" ou "simulado").
    """
    leitura = ler_inversor_real(ip)

    if leitura is not None:
        # Em um cenário real, seria necessário acumular leituras ao longo do
        # tempo para montar o histórico. Para uma demonstração pontual, criamos
        # um DataFrame de uma linha e sinalizamos a origem.
        df = pd.DataFrame(
            [
                {
                    "timestamp": leitura.timestamp,
                    "potencia_gerada_kw": leitura.potencia_gerada_kw,
                    "potencia_consumo_kw": 0.0,  # consumo viria de medidor separado
                    "tensao_ca_v": leitura.tensao_ca_v,
                    "tensao_cc_v": leitura.tensao_cc_v,
                    "corrente_cc_a": leitura.corrente_cc_a,
                    "temperatura_inversor_c": leitura.temperatura_inversor_c,
                    "energia_dia_kwh": leitura.energia_dia_kwh,
                }
            ]
        )
        return df, "real"

    # Fallback: simulação
    from src.simulator import gerar_dados_simulados

    return gerar_dados_simulados(), "simulado"


if __name__ == "__main__":
    df, origem = carregar_dados()
    print(f"Origem dos dados: {origem}")
    print(f"Linhas carregadas: {len(df)}")
    print(df.head().to_string(index=False))