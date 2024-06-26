# Copyright (c) EGOGE - All Rights Reserved.
# This software may be used and distributed according to the terms of the Apache-2.0 license.
from typing import List
from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, SmallInteger
from sqlalchemy.orm import relationship
from .study_stream_school_type import StudyStreamSchoolType
from .study_stream_note import Base

"""
Stores the information about a class and documents associated with it.
"""
class StudyStreamSchool(Base):
    __tablename__ = 'study_stream_school'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    school_type = Column(SmallInteger, nullable=False)
    start_date = Column(TIMESTAMP, nullable=False, default=datetime.now)
    finish_date = Column(TIMESTAMP)

    subjects = relationship('StudyStreamSubject', backref='school', cascade='all, delete-orphan', lazy='joined')  

    def __init__(self, school_name: str, school_type: StudyStreamSchoolType):
        self.name = school_name
        self.school_type = school_type.value  # Store the enum value

    @property
    def school_type_enum(self):
        return StudyStreamSchoolType(self.school_type)

    # CRUD operations
    @staticmethod
    def create(session, school):
        session.add(school)
        session.commit()
        return school

    @staticmethod
    def read(session, school_id):
        return session.query(StudyStreamSchool).filter_by(id=school_id).first()
   
    def update(self, session, **update_values):
        for key, value in update_values.items():
            setattr(self, key, value)
        session.commit()

    @staticmethod
    def delete(session, object_id):
        school = session.query(StudyStreamSchool).filter_by(id=object_id).first()
        if school:
            session.delete(school)
            session.commit()
