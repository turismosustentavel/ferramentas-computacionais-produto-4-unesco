# dados/

Pasta de dados padrão. Nada aqui é versionado além deste arquivo.

Os scripts procuram os dados abaixo de uma raiz, lida da variável de ambiente
`P4_DADOS`. Sem ela, a raiz é esta pasta. A árvore abaixo da raiz reproduz a pasta
do convênio:

```
<P4_DADOS>/
├── Levantamentos e Análises/
│   └── Produto 4/                      acervo: bases oficiais, campo, telemetria
│       ├── 01_Bases_Secundarias_Oficiais/Shapes/
│       ├── 03_Pesquisa_de_Campo_Primaria/
│       ├── 04_Entrevistas_e_Qualitativo/
│       ├── 05_Telemetria_e_BigData/
│       ├── 06_Dados_Processados_Pipeline/
│       ├── 08_Infraestrutura_e_Turismo_Nautico/
│       └── 09_Base_Socioeconomica_Municipal/
└── Entregas/
    └── Produto 4/
        ├── Entrega 4.3/                material de campo por município
        └── produção/                   bases tratadas do diagnóstico regional
            ├── 01_… a 18_…             uma pasta por tema
            ├── Seleção dos pontos para aferição/
            └── Caderno de informações por município/
                ├── 00_Gestao/          relatórios de auditoria
                └── 02_Dados_Municipais/ saídas por município e cache
```

Quem tem acesso à pasta do convênio aponta `P4_DADOS` para ela e roda os scripts
sem copiar nada. Quem vai montar os dados do zero cria essa árvore aqui e coloca
cada arquivo onde o [mapa de dados](../docs/mapa_de_dados.md) indica.
