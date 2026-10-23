# Justificativa de Alinhamento à GoodWe e à Disciplina

## 1. Conexão com o Ecossistema GoodWe
A solução foi projetada para atuar como uma camada de inteligência sobre os dados gerados pelos inversores GoodWe.
- **Integração Real:** O arquivo `src/goodwe_reader.py` implementa a conexão local via biblioteca oficial `goodwe` (UDP 8899 / Modbus TCP 502), lendo sensores como `ppv`, `vpv1`, `ipv1`, `vgrid1` e `e_day`.
- **Complemento ao SEMS+:** Enquanto o SEMS+ foca no monitoramento e agendamento, nossa solução foca na **tradução dos dados em ações de sustentabilidade** e economia, calculando CO₂ evitado e gerando recomendações acionáveis baseadas em regras de negócio.

## 2. Alinhamento com a Disciplina
- **Linguagem e Frameworks:** Python, Pandas (análise de dados), Plotly (visualização) e Streamlit (dashboard interativo).
- **Sensores e Dados:** Modelagem de dados baseada nos sensores reais do inversor, garantindo que a transição do simulador para o hardware real seja transparente.
- **Sustentabilidade:** Cálculo do CO₂ evitado usando o fator de emissão do SIN (MCTI), demonstrando o impacto ambiental positivo da solução.