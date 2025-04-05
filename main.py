import secrets
import base64
import pyotp
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from sqlmodel import create_engine, Session, SQLModel, select
from typing import Annotated
from model import MOTD, MOTDBase
from datetime import datetime
import random

# SQLite Database
sqlite_file_name = "motd.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"
connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

# FastAPI
app = FastAPI(docs_url=None, redoc_url=None)
security = HTTPBasic()

# Users - lengkapi dengan userid dan shared_secret yang sesuai
users = {
    "sister": "ii2210_sister",
    "hakimkaarzaqiel": "punya_hakimkaarzaqiel"
} 

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.get("/motd")
async def get_motd(session: SessionDep):
    statement = select(MOTD)
    results = session.exec(statement).all()
    
    if not results:
        return "message : tidak ada message of the day"
    
    random_message = random.choice(results)
    return f"Message of the day: {random_message.motd} Created At: {random_message.created_at} Creator: {random_message.creator}"

@app.post("/motd")
async def post_motd(
    message: MOTDBase, 
    session: SessionDep, 
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
    request: Request
):
    current_password_bytes = credentials.password.encode("utf8")
    valid_username, valid_password = False, False

    try:
        if credentials.username in users:
            valid_username = True
            s = base64.b32encode(users[credentials.username].encode("utf-8")).decode("utf-8")
            totp = pyotp.TOTP(s=s, digest="SHA256", digits=8)
            valid_password = secrets.compare_digest(current_password_bytes, totp.now().encode("utf8"))

            if valid_password and valid_username:
                db_motd = MOTD(
                    motd=message.motd,
                    creator=credentials.username
                )
                session.add(db_motd)
                session.commit()
                session.refresh(db_motd)
                
                return f"Pesan Berhasil ditambahkan ke database, Message: {db_motd.motd} Creator: {db_motd.creator} Created At: {db_motd.created_at}"
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid userid or password.",
                    headers={"WWW-Authenticate": "Basic"}
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid userid or password.",
                headers={"WWW-Authenticate": "Basic"}
            )
    except HTTPException as e:
        raise e

if __name__ == "__main__":
    create_db_and_tables()
    import uvicorn
    uvicorn.run(app, host="13.64.130.210", port=17787)