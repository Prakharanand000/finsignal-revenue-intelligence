import numpy as np
import pandas as pd
from datetime import date, timedelta
from snowflake.snowpark.context import get_active_session

session = get_active_session()
np.random.seed(42)

# === CONFIG ===
NUM_CUSTOMERS    = 2000
PERIOD_START     = date(2023, 2, 1)   # FY2024 Q1 start
PERIOD_END       = date(2026, 1, 31)  # FY2026 Q4 end

PLAN_TIERS       = ["Starter", "Growth", "Enterprise"]
PLAN_MRR         = {"Starter": 200, "Growth": 1200, "Enterprise": 6000}
PLAN_WEIGHTS     = [0.60, 0.30, 0.10]
REGIONS          = ["NA", "EMEA", "APAC", "LATAM"]
REGION_WEIGHTS   = [0.40, 0.30, 0.20, 0.10]

MONTHLY_CHURN_RATE       = 0.015
MONTHLY_EXPANSION_RATE   = 0.0064   # ~8% annual
MONTHLY_CONTRACTION_RATE = 0.0025   # ~3% annual
MONTHLY_REACTIVATION_RATE= 0.005

# Bad quarter: FY2026-Q3 = Aug, Sep, Oct 2025 (fiscal year starts Feb 1)
BAD_QUARTER_MONTHS        = [date(2025, 8, 1), date(2025, 9, 1), date(2025, 10, 1)]
BAD_QUARTER_CHURN_RATE    = 0.030   # 2x for Growth tier
BAD_QUARTER_CONTRACTION   = 0.005   # 2x for Growth tier

# === CUSTOMERS ===
total_days   = (PERIOD_END - PERIOD_START).days
offsets      = np.random.randint(0, total_days, size=NUM_CUSTOMERS)
signup_dates = [PERIOD_START + timedelta(days=int(d)) for d in offsets]

customers = pd.DataFrame({
    "customer_id":       [f"CUST-{i:05d}" for i in range(1, NUM_CUSTOMERS + 1)],
    "signup_date":       signup_dates,
    "region":            np.random.choice(REGIONS, size=NUM_CUSTOMERS, p=REGION_WEIGHTS),
    "initial_plan_tier": np.random.choice(PLAN_TIERS, size=NUM_CUSTOMERS, p=PLAN_WEIGHTS),
})

# === SUBSCRIPTIONS ===
all_months     = pd.date_range(PERIOD_START, PERIOD_END, freq="MS").date.tolist()
subscriptions  = []
sub_counter    = 0
customer_state = {}
churned_pool   = set()

for month in all_months:
    next_month = (pd.Timestamp(month) + pd.offsets.MonthBegin(1)).date()
    new_this   = customers[(customers["signup_date"] >= month) & (customers["signup_date"] < next_month)]
    for _, row in new_this.iterrows():
        customer_state[row["customer_id"]] = {"plan_tier": row["initial_plan_tier"], "status": "active"}

    if churned_pool:
        n_reactivate = max(1, int(len(churned_pool) * MONTHLY_REACTIVATION_RATE))
        for cid in np.random.choice(list(churned_pool), size=min(n_reactivate, len(churned_pool)), replace=False):
            churned_pool.discard(cid)
            customer_state[cid] = {"plan_tier": "Starter", "status": "active"}

    for cid, state in [(c, s) for c, s in customer_state.items() if s["status"] == "active"]:
        tier     = state["plan_tier"]
        tier_idx = PLAN_TIERS.index(tier) if tier in PLAN_TIERS else 0
        is_bad   = month in BAD_QUARTER_MONTHS and tier == "Growth"
        churn_r  = BAD_QUARTER_CHURN_RATE  if is_bad else MONTHLY_CHURN_RATE
        cont_r   = BAD_QUARTER_CONTRACTION if is_bad else MONTHLY_CONTRACTION_RATE
        roll     = np.random.random()

        if roll < churn_r:
            customer_state[cid]["status"] = "churned"; churned_pool.add(cid)
            final_tier, status = tier, "churned"
        elif roll < churn_r + MONTHLY_EXPANSION_RATE and tier_idx < 2:
            new_tier = PLAN_TIERS[tier_idx + 1]; customer_state[cid]["plan_tier"] = new_tier
            final_tier, status = new_tier, "active"
        elif roll < churn_r + MONTHLY_EXPANSION_RATE + cont_r and tier_idx > 0:
            new_tier = PLAN_TIERS[tier_idx - 1]; customer_state[cid]["plan_tier"] = new_tier
            final_tier, status = new_tier, "active"
        else:
            final_tier, status = tier, "active"

        sub_counter += 1
        subscriptions.append({
            "subscription_id": f"SUB-{sub_counter:07d}",
            "customer_id": cid,
            "month": month.strftime("%Y-%m-%d"),
            "plan_tier": final_tier,
            "mrr": round(PLAN_MRR.get(final_tier, 200) * np.random.uniform(0.9, 1.1), 2),
            "status": status,
        })

