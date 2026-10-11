# Expense Splitter API

A REST API for splitting shared expenses in groups and finding out who owes whom.
Built with FastAPI, SQLAlchemy, SQLite and JWT authentication.

## Features

- Register and log in with JWT authentication
- Create groups and add members
- Add expenses split equally among all members or a chosen few
- Money stored as integer paise to avoid floating-point errors
- Equal split handles remainders (Rs 1.00 among 3 people becomes 0.34, 0.33, 0.33)
- Balances per member and a settle-up endpoint that minimises the number of payments
- Unit tests for the logic and API tests for every endpoint

## Run locally

1. Create and activate a virtual environment

   ```bash
   python -m venv venv
   venv\Scripts\activate          # Windows
   source venv/bin/activate       # Mac / Linux
   ```

2. Install the packages

   ```bash
   pip install -r requirements.txt
   ```

3. Start the server

   ```bash
   uvicorn app.main:app --reload
   ```

4. Open http://127.0.0.1:8000/docs to try the API in Swagger.

The SQLite database file `splitter.db` is created automatically on first run.

Optional: set a real secret for signing tokens before running.

```bash
set SECRET_KEY=some-long-random-string          # Windows (cmd)
export SECRET_KEY=some-long-random-string       # Mac / Linux
```

## Run the tests

```bash
python -m pytest
```

## Endpoints

| Method | Endpoint | What it does |
| --- | --- | --- |
| POST | /auth/register | Create a user |
| POST | /auth/login | Get a JWT access token |
| POST | /groups/ | Create a group (you become a member) |
| GET | /groups/ | List your groups |
| POST | /groups/{group_id}/members | Add a member by username |
| POST | /groups/{group_id}/expenses | Add an expense, split equally |
| GET | /groups/{group_id}/expenses | List the group's expenses |
| DELETE | /groups/{group_id}/expenses/{expense_id} | Delete an expense you added |
| GET | /groups/{group_id}/balances | Net balance per member |
| GET | /groups/{group_id}/settle | Minimal payments that settle everyone |

## Example

Alice pays Rs 3000 for a hotel and Bob pays Rs 900 for dinner, both split three ways with Charlie.

`GET /groups/1/balances` returns alice +1700, bob -400, charlie -1300.

`GET /groups/1/settle` returns two payments: charlie pays alice 1300, and bob pays alice 400.

## How the settle-up works

Each member's balance is what they paid minus what they owe. The algorithm then repeatedly
matches the person who owes the most with the person owed the most, and settles as much as
possible between them. This keeps the number of payments low.

## Project structure

```text
app/
  main.py          FastAPI app and router setup
  database.py      SQLAlchemy engine and session
  models.py        Database tables
  schemas.py       Request and response models
  security.py      Password hashing and JWT helpers
  services.py      Splitting, balances and settle-up logic
  routers/         auth, groups and expenses endpoints
tests/             unit tests and API tests
```
