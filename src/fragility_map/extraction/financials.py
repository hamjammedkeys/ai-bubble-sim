from pydantic import BaseModel


class FinancialMetricSnapshot(BaseModel):
    company_id: str
    fiscal_period: str
    revenue: float | None = None
    cash: float | None = None
    debt: float | None = None
    operating_income: float | None = None
    capital_expenditure: float | None = None
    interest_expense: float | None = None
    metric_source_ids: list[str] = []
