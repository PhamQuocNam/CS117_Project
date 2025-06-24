from sqlalchemy.orm import Session
from models import History
from datetime import datetime  # You need this

def get_user(db: Session, id: int):
    return db.query(History).filter(History.id == id).first()

def create_history(db: Session, number_plate: str, position: str, status: str, time: datetime):
    history = History(
        number_plate=number_plate,
        position=position,
        status=status,
        time=time
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
