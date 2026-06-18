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

Projekt zawiera proces ETL w pliku `etl_products.py`.

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
python etl_products.py --dry-run
```

Uruchomienie pelnego importu:

```
python etl_products.py
```

### Scenariusz ETL: import klientow z CSV lub JSON

Projekt zawiera proces ETL w pliku `etl_customers.py`.

- Extract: odczyt danych z `data/customers_feed.csv` albo pliku JSON o tych samych polach.
- Transform: oczyszczenie imienia, nazwiska, emaila, telefonu i danych adresowych, konwersja telefonu na liczbe oraz dopasowanie miasta do slownika `data/polskie_miejscowosci.json`.
- Validation: rekordy, ktorych nie da sie sparsowac albo ktorych miasta nie pasuja do slownika, sa odrzucane do raportu `data/customers_rejected.csv`.
- Load: wyszukanie lub utworzenie adresu w tabeli `adrklienta`, a nastepnie dodanie albo aktualizacja klienta w tabeli `klient` po adresie email.

Plik wejsciowy:

```
imie,nazwisko,email,telefon,miejscowosck,ulica,kodpocztowyk,krajk
Liliana,Wisniewska,lilwis@test.pl,821885951,Biala Podlaska,Powstancow Wielkopolskich 34,60-009,Polska
```

Scenariusz jest dostepny w dashboardzie po wybraniu `Customers Import`.

Slownik miejscowosci pochodzi z repozytorium `jjbartek/polskie-miejscowosci`: https://github.com/jjbartek/polskie-miejscowosci. Plik zrodlowy zawiera miejscowosci z PRNG w formacie JSON z polami `Name`, `Type`, `Province`, `District` i `Commune`.

Algorytm dopasowania:

- Exact/normalized match: ignoruje wielkosc liter, polskie znaki i nadmiarowe spacje, np. `Krakow` -> `Kraków`.
- Fuzzy auto match: jesli najlepszy kandydat jest wystarczajaco podobny i jednoznacznie lepszy od kolejnego, ETL poprawia miasto automatycznie.
- Uncertain match: jesli istnieja podobne kandydaty, ale dopasowanie nie jest jednoznaczne, dashboard pokazuje sugestie i czeka na decyzje uzytkownika. Do czasu decyzji import klientow nie zapisuje zmian do bazy.
- Reject: jesli nie ma sensownego kandydata, rekord trafia do raportu odrzuconych rekordow.

Dashboard pokazuje liczbe automatycznych korekt miast, tabele korekt oraz osobny formularz dla niepewnych dopasowan. W formularzu mozna zaakceptowac jedna z sugestii slownika albo odrzucic rekord.

### Scenariusz ETL: aktualizacja stanow magazynowych

Projekt zawiera proces ETL w pliku `etl_inventory.py`.

- Extract: odczyt korekt z pierwszego arkusza pliku `data/inventory_updates_feed.xlsx`.
- Transform: normalizacja nazw produktu i producenta, walidacja liczbowej zmiany stanu oraz agregacja wielu korekt tego samego produktu z jednego pliku.
- Validation: sprawdzenie w bazie, czy produkt istnieje i czy korekta nie sprowadzi stanu magazynowego ponizej zera.
- Rejects: zapis odrzuconych rekordow do `data/inventory_updates_rejected.csv`.
- Load: aktualizacja pola `stanmagazynowy` w tabeli `produkt`.

Plik wejsciowy `.xlsx` powinien zawierac kolumny:

| nazwa | producent | zmiana_stanu | powod |
| --- | --- | ---: | --- |
| Laptop biznesowy | Lenovo | 5 | dostawa |
| Monitor 27 cali | Dell | -2 | sprzedaz |

Sprawdzenie scenariusza bez zapisu do bazy:

```
python etl_inventory.py --dry-run
```

Uruchomienie pelnej aktualizacji:

```
python etl_inventory.py
```
