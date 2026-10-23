# Modelagem de dados — Gerenciamento de Projetos com IA

> **Estado atual (outubro/2026):** banco operacional **PostgreSQL relacional**, hospedado no **Supabase**. Este documento representa as tabelas e relacionamentos verificados no ambiente; não é um script de recriação do banco. Não contém dados pessoais, chaves ou credenciais.

## 1. Diagrama entidade-relacionamento (OLTP)

```mermaid
erDiagram
    PROJETOS ||--o{ PENDENCIAS : possui
    PROJETOS ||--o{ GARGALOS : registra
    PROJETOS ||--o{ ATAS : referencia
    PROJETOS ||--o{ HISTORICO : registra
    PROJETOS ||--o{ SUGESTOES_ATAS : recebe
    PROJETOS ||--o{ PROJETO_ACESSOS : autoriza
    PERFIS_USUARIOS ||--o{ PROJETO_ACESSOS : participa
    PROJETOS ||--o{ PROJETO_SQUADS : vincula
    SQUADS ||--o{ PROJETO_SQUADS : vincula
    SQUADS ||--o{ SQUAD_MEMBROS : possui
    PERFIS_USUARIOS ||--o{ SQUAD_MEMBROS : integra
    AUTH_USERS ||--o| PERFIS_USUARIOS : autentica

    PROJETOS {
        bigint id PK
        text nome UK
        text responsavel
        date inicio
        date prazo
        text status
        text farol
        timestamptz atualizado_em
    }
    PENDENCIAS {
        bigint id PK
        bigint projeto_id FK
        text descricao
        text responsavel
        date prazo
        text status
        text origem
        text prioridade
        int progresso
    }
    GARGALOS {
        bigint id PK
        bigint projeto_id FK
        text descricao
        text impacto
        text status
    }
    ATAS {
        bigint id PK
        bigint projeto_id FK
        date data_reuniao
        text titulo
        text caminho_arquivo
    }
    HISTORICO {
        bigint id PK
        bigint projeto_id FK
        text descricao
        text origem
    }
    SUGESTOES_ATAS {
        bigint id PK
        bigint projeto_id FK
        text fonte_arquivo
        text tipo
        text chave_fonte UK
        text status
        uuid revisado_por FK
    }
    PERFIS_USUARIOS {
        uuid id PK
        uuid auth_user_id FK
        text nome
        text perfil_global
        boolean ativo
    }
    AUTH_USERS {
        uuid id PK
    }
    SQUADS {
        bigint id PK
        text nome UK
        boolean ativo
    }
    SQUAD_MEMBROS {
        bigint squad_id PK,FK
        uuid usuario_id PK,FK
        text papel
    }
    PROJETO_SQUADS {
        bigint projeto_id PK,FK
        bigint squad_id PK,FK
    }
    PROJETO_ACESSOS {
        bigint projeto_id PK,FK
        uuid usuario_id PK,FK
        text papel
    }
```

**Nota:** `auth.users` pertence ao schema gerenciado pelo Supabase Auth. `app_private.admin_allowlist` e as tabelas privadas de auditoria não são expostas como dados de domínio na API pública. A coluna `revisado_por` da fila aponta para `auth.users`.

## 2. Organização lógica

| Domínio | Tabelas | Responsabilidade |
|---|---|---|
| Portfólio | `projetos` | Identidade, responsável, datas e estado do projeto |
| Execução | `pendencias`, `gargalos` | Tarefas, prioridades, progresso, bloqueios e riscos |
| Reuniões | `atas`, `sugestoes_atas`, `historico` | Referências de atas, propostas de atualização e rastreabilidade |
| Identidade e autorização | `perfis_usuarios`, `projeto_acessos` | Perfil interno e acesso explícito por projeto |
| Colaboração | `squads`, `squad_membros`, `projeto_squads` | Relações muitos-para-muitos entre pessoas, squads e projetos |

### Regras e decisões arquiteturais

- **Chaves primárias e estrangeiras** asseguram vínculos entre projetos, tarefas, squads e usuários.
- **Tabelas associativas** resolvem relações muitos-para-muitos, evitando listas de IDs em colunas de texto.
- **Tipos**: `bigint` para entidades operacionais; `uuid` para identidade; `date` para prazos; `timestamptz` para rastreabilidade.
- **Restrições `CHECK`** limitam valores de status, prioridade, progresso e impacto.
- **`sugestoes_atas.chave_fonte` é única**, ajudando a não duplicar propostas originadas do mesmo trecho de ata.
- **RLS (Row Level Security)** habilitada nas tabelas de negócio: a consulta depende das permissões do usuário autenticado.
- **Aprovação transacional**: a função `aplicar_sugestao_ata` utiliza uma transação de banco para aplicar a alteração e registrar a decisão como uma operação indivisível.
- **As atas de demonstração são arquivos TXT públicos no GitHub**, e não registros persistidos na tabela `atas`; esta última está preparada para evolução do domínio.

## 3. Fluxo de dados

```mermaid
flowchart LR
    A["Atas fictícias (.txt) no GitHub"] --> B["Leitura e extração por regras em Python"]
    B --> C["sugestoes_atas — fila central"]
    C --> D{"Revisão humana"}
    D -->|Aprovar / ajustar| E["RPC transacional no PostgreSQL"]
    D -->|Rejeitar| F["Histórico de decisão"]
    E --> G["projetos / pendencias / gargalos"]
    G --> H["Visão executiva / indicadores"]
```

**Limite funcional:** a extração é baseada em prefixos e regras textuais; não há evidência de uso de um modelo generativo/LLM em produção. A atualização depende de aprovação, e o vínculo com a tarefa existente é selecionado pelo revisor.

## 4. Evolução proposta: camada analítica dimensional (não implementada)

Para evoluir BI sem comprometer o modelo transacional, a proposta é criar **um data mart separado** (ou schema `analytics`) com cargas controladas:

```mermaid
flowchart TB
    D1["dim_projeto"] --> F["fato_snapshot_tarefas"]
    D2["dim_data"] --> F
    D3["dim_status"] --> F
    D4["dim_prioridade"] --> F
    D1 --> F2["fato_decisoes_atas"]
    D2 --> F2
```

- **Grão de `fato_snapshot_tarefas`**: uma linha por tarefa por data de observação. Métricas: quantidade, progresso, vencimento e atraso.
- **Grão de `fato_decisoes_atas`**: uma linha por sugestão revisada. Métricas: quantidade aprovada/rejeitada, tempo de revisão e categoria.
- **Dimensões**: projeto, data, status e prioridade, com chaves substitutas quando fizer sentido.
- **Benefícios**: séries históricas, análise de SLA, tendências de atraso e relatórios Power BI.
- **Cuidados**: LGPD, minimização de dados pessoais, pseudonimização de responsáveis, acesso por perfil e retenção definida.

> A modelagem dimensional é um **roadmap de engenharia de dados**, não uma funcionalidade já disponível no aplicativo.
