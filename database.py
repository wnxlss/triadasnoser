# database.py
import datetime
from peewee import *

db = SqliteDatabase('users.db')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    user_id = BigIntegerField(primary_key=True)
    last_used = DateTimeField(default=datetime.datetime.now)
    referral_code = CharField(max_length=8, default='')
    refcount = IntegerField(default=0)
    activateduntil = DateTimeField(null=True)  # Ключевое: null=True
    
    class Meta:
        table_name = 'user'  # Или 'users' в зависимости от вашей таблицы

# Создаем таблицы
def init_database():
    db.connect()
    db.create_tables([User], safe=True)
    db.close()

# Инициализируем базу при импорте
init_database()