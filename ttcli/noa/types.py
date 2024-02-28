from datetime import datetime
from typing import Optional

from inflection import camelize
from pydantic import ConfigDict, BaseModel


class NoaTimesheetEntryPartial(BaseModel):
    activity_id: int
    approval_status: int
    billable: bool
    correction: int
    cost: float
    cost_currency_amount: float
    cost_currency_id: int
    cost_method: int
    create_date: datetime
    create_resource_id: int
    deleted_marked: bool
    description_required: bool
    hours_moved: float
    id: int
    job_id: int
    journal_number: int
    post_date: datetime
    pricelist_id: int
    public: bool
    registration_date: datetime
    resource_id: int
    sale: float
    sale_currency_amount: float
    sale_currency_id: int
    sequence_number: int
    tariff_additional_percent_cost: float
    tariff_additional_percent_ic_sale: float
    tariff_additional_percent_sale: float
    task_id: int
    update_date: datetime
    update_resource_id: int
    update_type: int
    description: Optional[str] = None
    has_approved_resource_initals: Optional[str] = None
    hours: Optional[float] = None
    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True, extra="forbid")


class NoaTimesheetEntry(NoaTimesheetEntryPartial):
    access: bool
    can_edit: bool
    can_edit_week: bool
    lock_description: str
    lock_number: int
    locked: bool
    pinned: bool
    sequence_has_entry: bool
    task_hours: float
    task_hours_time_registration: float
    task_phase_name: str
    is_costing_code_valid: bool


class NoaDateVisualization(BaseModel):
    access: bool
    activity_id: int
    activity_text: str
    customer_id: int
    customer_name: str
    first_reg_date: str
    id: int
    job_id: int
    job_name: str
    pinned: bool
    project_id: int
    project_name: str
    resource_id: int
    sequence_number: int
    task_description: str
    task_hours: float
    task_hours_time_registration: float
    task_id: int
    task_phase_name: str
    model_config = ConfigDict(alias_generator=camelize, populate_by_name=True)
