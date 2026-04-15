"""
Script para criar todas as tabelas no banco de dados.
Execute uma vez para inicializar o banco.

  python create_tables.py
"""
import sys
import os

# Garante que o diretório backend está no path
sys.path.insert(0, os.path.dirname(__file__))

from app.db.database import engine, Base
from app.models import *  # importa todos os models para o Base conhecê-los


def create_all_tables():
    print("Criando tabelas no banco de dados...")
    Base.metadata.create_all(bind=engine)
    print("Tabelas criadas com sucesso!")

    # Lista as tabelas criadas
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTabelas no banco ({len(tables)}):")
    for t in sorted(tables):
        print(f"  [OK] {t}")


if __name__ == "__main__":
    create_all_tables()
