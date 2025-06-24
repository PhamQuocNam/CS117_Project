from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class History(Base):
    __tablename__ = "history" 
    
    id = Column(Integer, primary_key=True, index=True)
    number_plate = Column(String, index=True)
    position = Column(String, index=True)
    status = Column(String, index=True)
    time = Column(DateTime, index=True)  
