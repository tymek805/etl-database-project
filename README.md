### Instalacja:

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\requirements.txt
```

### Uruchomienie:

```
streamlit run dashboard.py
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
GRANT INSERT, SELECT, UPDATE ON ALL TABLES IN SCHEMA public TO etl_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO etl_user;
```

### Scenariusz ETL: zaawansowany import produktow z CSV

Projekt zawiera proces ETL w pliku `etl_products_csv.py`.

- Extract: odczyt danych z `data/products_feed.csv`.
- Transform: normalizacja tekstu, walidacja pol liczbowych, pominiecie produktow nieaktywnych, odrzucenie blednych rekordow oraz deduplikacja produktow z tego samego pliku.
- Enrichment: wyliczenie wartosci magazynu jako `cena * stanmagazynowy`.
- Rejects: zapis odrzuconych rekordow do `data/products_rejected.csv`.
- Load: automatyczne utworzenie brakujacych kategorii i producentow, a nastepnie upsert produktow do tabeli `produkt`.

Plik wejsciowy uzywa nazw kategorii i producentow zamiast surowych identyfikatorow:

```
nazwa,cena,stanmagazynowy,kategoria,producent,kraj_producenta,aktywny
Laptop biznesowy,4299,12,Elektronika,Lenovo,Chiny,tak
```

Sprawdzenie scenariusza bez zapisu do bazy:

```
python etl_products_csv.py --dry-run
```

Uruchomienie pelnego importu:

```
python etl_products_csv.py
```
