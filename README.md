### Instalacja:

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\requirements.txt
```

### Uruchomienie:

```
python.exe main.py
```

### Połączenie z bazą danych:

Umieść w folderze plik .env - przykładowa zawartość:

```
DATABASE_URL=postgresql+psycopg2://etl_user:etlProjekt008@localhost:5432/etl
```

gdzie `etl_user` - nazwa użytkownika, `etlProjekt008` - hasło użytkownika, `etl` - nazwa bazy.

#### Tworzenie użytkownika przez CLI:

```
CREATE USER etl_user WITH PASSWORD 'etlProjekt008';
GRANT CONNECT ON DATABASE etl TO etl_user;
\c etl
GRANT USAGE ON SCHEMA public TO etl_user;
GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA public TO etl_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO etl_user;
```