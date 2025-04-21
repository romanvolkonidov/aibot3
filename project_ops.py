# project_ops.py
from db import SessionLocal, User, Project, UserProject, Conversation, ProjectFile
from sqlalchemy import and_

def get_user_projects(user_id: int):
    with SessionLocal() as session:
        return session.query(Project).join(UserProject).filter(UserProject.user_id == user_id).all()

def create_project(user_id: int, name: str, context: str = ""):
    with SessionLocal() as session:
        project = Project(name=name, context=context)
        session.add(project)
        session.flush()
        
        user_project = UserProject(user_id=user_id, project_id=project.id)
        session.add(user_project)
        session.commit()
        return project

def set_current_project(user_id: int, project_id: int):
    with SessionLocal() as session:
        # Reset current project
        session.query(UserProject).filter(
            UserProject.user_id == user_id
        ).update({"is_current": False})
        
        # Set new current project
        session.query(UserProject).filter(
            and_(UserProject.user_id == user_id, UserProject.project_id == project_id)
        ).update({"is_current": True})
        session.commit()

def save_conversation(user_id: int, project_id: int, role: str, content: str):
    with SessionLocal() as session:
        conv = Conversation(
            user_id=user_id,
            project_id=project_id,
            role=role,
            content=content
        )
        session.add(conv)
        session.commit()