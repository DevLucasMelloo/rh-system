"""
Script de seed — cria dados de teste completos no sistema RH.
Requer backend rodando em localhost:8080.
"""
import requests, random
from datetime import date, timedelta

BASE = "http://localhost:8080/api/v1"
s = requests.Session()

def gen_cpf():
    """Gera CPF com dígitos verificadores válidos."""
    n = [random.randint(0, 9) for _ in range(9)]
    r1 = sum(n[i] * (10 - i) for i in range(9)) % 11
    d1 = 0 if r1 < 2 else 11 - r1
    r2 = (sum(n[i] * (11 - i) for i in range(9)) + d1 * 2) % 11
    d2 = 0 if r2 < 2 else 11 - r2
    digits = n + [d1, d2]
    return (f'{"".join(map(str, digits[:3]))}.'
            f'{"".join(map(str, digits[3:6]))}.'
            f'{"".join(map(str, digits[6:9]))}-'
            f'{"".join(map(str, digits[9:]))}')

def login(username, password):
    r = s.post(f"{BASE}/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    token = r.json()["access_token"]
    s.headers.update({"Authorization": f"Bearer {token}"})
    print(f"Login como {username}")

def get(path, **params):
    r = s.get(f"{BASE}{path}", params=params)
    if not r.ok:
        print(f"  GET {path} -> {r.status_code}: {r.text[:200]}")
    return r.json() if r.ok else None

def post(path, body=None):
    r = s.post(f"{BASE}{path}", json=body)
    if not r.ok:
        print(f"  POST {path} -> {r.status_code}: {r.text[:300]}")
        return None
    return r.json()

def patch(path, body=None):
    r = s.patch(f"{BASE}{path}", json=body)
    if not r.ok:
        print(f"  PATCH {path} -> {r.status_code}: {r.text[:200]}")
    return r.json() if r.ok else None

EMPLOYEES = [
    {"name": "Ana Paula Ferreira",   "role": "Auxiliar Administrativo", "salary": 1800.00, "admission": "2022-03-15"},
    {"name": "Bruno Henrique Costa", "role": "Operador de Maquina",      "salary": 2200.00, "admission": "2021-07-01"},
    {"name": "Carla Mendes Silva",   "role": "Supervisora de Producao",  "salary": 3500.00, "admission": "2020-01-10"},
    {"name": "Diego Lima Santos",    "role": "Tecnico de Manutencao",    "salary": 2800.00, "admission": "2023-05-20"},
    {"name": "Eduarda Rocha Neves",  "role": "Assistente de RH",         "salary": 2100.00, "admission": "2022-11-01"},
    {"name": "Felipe Torres Braga",  "role": "Almoxarife",               "salary": 1950.00, "admission": "2021-04-15"},
    {"name": "Gabriela Motta Leal",  "role": "Analista Financeiro",      "salary": 3200.00, "admission": "2019-08-01"},
    {"name": "Henrique Vaz Cunha",   "role": "Auxiliar de Producao",     "salary": 1600.00, "admission": "2024-02-01"},
]

SEAMSTRESSES = [
    "Rosana Aparecida Pinto",
    "Fernanda Cruz Oliveira",
    "Marisa Teixeira Gomes",
    "Patricia Borges Sousa",
    "Simone Alves Cardoso",
]

def create_employees():
    created = []
    for e in EMPLOYEES:
        body = {
            "name": e["name"],
            "cpf": gen_cpf(),
            "role": e["role"],
            "salary": e["salary"],
            "admission_date": e["admission"],
            "registration_date": e["admission"],
            "weekly_hours": 44,
            "needs_transport": random.choice([True, False]),
            "vt_daily": 8.50 if random.random() > 0.5 else None,
            "auxilio": random.choice([None, 150.00, 200.00]),
            "phone": f"(11) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}",
            "city": random.choice(["Sao Paulo", "Guarulhos", "Maua", "Santo Andre"]),
            "state": "SP",
        }
        emp = post("/employees", body)
        if emp:
            created.append(emp)
            print(f"  Funcionario: {e['name']} (id={emp['id']})")
    return created

def create_seamstresses():
    created = []
    for name in SEAMSTRESSES:
        body = {
            "name": name,
            "cpf": gen_cpf(),
            "phone": f"(11) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}"
        }
        seam = post("/seamstresses", body)
        if seam:
            created.append(seam)
            print(f"  Costureira: {name} (id={seam['id']})")
    return created

def create_timesheet(emp_id, month, year):
    from calendar import monthrange
    days = monthrange(year, month)[1]
    for day in range(1, days + 1):
        d = date(year, month, day)
        if d.weekday() >= 5:
            continue
        if d > date.today():
            break
        roll = random.random()
        if roll < 0.05:
            post(f"/timesheet/{emp_id}", {
                "work_date": d.isoformat(),
                "is_absence": True, "justification": "Falta nao justificada"
            })
        elif roll < 0.08:
            post(f"/timesheet/{emp_id}", {
                "work_date": d.isoformat(),
                "is_absence": True, "is_medical_certificate": True,
                "justification": "Atestado medico"
            })
        else:
            extra = random.choice([0, 0, 0, 30, 60, -30])
            exit_min = 17 * 60 + 48 + extra
            exit_h, exit_m = divmod(exit_min, 60)
            post(f"/timesheet/{emp_id}", {
                "work_date": d.isoformat(),
                "entry_time": "08:00:00",
                "lunch_out_time": "12:00:00",
                "lunch_in_time": "13:00:00",
                "exit_time": f"{exit_h:02d}:{exit_m:02d}:00",
            })

def close_payroll_month(month, year):
    pay_date = date(year, month, 5)
    if pay_date > date.today():
        pay_date = date.today()

    result = post("/payroll/batch", {
        "competence_month": month,
        "competence_year": year,
        "payment_date": pay_date.isoformat()
    })
    if result:
        print(f"    {len(result)} holerite(s) gerado(s) para {month:02d}/{year}")

    closed = post(f"/payroll/period/close-all?month={month}&year={year}&payment_date={pay_date.isoformat()}")
    if closed:
        print(f"    {len(closed)} holerite(s) fechado(s)")
    return closed or []

def next_month_5th(month, year):
    """Retorna o dia 5 do mês seguinte (data de pagamento da regra)."""
    if month == 12:
        return date(year + 1, 1, 5)
    return date(year, month + 1, 5)

def register_seamstress_payments(seam_ids, month, year):
    for sid in seam_ids:
        post(f"/seamstresses/{sid}/payments", {
            "payment_type": "mensal",
            "competence_month": month,
            "competence_year": year,
            "amount": round(random.uniform(400, 900), 2),
        })
        if random.random() < 0.4:
            post(f"/seamstresses/{sid}/payments", {
                "payment_type": "entrega",
                "competence_month": month,
                "competence_year": year,
                "amount": round(random.uniform(100, 500), 2),
                "payment_date": date(year, month, random.randint(10, 25)).isoformat(),
            })

    # Fecha o mês marcando todos como pago (dia 5 do mês seguinte)
    pay_date = next_month_5th(month, year)
    if pay_date > date.today():
        pay_date = date.today()
    result = post("/seamstresses/close-month", {
        "competence_month": month,
        "competence_year": year,
        "payment_date": pay_date.isoformat(),
    })
    if result:
        print(f"    Costureiras {month:02d}/{year} fechadas — pago em {pay_date}")

def program_vacations(employees):
    for i, emp in enumerate(employees):
        emp_id = emp["id"]
        admission = date.fromisoformat(emp["admission_date"])
        if (date.today() - admission).days < 365:
            continue

        acq_start = admission
        acq_end   = admission + timedelta(days=364)

        roll = i % 4

        if roll == 0:
            r = post("/vacation", {
                "employee_id": emp_id,
                "acquisition_start": acq_start.isoformat(),
                "acquisition_end": acq_end.isoformat(),
                "enjoyment_start": date(2025, 1, 6).isoformat(),
                "enjoyment_days": 30,
            })
            if r:
                post(f"/vacation/{r['id']}/complete")
                print(f"    Ferias concluidas: {emp['name']}")

        elif roll == 1:
            r = post("/vacation", {
                "employee_id": emp_id,
                "acquisition_start": acq_start.isoformat(),
                "acquisition_end": acq_end.isoformat(),
                "enjoyment_start": date(2026, 7, 6).isoformat(),
                "enjoyment_days": 30,
            })
            if r:
                print(f"    Ferias agendadas (Jul/2026): {emp['name']}")

        elif roll == 2:
            r = post("/vacation", {
                "employee_id": emp_id,
                "acquisition_start": acq_start.isoformat(),
                "acquisition_end": acq_end.isoformat(),
                "sell_all_days": True,
                "enjoyment_days": 0,
            })
            if r:
                post(f"/vacation/{r['id']}/complete")
                print(f"    Ferias vendidas (sell_all): {emp['name']}")

        elif roll == 3:
            r = post("/vacation", {
                "employee_id": emp_id,
                "acquisition_start": acq_start.isoformat(),
                "acquisition_end": acq_end.isoformat(),
                "enjoyment_start": date(2025, 6, 2).isoformat(),
                "enjoyment_days": 20,
                "abono_days": 10,
            })
            if r:
                post(f"/vacation/{r['id']}/complete")
                print(f"    Ferias com abono (20+10): {emp['name']}")

if __name__ == "__main__":
    login("teste", "Seri1263@")

    print("\n-- Criando funcionarios --")
    employees = create_employees()
    if not employees:
        print("Nenhum funcionario criado. Verifique o login.")
        exit(1)

    print("\n-- Criando costureiras --")
    seamstresses = create_seamstresses()

    emp_ids  = [e["id"] for e in employees]
    seam_ids = [s["id"] for s in seamstresses]

    months = [(1,2026),(2,2026),(3,2026),(4,2026),(5,2026)]
    today  = date.today()

    print("\n-- Registrando e fechando ponto --")
    for month, year in months:
        if date(year, month, 1) > today:
            break
        print(f"  Periodo {month:02d}/{year}...")
        # Cria o período
        post("/timesheet/periods", {"competence_month": month, "competence_year": year})
        # Registra entradas de cada funcionário
        for emp_id in emp_ids:
            create_timesheet(emp_id, month, year)
        # Fecha o período
        result = post(f"/timesheet/periods/{month}/{year}/close")
        if result is not None:
            print(f"    Periodo fechado")

    print("\n-- Fechando folhas de pagamento --")
    for month, year in months:
        if date(year, month, 1) > today:
            break
        print(f"  Folha {month:02d}/{year}...")
        close_payroll_month(month, year)

    print("\n-- Registrando pagamentos de costureiras --")
    for month, year in months:
        if date(year, month, 1) > today:
            break
        print(f"  Costureiras {month:02d}/{year}...")
        register_seamstress_payments(seam_ids, month, year)
    print("  Pagamentos registrados")

    print("\n-- Programando ferias --")
    program_vacations(employees)

    print(f"\nSeed concluido!")
    print(f"  {len(employees)} funcionarios | {len(seamstresses)} costureiras | {len(months)} meses")
