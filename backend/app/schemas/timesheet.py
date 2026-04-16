from datetime import date, time
from pydantic import BaseModel, field_validator, model_validator


class TimesheetEntryCreate(BaseModel):
    work_date: date
    entry_time: time | None = None
    lunch_out_time: time | None = None
    lunch_in_time: time | None = None
    exit_time: time | None = None
    is_absence: bool = False
    is_medical_certificate: bool = False
    justification: str | None = None

    @model_validator(mode="after")
    def validate_times(self):
        times = [self.entry_time, self.lunch_out_time, self.lunch_in_time, self.exit_time]
        filled = [t for t in times if t is not None]

        # Dia de falta: não precisa de horários
        if self.is_absence or self.is_medical_certificate:
            return self

        # Se algum horário foi preenchido, todos devem ser
        if filled and len(filled) != 4:
            raise ValueError("Preencha todas as 4 batidas ou deixe todas em branco")

        if len(filled) == 4:
            def m(t: time) -> int:
                return t.hour * 60 + t.minute

            if m(self.lunch_out_time) <= m(self.entry_time):
                raise ValueError("Saída almoço deve ser após a entrada")
            if m(self.lunch_in_time) <= m(self.lunch_out_time):
                raise ValueError("Retorno almoço deve ser após a saída para almoço")
            if m(self.exit_time) <= m(self.lunch_in_time):
                raise ValueError("Saída final deve ser após o retorno do almoço")

        return self


class TimesheetEntryUpdate(BaseModel):
    entry_time: time | None = None
    lunch_out_time: time | None = None
    lunch_in_time: time | None = None
    exit_time: time | None = None
    is_absence: bool | None = None
    is_medical_certificate: bool | None = None
    justification: str | None = None
    is_annulled: bool | None = None


class TimesheetEntryRead(BaseModel):
    id: int
    employee_id: int
    work_date: date
    entry_time: time | None
    lunch_out_time: time | None
    lunch_in_time: time | None
    exit_time: time | None
    worked_minutes: int
    overtime_minutes: int
    late_minutes: int
    is_absence: bool
    is_medical_certificate: bool
    is_annulled: bool
    justification: str | None

    model_config = {"from_attributes": True}


class HourBankRead(BaseModel):
    employee_id: int
    balance_minutes: int
    balance_hours: str  # ex: "+2h30" ou "-1h15"

    model_config = {"from_attributes": True}


class MonthlyReportEntry(BaseModel):
    work_date: date
    worked_minutes: int
    overtime_minutes: int
    late_minutes: int
    is_absence: bool
    is_medical_certificate: bool
    is_annulled: bool


class MonthlyReport(BaseModel):
    employee_id: int
    employee_name: str
    month: int
    year: int
    total_worked_minutes: int
    total_overtime_minutes: int
    total_late_minutes: int
    total_absences: int
    total_medical_certificates: int
    hour_bank_balance_minutes: int
    entries: list[MonthlyReportEntry]
