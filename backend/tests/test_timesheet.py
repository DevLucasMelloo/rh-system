"""
Testes do módulo de controle de ponto.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, time
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models import *
from app.utils.timesheet_calc import (
    expected_minutes, calc_worked_minutes,
    calc_overtime_minutes, calc_late_minutes,
    calc_bank_delta, format_minutes,
)
from app.schemas.company import CompanyCreate
from app.schemas.user import UserCreate
from app.schemas.employee import EmployeeCreate
from app.schemas.timesheet import TimesheetEntryCreate, TimesheetEntryUpdate
from app.services import company as company_service
from app.services import user as user_service
from app.services import employee as emp_service
from app.services import timesheet as ts_service


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def setup(db):
    company = company_service.register_company(
        db, CompanyCreate(razao_social="Teste", cnpj="11222333000181", email="a@b.com")
    )
    admin = user_service.create_user(
        db, UserCreate(name="Admin", email="admin@t.com", password="Senha@123", role="admin"),
        company.id, 0,
    )
    emp_data = emp_service.create_employee(
        db, EmployeeCreate(
            name="Joao CLT", cpf="529.982.247-25", role="Operador",
            salary=Decimal("2500"), admission_date=date(2023,1,1), registration_date=date(2023,1,1),
        ),
        company.id, admin.id,
    )
    return company, admin, emp_data


# ─────────────────────────────────────────────────────────────────────────────
# Testes de cálculo puro (sem banco)
# ─────────────────────────────────────────────────────────────────────────────

def test_calc_expected_minutes():
    # Segunda = 540 min (9h), Sexta = 480 min (8h), Sábado = 0
    assert expected_minutes(date(2025, 4, 14), False, 44) == 540  # Segunda
    assert expected_minutes(date(2025, 4, 18), False, 44) == 480  # Sexta
    assert expected_minutes(date(2025, 4, 19), False, 44) == 0    # Sábado
    assert expected_minutes(date(2025, 4, 20), False, 44) == 0    # Domingo
    print("[OK] Expected minutes: Seg=540, Sex=480, Sab/Dom=0")


def test_calc_expected_minutes_intern():
    # Estagiário 30h/semana → 30*60/5 = 360 min/dia
    assert expected_minutes(date(2025, 4, 14), True, 30) == 360
    print("[OK] Expected minutes estagiario (30h/semana = 360 min/dia)")


def test_calc_worked_minutes_normal():
    # Entrada 8h, almoço 12h-13h, saída 17h → 8h trabalho = 480 min
    worked = calc_worked_minutes(
        time(8, 0), time(12, 0), time(13, 0), time(17, 0)
    )
    assert worked == 480
    print("[OK] Worked minutes: 8h-17h com 1h almoço = 480 min")


def test_calc_worked_minutes_9h():
    # 8h-18h com 1h almoço = 9h = 540 min
    worked = calc_worked_minutes(
        time(8, 0), time(12, 0), time(13, 0), time(18, 0)
    )
    assert worked == 540
    print("[OK] Worked minutes: 8h-18h com 1h almoço = 540 min")


def test_calc_worked_minutes_incomplete():
    assert calc_worked_minutes(time(8, 0), None, None, None) == 0
    assert calc_worked_minutes(None, None, None, None) == 0
    print("[OK] Batidas incompletas retornam 0")


def test_overtime_threshold():
    # Trabalhou 550 min, esperado 540 → 10 min a mais → abaixo do limiar → sem hora extra
    assert calc_overtime_minutes(550, 540) == 0
    # Trabalhou 551 min → 11 min a mais → gera hora extra
    assert calc_overtime_minutes(551, 540) == 11
    # Trabalhou 600 min → 60 min a mais → hora extra
    assert calc_overtime_minutes(600, 540) == 60
    print("[OK] Threshold de hora extra: ate 10 min a mais nao gera hora extra")


def test_late_tolerance():
    # Trabalhou 536 min, esperado 540 → 4 min a menos → dentro da tolerância → sem atraso
    assert calc_late_minutes(536, 540) == 0
    # Trabalhou 534 min → 6 min a menos → atraso
    assert calc_late_minutes(534, 540) == 6
    # Trabalhou 480 min, esperado 540 → 60 min a menos → atraso
    assert calc_late_minutes(480, 540) == 60
    print("[OK] Tolerancia de 5 min: ate 5 min a menos nao conta como atraso")


def test_bank_delta_normal():
    # Trabalhou 570 min, esperado 540 → +30 no banco
    assert calc_bank_delta(570, 540, False, False, False) == 30
    # Trabalhou 510 min, esperado 540 → -30 no banco
    assert calc_bank_delta(510, 540, False, False, False) == -30
    print("[OK] Bank delta: diferenca entre trabalhado e esperado")


def test_bank_delta_absence():
    # Falta → desconta o dia completo
    assert calc_bank_delta(0, 540, True, False, False) == -540
    print("[OK] Falta desconta o dia completo do banco")


def test_bank_delta_medical_and_annulled():
    # Atestado e anulado → zero impacto
    assert calc_bank_delta(0, 540, False, True, False) == 0
    assert calc_bank_delta(0, 540, False, False, True) == 0
    print("[OK] Atestado e dia anulado nao impactam banco de horas")


def test_format_minutes():
    assert format_minutes(150) == "+2h30"
    assert format_minutes(-75) == "-1h15"
    assert format_minutes(0) == "+0h00"
    assert format_minutes(60) == "+1h00"
    print("[OK] Formatacao de minutos para horas")


# ─────────────────────────────────────────────────────────────────────────────
# Testes de integração (com banco em memória)
# ─────────────────────────────────────────────────────────────────────────────

def test_registrar_ponto_dia_util():
    db = make_db()
    company, admin, emp = setup(db)

    # Segunda-feira, trabalhou 9h25 (565 min trabalhados) → 25 min além do limiar → 25 min extra
    entry = ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(
            work_date=date(2025, 4, 14),  # Segunda
            entry_time=time(8, 0),
            lunch_out_time=time(12, 0),
            lunch_in_time=time(13, 0),
            exit_time=time(18, 25),
        ),
        company.id, admin.id,
    )
    assert entry.worked_minutes == 565
    assert entry.overtime_minutes == 25   # 565 - 540 = 25 (acima do limiar de 10)
    assert entry.late_minutes == 0
    print("[OK] Registrar ponto: hora extra calculada corretamente")


def test_banco_de_horas_acumulado():
    db = make_db()
    company, admin, emp = setup(db)

    # Dia 1 (Seg): +30 min
    ts_service.register_entry(db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,14), entry_time=time(8,0),
            lunch_out_time=time(12,0), lunch_in_time=time(13,0), exit_time=time(18,30)),
        company.id, admin.id)

    # Dia 2 (Ter): -60 min (saiu mais cedo)
    ts_service.register_entry(db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,15), entry_time=time(8,0),
            lunch_out_time=time(12,0), lunch_in_time=time(13,0), exit_time=time(17,0)),
        company.id, admin.id)

    bank = ts_service.get_hour_bank(db, emp["id"], company.id)
    # +30 do dia 1 + (-60) do dia 2 = -30
    assert bank["balance_minutes"] == -30
    assert bank["balance_hours"] == "-0h30"
    print("[OK] Banco de horas acumulado: +30 - 60 = -30 min")


def test_registrar_falta():
    db = make_db()
    company, admin, emp = setup(db)

    entry = ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,14), is_absence=True),
        company.id, admin.id,
    )
    assert entry.is_absence is True
    assert entry.worked_minutes == 0

    bank = ts_service.get_hour_bank(db, emp["id"], company.id)
    assert bank["balance_minutes"] == -540  # desconta 9h (segunda-feira)
    print("[OK] Falta registrada e banco descontado")


def test_atestado_nao_desconta_banco():
    db = make_db()
    company, admin, emp = setup(db)

    ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(
            work_date=date(2025,4,14),
            is_medical_certificate=True,
            justification="Atestado médico 1 dia",
        ),
        company.id, admin.id,
    )
    bank = ts_service.get_hour_bank(db, emp["id"], company.id)
    assert bank["balance_minutes"] == 0  # atestado não desconta
    print("[OK] Atestado medico nao desconta banco de horas")


def test_anular_dia_reverte_banco():
    db = make_db()
    company, admin, emp = setup(db)

    # Registra falta (desconta -540)
    entry = ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,14), is_absence=True),
        company.id, admin.id,
    )
    bank_antes = ts_service.get_hour_bank(db, emp["id"], company.id)
    assert bank_antes["balance_minutes"] == -540

    # Anula o dia (atestado aprovado)
    ts_service.annul_entry(db, entry.id, "Atestado apresentado", company.id, admin.id)

    bank_depois = ts_service.get_hour_bank(db, emp["id"], company.id)
    assert bank_depois["balance_minutes"] == 0  # reverteu o desconto
    print("[OK] Anular dia reverte impacto no banco de horas")


def test_duplicata_no_mesmo_dia():
    from fastapi import HTTPException
    db = make_db()
    company, admin, emp = setup(db)

    ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,14), is_absence=True),
        company.id, admin.id,
    )
    try:
        ts_service.register_entry(
            db, emp["id"],
            TimesheetEntryCreate(work_date=date(2025,4,14), is_absence=True),
            company.id, admin.id,
        )
        assert False
    except HTTPException as e:
        assert e.status_code == 409
    print("[OK] Registro duplicado no mesmo dia retorna 409")


def test_sexta_com_8h():
    db = make_db()
    company, admin, emp = setup(db)

    # Sexta: trabalhou exatamente 8h → sem extra nem atraso
    entry = ts_service.register_entry(
        db, emp["id"],
        TimesheetEntryCreate(
            work_date=date(2025, 4, 18),  # Sexta
            entry_time=time(8, 0),
            lunch_out_time=time(12, 0),
            lunch_in_time=time(13, 0),
            exit_time=time(17, 0),
        ),
        company.id, admin.id,
    )
    assert entry.worked_minutes == 480   # 8h
    assert entry.overtime_minutes == 0
    assert entry.late_minutes == 0
    print("[OK] Sexta: 8h exatas, sem extra nem atraso")


def test_relatorio_mensal():
    db = make_db()
    company, admin, emp = setup(db)

    # Semana com falta, atestado e 2 dias normais
    ts_service.register_entry(db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,14),
            entry_time=time(8,0), lunch_out_time=time(12,0), lunch_in_time=time(13,0), exit_time=time(18,0)),
        company.id, admin.id)

    ts_service.register_entry(db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,15), is_absence=True),
        company.id, admin.id)

    ts_service.register_entry(db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,16),
            is_medical_certificate=True, justification="Consulta médica"),
        company.id, admin.id)

    ts_service.register_entry(db, emp["id"],
        TimesheetEntryCreate(work_date=date(2025,4,17),
            entry_time=time(8,0), lunch_out_time=time(12,0), lunch_in_time=time(13,0), exit_time=time(17,0)),
        company.id, admin.id)

    report = ts_service.get_monthly_report(db, emp["id"], 4, 2025, company.id)

    assert report["total_absences"] == 1
    assert report["total_medical_certificates"] == 1
    assert len(report["entries"]) == 4
    assert report["employee_name"] == "Joao CLT"
    print("[OK] Relatorio mensal com faltas, atestados e dias normais")


if __name__ == "__main__":
    print("=== Testando controle de ponto ===\n")
    # Cálculos puros
    test_calc_expected_minutes()
    test_calc_expected_minutes_intern()
    test_calc_worked_minutes_normal()
    test_calc_worked_minutes_9h()
    test_calc_worked_minutes_incomplete()
    test_overtime_threshold()
    test_late_tolerance()
    test_bank_delta_normal()
    test_bank_delta_absence()
    test_bank_delta_medical_and_annulled()
    test_format_minutes()
    # Integração
    test_registrar_ponto_dia_util()
    test_banco_de_horas_acumulado()
    test_registrar_falta()
    test_atestado_nao_desconta_banco()
    test_anular_dia_reverte_banco()
    test_duplicata_no_mesmo_dia()
    test_sexta_com_8h()
    test_relatorio_mensal()
    print("\nTodos os testes passaram!")