subs_df = pd.DataFrame(subscriptions)
null_mask = np.random.random(len(subs_df)) < 0.01
subs_df.loc[null_mask, "plan_tier"] = None

# === INVOICES ===
active_subs = subs_df[subs_df["status"] == "active"].copy().reset_index(drop=True)
invoices    = active_subs[["customer_id", "month", "mrr"]].copy()
invoices["invoice_id"]   = [f"INV-{i:07d}" for i in range(1, len(invoices) + 1)]
invoices["period_month"] = invoices["month"]
inv_dates = pd.to_datetime(invoices["month"])
late_mask = np.random.random(len(invoices)) < 0.05
late_days = np.random.randint(5, 16, size=len(invoices))
month_ends = inv_dates + pd.offsets.MonthEnd(0)
invoices["invoice_date"] = inv_dates.dt.strftime("%Y-%m-%d")
invoices.loc[late_mask, "invoice_date"] = (
    month_ends[late_mask] + pd.to_timedelta(late_days[late_mask], unit="D")
).dt.strftime("%Y-%m-%d")
invoices["amount"] = invoices["mrr"]
invoices = invoices[["invoice_id", "customer_id", "invoice_date", "period_month", "amount"]]
dup_idx  = np.random.choice(invoices.index, size=int(len(invoices) * 0.02), replace=False)
invoices = pd.concat([invoices, invoices.loc[dup_idx].copy()], ignore_index=True)

# === USAGE EVENTS ===
EVENT_TYPES   = ["api_call", "login", "report_generated", "data_export", "integration_sync"]
usage_events  = []
event_counter = 0
active_grouped = subs_df[subs_df["status"] == "active"].groupby("customer_id")["month"].apply(list).to_dict()

for cid, months in active_grouped.items():
    for m in months:
        ms = pd.to_datetime(m).date()
        for _ in range(np.random.randint(2, 11)):
            event_counter += 1
            usage_events.append({
                "event_id":   f"EVT-{event_counter:09d}",
                "customer_id": cid,
                "event_date": (ms + timedelta(days=np.random.randint(0, 28))).strftime("%Y-%m-%d"),
                "event_type": np.random.choice(EVENT_TYPES),
            })

usage_df = pd.DataFrame(usage_events)

# === WRITE TO SNOWFLAKE ===
session.sql("USE ROLE ACCOUNTADMIN").collect()
session.sql("USE WAREHOUSE FINSIGNAL_WH").collect()
session.sql("USE DATABASE FINSIGNAL").collect()
session.sql("USE SCHEMA BRONZE").collect()

session.write_pandas(customers, "RAW_CUSTOMERS",     auto_create_table=True, overwrite=True)
session.write_pandas(subs_df,   "RAW_SUBSCRIPTIONS", auto_create_table=True, overwrite=True)
session.write_pandas(invoices,  "RAW_INVOICES",       auto_create_table=True, overwrite=True)
session.write_pandas(usage_df,  "RAW_USAGE_EVENTS",   auto_create_table=True, overwrite=True)

print(f"RAW_CUSTOMERS:     {len(customers):,} rows")
print(f"RAW_SUBSCRIPTIONS: {len(subs_df):,} rows")
print(f"RAW_INVOICES:      {len(invoices):,} rows (includes ~2% duplicates)")
print(f"RAW_USAGE_EVENTS:  {len(usage_df):,} rows")
print("All tables loaded to FINSIGNAL.BRONZE successfully.")
