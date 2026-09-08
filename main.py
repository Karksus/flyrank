import os
from dotenv import load_dotenv
from fastapi import FastAPI, Response, status, Depends
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from contextlib import asynccontextmanager
from typing import Optional
from supabase import AuthError, create_client, Client

load_dotenv()

supb_url: str = os.environ.get("SUPABASE_URL")
supb_key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supb_url, supb_key)

class Tasks(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    done: bool


engine = create_engine(os.getenv('DATABASE_URL'))

def get_session():
    with Session(engine) as session:
        yield session


class TaskCreate(BaseModel):
    title: str | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None

class AuthRequest(BaseModel):
    email: str | None = None
    password: str | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server running and connected to Supabase", flush=True)
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        statement = select(Tasks)
        existing_task = session.exec(statement).first()
        
        if not existing_task:
            initial_tasks = [
                Tasks(title="Learn FastAPI Basics and Routing", done=True),
                Tasks(title="Implement Pydantic Models & Validation", done=False),
                Tasks(title="Write Complete CRUD Endpoints", done=False),
            ]
            session.add_all(initial_tasks)
            session.commit()
            
    yield
    pass

app = FastAPI(
    title="FastAPI Task Manager Toy API",
    description="A fully-featured toy CRUD application managing FastAPI learning tasks with input validation and error handling.",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

class SqlOperator:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, task_id: int) -> Optional[Tasks]:
        return self.session.get(Tasks, task_id)

    def create(self, title: str) -> Tasks:
        db_task = Tasks(title=title, done=False)
        self.session.add(db_task)
        self.session.commit()
        self.session.refresh(db_task)
        return db_task

    def update(self, task: Tasks, title: Optional[str] = None, done: Optional[bool] = None) -> Tasks:
        if title is not None:
            task.title = title.strip()
        if done is not None:
            task.done = done
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        return task

    def delete(self, task: Tasks) -> None:
        self.session.delete(task)
        self.session.commit()

class AuthOperator:
    def __init__(self, client: Client):
        self.client = client

    def signup(self, email: str, password: str):
        return self.client.auth.sign_up({"email": email, "password": password})

    def login(self, email: str, password: str):
        return self.client.auth.sign_in_with_password({"email": email, "password": password})

@app.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks(session: Session = Depends(get_session)):
    statement = select(Tasks)
    return session.exec(statement).all()


@app.get("/tasks/{task_id}")
def get_task_id(task_id: int, response: Response, session: Session = Depends(get_session)):
    db = SqlOperator(session)
    task = db.get_by_id(task_id)

    if task is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": f"Task {task_id} not found"}

    return task


@app.post("/tasks")
def create_task(task_in: TaskCreate, response: Response, session: Session = Depends(get_session)):
    if not task_in.title or not task_in.title.strip():
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Title is required and cannot be empty"}

    db = SqlOperator(session)
    new_task = db.create(task_in.title.strip())

    response.status_code = status.HTTP_201_CREATED
    return new_task

@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_in: TaskUpdate, response: Response, session: Session = Depends(get_session)):
    db = SqlOperator(session)
    task = db.get_by_id(task_id)
    
    if task is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": f"Task {task_id} not found"}
    
    if task_in.title is None and task_in.done is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Request body must contain 'title' and/or 'done'"}
    
    if task_in.title is not None and not task_in.title.strip():
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Title cannot be empty"}
        
    updated_task = db.update(task, title=task_in.title, done=task_in.done)
    return updated_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, response: Response, session: Session = Depends(get_session)):
    db = SqlOperator(session)
    task = db.get_by_id(task_id)
    
    if task is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"error": f"Task {task_id} not found"}
    
    db.delete(task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.post("/auth/signup")
def signup(auth_in: AuthRequest, response: Response):
    if not auth_in.email or not auth_in.password:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Bad Request"}

    auth = AuthOperator(supabase)
    try:
        result = auth.signup(auth_in.email.strip(), auth_in.password)
    except AuthError as err:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": str(err)}

    if result.user is None:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Bad Request"}

    response.status_code = status.HTTP_201_CREATED
    return result.user.model_dump()

@app.post("/auth/login")
def login(auth_in: AuthRequest, response: Response):
    if not auth_in.email or not auth_in.password:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Bad Request"}

    auth = AuthOperator(supabase)
    try:
        result = auth.login(auth_in.email.strip(), auth_in.password)
    except AuthError:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "Invalid login credentials"}

    if result.session is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"error": "Invalid login credentials"}

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }