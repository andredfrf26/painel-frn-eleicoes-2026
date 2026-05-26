# Painel Processual Eleicoes 2026

Dashboard em Streamlit para acompanhamento processual.

## Arquivos principais

- `app.py`: aplicacao Streamlit.
- `requirements.txt`: bibliotecas necessarias.
- `assets/`: logo e estilos.
- `data/`: CSV local usado como fallback.

## Fonte Google Sheets

O app le a variavel `GOOGLE_SHEET_URL` em `st.secrets`.

No Streamlit Community Cloud, configure em **Settings > Secrets**:

```toml
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1j-7TIKWzKt9IgZza2l5AwW_93sempqfnUdC3hAqcnTk/edit?gid=0#gid=0"
```

Se a planilha nao estiver publica para leitura, o app usa o CSV local como fallback.

## Deploy no Streamlit Community Cloud

1. Suba este projeto para um repositorio no GitHub.
2. Acesse `https://share.streamlit.io`.
3. Clique em **Create app**.
4. Selecione o repositorio, a branch `main` e o arquivo `app.py`.
5. Configure os secrets, se for usar Google Sheets.
6. Clique em **Deploy**.
