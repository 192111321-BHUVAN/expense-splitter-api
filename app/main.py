from fastapi import FastAPI

from . import models
from .database import engine
from .routers import auth, expenses, groups

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Expense Splitter API",
    description="Track shared expenses in groups and find out who owes whom.",
    version="1.0.0",
)

app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(expenses.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Expense Splitter API is running"}
