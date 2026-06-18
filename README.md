# Game Skild

> Também referido nos documentos como *Guardião Gamer*.

Protótipo acadêmico de controle parental e segurança infantil em jogos online. A aplicação analisa mensagens simuladas de chats de jogos, classifica o risco como baixo, médio ou alto e gera alertas para pais, responsáveis ou moderadores.

> Importante: não use dados reais de crianças. Este projeto é demonstrativo, local e acadêmico.

## Objetivo

O Guardião Gamer propõe uma aplicação capaz de identificar indícios de:

- Solicitação de dados pessoais.
- Tentativa de levar a conversa para fora do jogo.
- Pedido de segredo ou isolamento.
- Ofertas de presentes virtuais em troca de contato.
- Pedidos de foto, vídeo ou imagem pessoal.
- Golpes envolvendo senha, login ou código de verificação.

## Estrutura de pastas

```text
.
├── backend/
│   ├── analyzer.py          # classificador de risco por regras (NLP explicavel)
│   ├── classifier.py        # modelo de aprendizado de maquina (Naive Bayes) que aprende
│   ├── notifications.py     # notificacoes em tempo real (SSE) e Web Push (VAPID)
│   ├── app.py               # API Flask + entrega do frontend
│   ├── evaluate.py          # metricas (matriz de confusao, precisao, recall, F1)
│   ├── test_analyzer.py     # testes automatizados (unittest)
│   └── requirements.txt
├── data/
│   ├── simulated_messages.json   # base rotulada ficticia (segura/suspeita/perigosa)
│   ├── learning_data.json        # correcoes humanas aprendidas (gitignore)
│   ├── database.json             # dados gerados na execucao (gitignore)
│   ├── vapid.json                # chaves de Web Push (gitignore)
│   └── push_subscriptions.json   # inscricoes de notificacao (gitignore)
├── docs/
│   └── projeto_academico.md
├── frontend/
│   ├── app.js
│   ├── index.html
│   ├── sw.js                # service worker (Web Push)
│   ├── manifest.webmanifest
│   ├── generate_icons.py    # gera os icones PWA (escudo)
│   ├── icon-192.png
│   ├── icon-512.png
│   └── styles.css
└── README.md
```

## Tecnologias

- Python 3
- Flask
- HTML, CSS e JavaScript (PWA)
- Análise híbrida: regras explicáveis de NLP + modelo de aprendizado de máquina (Naive Bayes em Python puro) que melhora com as correções humanas
- Notificações em tempo real: Server-Sent Events (app aberto) e Web Push/VAPID (app fechado)

## Instalação

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

No Linux/macOS, a ativação do ambiente virtual costuma ser:

```bash
source .venv/bin/activate
```

## Execução

```bash
cd backend
python app.py
```

Abra no computador:

```text
http://127.0.0.1:5000
```

Use o botão **Carregar exemplos** para popular a aplicação com mensagens fictícias.

## Testar no celular

1. Conecte o computador e o celular na mesma rede Wi-Fi.
2. Execute o backend:

```bash
cd backend
python app.py
```

3. O terminal mostrará um endereço parecido com:

```text
Celular na mesma Wi-Fi: http://192.168.18.226:5000
```

4. Abra esse endereço no navegador do celular.
5. Se o Windows Firewall perguntar, permita o Python em rede privada.

Também existe um bloco na própria tela do Guardião Gamer chamado **Teste no celular**, que mostra os links detectados automaticamente.

Para trocar a porta:

```bash
set PORT=5001
python app.py
```

No PowerShell:

```powershell
$env:PORT = "5001"
python app.py
```

## API principal

### Verificar saúde

```http
GET /api/health
```

### Consultar links de rede local

```http
GET /api/network
```

### Cadastrar criança fictícia

```http
POST /api/children
Content-Type: application/json

{
  "child_name": "Crianca Simulada",
  "responsible_name": "Responsavel Simulado",
  "age": 11
}
```

### Registrar e analisar mensagem

```http
POST /api/messages
Content-Type: application/json

{
  "child_id": "id-retornado-no-cadastro",
  "sender_name": "Jogador123",
  "sender_type": "desconhecido",
  "game": "Arena Escolar",
  "message": "Me chama no WhatsApp depois do jogo."
}
```

### Consultar alertas

```http
GET /api/alerts
```

### Ensinar o modelo (correção humana)

Quando o responsável confirma ou corrige o nível de um alerta, o exemplo entra na base
de aprendizado e o modelo é re-treinado na hora.

```http
POST /api/feedback
Content-Type: application/json

{
  "message": "vamos manter isso em segredo",
  "level": "alto"
}
```

### Estado do modelo

```http
GET /api/model
```

### Notificações em tempo real (SSE)

```http
GET /api/stream
```

### Web Push (app fechado)

```http
GET  /api/push/public-key      # chave pública VAPID
POST /api/push/subscribe       # registra a inscrição do navegador
POST /api/push/test            # dispara uma notificação de teste
```

## Como a análise funciona

A classificação combina duas camadas:

1. **Regras explicáveis** (`backend/analyzer.py`): normaliza a mensagem, procura padrões
   suspeitos e soma pesos por categoria. A pontuação vai de 0 a 100:
   - 0 a 34: risco baixo.
   - 35 a 69: risco médio.
   - 70 a 100: risco alto.
2. **Aprendizado de máquina** (`backend/classifier.py`): um Naive Bayes treinado na base
   simulada e nas correções humanas estima o nível de risco de forma independente.

O nível final é o **mais severo** entre as duas camadas. Quando o modelo eleva o risco,
isso é registrado em `risk_source` e os termos mais influentes são destacados, mantendo a
decisão transparente. Mensagens de risco alto recebem recomendação de bloqueio ou retenção
para revisão humana.

### Como o modelo aprende com o que acontece

O classificador começa treinado com `data/simulated_messages.json`. A cada correção enviada
em `/api/feedback`, o exemplo é gravado em `data/learning_data.json` e o modelo é re-treinado
imediatamente — então o sistema melhora conforme os responsáveis revisam os alertas.

## Notificações

- **Tempo real (app aberto):** o painel mantém uma conexão SSE (`/api/stream`) e, ao surgir
  um alerta de risco médio ou alto, mostra um aviso na hora e dispara uma notificação do
  navegador.
- **App fechado / celular bloqueado:** com o botão **Ativar notificações**, o navegador
  registra o service worker (`frontend/sw.js`) e uma inscrição de Web Push. Requer HTTPS ou
  `localhost` (o navegador bloqueia Web Push em HTTP de rede comum).

## Testes automatizados

Os testes usam apenas a biblioteca padrão do Python (`unittest`), sem dependências extras.

```bash
cd backend
python -m unittest
```

Os testes verificam, entre outros pontos, que:

- mensagens seguras ficam em risco baixo;
- pedido de contato externo, dados pessoais, imagem e senha geram alerta;
- combinações perigosas (segredo + apagar conversa, presente + contato) elevam o risco para alto;
- nenhuma mensagem perigosa da base é classificada como segura.

## Avaliação e métricas

O script `evaluate.py` roda o classificador sobre a base rotulada simulada e calcula
matriz de confusão, acurácia, precisão, revocação (recall) e F1 por classe.

```bash
cd backend
python evaluate.py
```

Mapeamento entre nível de risco e rótulo: `baixo → segura`, `medio → suspeita`, `alto → perigosa`.

Resultados na base simulada atual (36 mensagens fictícias, 12 por classe):

- Acurácia geral: **80,6%**
- F1 macro: **80,0%**
- Cobertura de alertas para mensagens perigosas: **100%** (12/12)
- Falsos negativos críticos (perigosa classificada como segura): **0**

Para segurança infantil, o erro mais grave é o falso negativo. Por isso o foco do projeto
é garantir que toda mensagem perigosa gere pelo menos um alerta, mesmo quando o nível
exato (médio ou alto) varia. As mensagens perigosas que aparecem como "suspeita" na matriz
de confusão ainda disparam alerta para revisão humana.

> Observação: os números podem variar conforme a base rotulada for ampliada. Recomenda-se
> rodar `python evaluate.py` antes da apresentação para refletir a versão atual dos dados.

## Privacidade, LGPD e consentimento

Este projeto deve ser tratado apenas como protótipo acadêmico. Em uma aplicação real, seria necessário obter orientação jurídica e adequar o sistema à LGPD, especialmente por envolver dados de crianças e adolescentes. Boas práticas mínimas:

- Usar consentimento apropriado dos responsáveis.
- Coletar somente dados necessários.
- Informar finalidade e tempo de retenção.
- Proteger dados com controle de acesso, criptografia e auditoria.
- Permitir revisão humana de alertas automatizados.
- Não usar dados reais de crianças sem base legal, autorização e avaliação ética.

Referências úteis:

- Lei Geral de Proteção de Dados Pessoais, Lei nº 13.709/2018: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/outros-documentos-e-publicacoes-institucionais/lgpd-en-lei-no-13-709-capa.pdf
- Autoridade Nacional de Proteção de Dados: https://www.gov.br/anpd/pt-br

## Limitações

- O sistema usa mensagens simuladas.
- O modelo de aprendizado de máquina é simples (Naive Bayes) e depende da qualidade e do tamanho da base; com poucos exemplos pode generalizar mal.
- Pode haver falsos positivos e falsos negativos.
- Não há integração real com jogos online.
- O sistema não identifica automaticamente a idade real dos usuários.
- A ferramenta não substitui supervisão humana, moderação profissional, apoio psicológico, orientação jurídica ou denúncia às autoridades.

## Próximos passos

- [x] Criar base rotulada simulada (`data/simulated_messages.json`).
- [x] Criar testes automatizados (`backend/test_analyzer.py`).
- [x] Criar avaliação com métricas (`backend/evaluate.py`).
- [x] Treinar um classificador de aprendizado de máquina que melhora com as correções humanas (`backend/classifier.py`).
- [x] Notificações em tempo real (SSE) e Web Push para responsáveis.
- [ ] Ampliar a base rotulada com mais exemplos revisados.
- [ ] Evoluir o modelo para scikit-learn, spaCy ou transformers usando a base atual como ponto de partida.
- [ ] Adicionar autenticação e perfis de responsáveis.
- [ ] Trocar JSON local por banco de dados.
- [ ] Implementar exportação de relatórios.
