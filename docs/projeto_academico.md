# Guardião Gamer - Projeto acadêmico

## 1. Tema

Aplicação de controle parental e segurança infantil em jogos online, com foco na identificação de mensagens e padrões de comunicação potencialmente associados a assédio, grooming, golpes, solicitação de dados pessoais e tentativa de migração da conversa para fora da plataforma do jogo.

## 2. Contexto do problema

Jogos online frequentemente oferecem chat por texto ou voz entre pessoas desconhecidas. Esse ambiente pode aproximar crianças de adultos mal-intencionados, especialmente quando a interação envolve criação de confiança, insistência, segredo, recompensas virtuais, pedido de contato externo ou solicitação de informações pessoais.

O Guardião Gamer é proposto como um protótipo acadêmico para analisar conversas simuladas e gerar alertas para pais, responsáveis e moderadores.

## 3. Público-alvo

- Pais e responsáveis.
- Moderadores de plataformas de jogos online.
- Pesquisadores e estudantes interessados em segurança infantil, IA aplicada e controle parental.

## 4. Objetivo geral

Desenvolver uma aplicação de controle parental que utilize conceitos de Inteligência Artificial, Machine Learning e Processamento de Linguagem Natural para identificar padrões de risco em mensagens trocadas entre usuários adultos/desconhecidos e usuários crianças, alertando responsáveis e apoiando o bloqueio de mensagens nocivas.

## 5. Objetivos específicos

1. Levantar dados sobre riscos em chats de jogos online.
2. Identificar padrões de linguagem associados a grooming, assédio, golpes e solicitação de dados pessoais.
3. Criar um modelo inicial de análise de mensagens usando técnicas de NLP.
4. Implementar um sistema de classificação de risco das mensagens.
5. Gerar alertas para pais, responsáveis ou moderadores.
6. Criar uma interface simples para visualização dos alertas.
7. Definir medidas de privacidade e proteção dos dados das crianças.

## 6. Metodologia

### Pesquisa bibliográfica

Realizar revisão sobre segurança infantil online, grooming, controle parental, moderação de conteúdo, proteção de dados, privacidade infantil e limitações de sistemas automatizados de IA. A pesquisa deve considerar materiais acadêmicos, documentos de organizações de proteção infantil, recomendações de plataformas digitais e legislação aplicável.

### Coleta simulada de dados

O projeto não utiliza dados reais de crianças. A base inicial deve conter mensagens fictícias, criadas apenas para representar situações seguras, suspeitas e perigosas. Exemplos:

- Mensagens seguras: convite para jogar em equipe, elogio ao desempenho no jogo.
- Mensagens suspeitas: pedido de contato externo, perguntas sobre escola ou endereço.
- Mensagens perigosas: pedido de segredo, incentivo para apagar conversa, tentativa de obter senha ou código.

### Organização e rotulagem

Cada mensagem simulada deve receber um rótulo: segura, suspeita ou perigosa. Também podem ser registradas categorias de risco, como dados pessoais, contato fora da plataforma, sigilo, recompensa, pedido de imagem, insistência ou golpe.

### Treinamento ou uso de modelo de NLP

Nesta versão inicial, o sistema usa um classificador por regras e palavras-chave. Em versões futuras, a base rotulada pode ser usada para treinar modelos com scikit-learn, spaCy ou transformers. O classificador deve continuar explicável, mostrando quais termos e categorias levaram ao alerta.

### Testes

Os testes devem usar mensagens simuladas. O objetivo é avaliar se o sistema:

- Classifica mensagens seguras como baixo risco.
- Identifica pedidos de contato externo como risco médio ou alto.
- Identifica segredo, isolamento, pedido de fotos, senha ou dados pessoais como risco alto.
- Aponta termos suspeitos para facilitar a revisão humana.

### Avaliação dos resultados

Usar métricas como acurácia, precisão, revocação e matriz de confusão quando houver uma base rotulada maior. Para segurança infantil, falsos negativos são especialmente críticos, pois uma mensagem perigosa não identificada pode representar risco real.

### Ajustes

Revisar falsos positivos e falsos negativos, ajustar pesos das regras, ampliar exemplos simulados e validar recomendações com especialistas de segurança, educação, psicologia e direito digital.

## 7. Etapas de desenvolvimento tecnológico

1. Levantamento de requisitos.
2. Definição das funcionalidades principais.
3. Criação da base de dados simulada.
4. Desenvolvimento do módulo de IA/NLP.
5. Desenvolvimento do backend.
6. Desenvolvimento da interface dos responsáveis.
7. Implementação do sistema de alertas.
8. Testes e validação.
9. Documentação final.

## 8. Requisitos funcionais

- Cadastrar criança e responsável fictícios.
- Registrar conversas simuladas.
- Analisar automaticamente mensagens.
- Classificar risco como baixo, médio ou alto.
- Destacar palavras ou frases suspeitas.
- Manter histórico de alertas.
- Exibir painel simples para responsáveis.
- Sugerir bloqueio ou retenção de mensagens perigosas.
- Gerar relatório com data, usuário, mensagem e nível de risco.

## 9. Requisitos não funcionais

- Interface simples e compreensível.
- Classificação explicável.
- Execução local para fins acadêmicos.
- Armazenamento apenas de dados simulados.
- Arquitetura preparada para evoluir para modelos de ML.
- Priorização de privacidade, minimização de dados e revisão humana.

## 10. Arquitetura proposta

- Frontend: HTML, CSS e JavaScript.
- Backend: Python com Flask.
- IA/NLP inicial: normalização de texto, busca por padrões e pontuação por categoria.
- Armazenamento: arquivo JSON local para facilitar demonstrações.

Fluxo:

1. O responsável cadastra uma criança fictícia.
2. Uma mensagem simulada é registrada.
3. O backend normaliza o texto e aplica regras de risco.
4. O sistema calcula pontuação de 0 a 100.
5. A mensagem recebe nível baixo, médio ou alto.
6. Alertas são exibidos no painel quando o risco é médio ou alto.
7. A interface destaca termos suspeitos e mostra recomendação de ação.

## 11. Privacidade, LGPD e ética

Este projeto é apenas acadêmico e deve usar somente dados simulados. Em uma aplicação real, seria necessário:

- Obter consentimento apropriado dos responsáveis.
- Tratar dados de crianças e adolescentes com prioridade ao melhor interesse da criança.
- Coletar apenas os dados estritamente necessários.
- Informar finalidade, forma de tratamento, prazo de retenção e responsáveis pelo tratamento.
- Proteger dados com controles de acesso, criptografia, auditoria e descarte seguro.
- Permitir revisão humana das decisões automatizadas.
- Evitar vigilância excessiva e uso incompatível com a finalidade de proteção.
- Consultar profissionais jurídicos para adequação à LGPD e normas aplicáveis.

## 12. Limitações

- O classificador inicial é baseado em regras e pode gerar falsos positivos e falsos negativos.
- O sistema analisa texto, não áudio real.
- O protótipo não se integra a jogos online.
- Não identifica idade real do remetente.
- Não substitui supervisão humana, moderação profissional ou denúncia às autoridades competentes.
- Palavras-chave podem ser contornadas por abreviações, gírias ou linguagem indireta.

## 13. Possíveis evoluções

- Treinar modelo supervisionado com base rotulada e anonimizada.
- Integrar detecção contextual por sequência de mensagens.
- Adicionar análise de sentimento e intenção.
- Implementar autenticação de responsáveis.
- Usar banco de dados relacional.
- Criar painel para moderadores.
- Adicionar exportação de relatórios.
- Incluir canal de denúncia e guia de orientação para responsáveis.
