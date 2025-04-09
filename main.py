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
from fastapi.templating import Jinja2Templates
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
templates = Jinja2Templates(directory=".") 

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

@app.get("/motd", response_class=HTMLResponse)
async def get_motd(request: Request, session: SessionDep):
    try:
        motds = session.exec(select(MOTD)).all()
        if not motds:
            return templates.TemplateResponse("motd.html", {"request": request, "motd": "Belum ada message of the day.", "creator": "", "created_at": ""})
        selected = random.choice(motds)
        if hasattr(selected, "_mapping") and hasattr(selected, "__getitem__"):
            motd_obj = selected[0]
        else:
            motd_obj = selected
        
        return templates.TemplateResponse("motd.html", {"request": request, "motd": motd_obj.motd, "creator": motd_obj.creator, "created_at": str(motd_obj.created_at)})
    except Exception as e:
        print(f"Error in get_motd: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"motd": "Error retrieving message of the day", "error": str(e)}
        )
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