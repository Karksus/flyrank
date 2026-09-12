from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, status
from sqlmodel import Field, Session, SQLModel, create_engine, select


# --- Database Setup ---
sqlite_file_name = "tasks.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})


class Task(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    done: bool = False


def create_db_and_seed():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Check if database is empty
        statement = select(Task)
        results = session.exec(statement).first()
        if not results:
            initial_tasks = [
                Task(
                    title="Learn about FastAPI path parameters", done=True
                ),
                Task(
                    title="Learn about FastAPI query parameters", done=False
                ),
                Task(title="Learn about FastAPI request body", done=False),
            ]
            session.add_all(initial_tasks)
            session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_seed()
    yield


app = FastAPI(lifespan=lifespan)


# --- Schemas ---
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


# --- Endpoints ---
@app.get("/")
def root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks", "/tasks/{task_id}"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks():
    with Session(engine) as session:
        return session.exec(select(Task)).all()


@app.get("/tasks/{task_id}")
def get_task_id(task_id: int, response: Response):
    with Session(engine) as session:
        task = session.get(Task, task_id)

        if task is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"error": f"Task {task_id} not found"}

        return task


@app.post("/tasks")
def create_task(task_in: TaskCreate, response: Response):
    if not task_in.title or not task_in.title.strip():
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"error": "Title is required and cannot be empty"}

    with Session(engine) as session:
        new_task = Task(title=task_in.title.strip(), done=False)
        session.add(new_task)
        session.commit()
        session.refresh(new_task)

        response.status_code = status.HTTP_201_CREATED
        return new_task


@app.put("/tasks/{task_id}")
def update_task(task_id: int, task_in: TaskUpdate, response: Response):
    with Session(engine) as session:
        task = session.get(Task, task_id)

        if task is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"error": f"Task {task_id} not found"}

        if task_in.title is None and task_in.done is None:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "error": "Request body must contain 'title' and/or 'done'"
            }

        if task_in.title is not None:
            if not task_in.title.strip():
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {"error": "Title cannot be empty"}
            task.title = task_in.title.strip()

        if task_in.done is not None:
            task.done = task_in.done

        session.add(task)
        session.commit()
        session.refresh(task)

        return task


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, response: Response):
    with Session(engine) as session:
        task = session.get(Task, task_id)

        if task is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return {"error": f"Task {task_id} not found"}

        session.delete(task)
        session.commit()

        return Response(status_code=status.HTTP_204_NO_CONTENT)