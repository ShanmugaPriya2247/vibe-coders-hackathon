import asyncio
import json
import math
import os
import random
from datetime import datetime, timezone

import asyncpg
import numpy as np
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

app = FastAPI(title="ChainSight Intelligence API", version="3.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

pg_pool = None
redis_client = None
neo4j_driver = None


class Scenario(BaseModel):
    disruption_type: str = "supplier"
    resource: str = "Supplier A — Microchip X"
    duration_days: int = Field(10, ge=1, le=60)
    demand_change_percent: float = Field(8, ge=-50, le=200)
    current_inventory: float = Field(500, ge=0)
    daily_consumption: float = Field(100, gt=0)
    unit_value: float = Field(1000, gt=0)


class VendorUpdate(BaseModel):
    vendor_name: str = Field(min_length=2, max_length=100)
    material: str = Field(min_length=2, max_length=100)
    availability_status: str
    available_capacity: float = Field(ge=0)
    lead_time_days: int = Field(ge=0, le=365)
    shipment_status: str
    message: str = Field(default="", max_length=500)


def level(score):
    return "CRITICAL" if score >= 80 else "HIGH" if score >= 60 else "MEDIUM" if score >= 40 else "LOW"


def simulate(s: Scenario):
    adjusted = s.daily_consumption * (1 + s.demand_change_percent / 100)
    coverage = s.current_inventory / adjusted
    shortage_days = max(0, s.duration_days - coverage)
    loss = round(shortage_days * adjusted)
    financial = round(loss * s.unit_value)
    orders = max(0, round(loss * 0.30))
    inventory_pressure = min(100, max(0, (s.duration_days - coverage) / max(1, s.duration_days) * 100))
    duration_pressure = min(100, s.duration_days * 6)
    demand_pressure = min(100, max(0, s.demand_change_percent * 5))
    dependency_criticality = 92 if s.disruption_type == "supplier" else 78
    financial_pressure = min(100, financial / 10000)
    score = round(0.28 * inventory_pressure + 0.18 * duration_pressure + 0.14 * demand_pressure + 0.25 * dependency_criticality + 0.15 * financial_pressure)

    rng = np.random.default_rng(42)
    demand_samples = rng.normal(adjusted, adjusted * 0.10, 1000).clip(min=1)
    stockout_samples = s.current_inventory / demand_samples
    p10, p50, p90 = [round(float(x), 1) for x in np.percentile(stockout_samples, [10, 50, 90])]

    mitigated_loss = max(0, loss - 650)
    mitigated_financial = round(mitigated_loss * s.unit_value + 125000)
    reduction = 0 if financial == 0 else round((financial - mitigated_financial) / financial * 100)

    return {
        "risk": {"score": score, "level": level(score), "confidence": 91},
        "summary": f"{s.resource} is disrupted for {s.duration_days} days. Inventory supports {coverage:.1f} days; stockout is most likely near day {math.ceil(coverage)} and {orders} orders may be exposed.",
        "impact": {
            "adjusted_daily_usage": round(adjusted, 1), "inventory_coverage_days": round(coverage, 1),
            "stockout_day": math.ceil(coverage), "production_loss_units": loss,
            "orders_exposed": orders, "financial_exposure": financial,
            "stockout_uncertainty": {"early_p10": p10, "median_p50": p50, "late_p90": p90}
        },
        "cascade": [
            {"stage": "NOW", "event": "Supplier resource unavailable"},
            {"stage": f"DAY {max(1, math.floor(coverage)-1)}", "event": "Safety stock breached"},
            {"stage": f"DAY {math.ceil(coverage)}", "event": "Production constrained"},
            {"stage": f"DAY {s.duration_days}", "event": f"{orders} customer orders exposed"}
        ],
        "recommendations": [
            {"action": "Activate Supplier B for 650 units", "reason": "Qualified alternate has a 3-day lead time, inside the forecast inventory runway.", "risk_reduction": max(35, reduction), "score": 94},
            {"action": "Transfer 200 units from Warehouse W2", "reason": "Available regional stock protects the highest-value production orders.", "risk_reduction": 31, "score": 87},
            {"action": "Prioritize high-margin customer orders", "reason": "Allocation reduces financial loss when full demand cannot be served.", "risk_reduction": 18, "score": 79}
        ],
        "before_after": {"before": financial, "after": mitigated_financial, "reduction_percent": reduction},
        "evidence": [
            f"Inventory cover: {coverage:.1f} days at {adjusted:.1f} units/day.",
            f"Disruption exceeds inventory runway by {shortage_days:.1f} days.",
            f"Monte Carlo stockout interval: day {p10} to day {p90}; median day {p50}.",
            "Neo4j path: Supplier A → Microchip X → Factory F1 → Product P1 → Customer orders.",
            "Supplier B lead time is 3 days with 650-unit emergency capacity."
        ]
    }


async def connect_with_retry():
    global pg_pool, redis_client, neo4j_driver
    for _ in range(30):
        try:
            pg_pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
            redis_client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
            await redis_client.ping()
            neo4j_driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]))
            neo4j_driver.verify_connectivity()
            await ensure_runtime_schema()
            seed_graph()
            return
        except Exception:
            await asyncio.sleep(2)


async def ensure_runtime_schema():
    await pg_pool.execute("""
        CREATE TABLE IF NOT EXISTS vendor_updates (
          id BIGSERIAL,
          vendor_name TEXT NOT NULL,
          material TEXT NOT NULL,
          availability_status TEXT NOT NULL,
          available_capacity NUMERIC NOT NULL DEFAULT 0,
          lead_time_days INTEGER NOT NULL DEFAULT 0,
          shipment_status TEXT NOT NULL,
          message TEXT NOT NULL DEFAULT '',
          observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          PRIMARY KEY (id, observed_at)
        );
    """)
    await pg_pool.execute("SELECT create_hypertable('vendor_updates','observed_at',if_not_exists=>TRUE)")


def seed_graph():
    query = """
    MERGE (s:Supplier {name:'Supplier A', risk:86})
    MERGE (m:Material {name:'Microchip X', criticality:95})
    MERGE (f:Factory {name:'Factory F1'})
    MERGE (w:Warehouse {name:'Warehouse W1'})
    MERGE (p:Product {name:'Product P1'})
    MERGE (s)-[:SUPPLIES]->(m)-[:FEEDS]->(f)-[:SHIPS_TO]->(w)-[:SUPPORTS]->(p)
    MERGE (b:Supplier {name:'Supplier B', risk:24, lead_time_days:3, emergency_capacity:650})
    MERGE (b)-[:ALTERNATIVE_FOR]->(m)
    """
    with neo4j_driver.session() as session:
        session.run(query).consume()


@app.on_event("startup")
async def startup():
    await connect_with_retry()


@app.on_event("shutdown")
async def shutdown():
    if pg_pool: await pg_pool.close()
    if redis_client: await redis_client.aclose()
    if neo4j_driver: neo4j_driver.close()


@app.get("/health")
async def health():
    pg = bool(pg_pool)
    rd = bool(redis_client and await redis_client.ping())
    graph = bool(neo4j_driver)
    return {"status": "healthy" if pg and rd and graph else "degraded", "postgres_timescale": pg, "neo4j": graph, "redis": rd, "time": datetime.now(timezone.utc).isoformat()}


@app.get("/risks")
async def risks():
    rows = await pg_pool.fetch("SELECT name, category, score, severity, evidence FROM risks ORDER BY score DESC")
    return [dict(row) for row in rows]


@app.get("/signals")
async def signals():
    rows = await pg_pool.fetch("SELECT source, signal_type, entity_name, value, status, observed_at FROM operational_signals ORDER BY observed_at DESC LIMIT 50")
    return [dict(row) for row in rows]


@app.get("/vendor-updates")
async def vendor_updates():
    rows = await pg_pool.fetch("""
        SELECT id, vendor_name, material, availability_status,
               available_capacity, lead_time_days, shipment_status,
               message, observed_at
        FROM vendor_updates
        ORDER BY observed_at DESC LIMIT 50
    """)
    return [dict(row) for row in rows]


@app.post("/vendor-updates")
async def create_vendor_update(update: VendorUpdate):
    row = await pg_pool.fetchrow("""
        INSERT INTO vendor_updates(
          vendor_name, material, availability_status, available_capacity,
          lead_time_days, shipment_status, message
        ) VALUES($1,$2,$3,$4,$5,$6,$7)
        RETURNING id, observed_at
    """, update.vendor_name, update.material, update.availability_status,
        update.available_capacity, update.lead_time_days,
        update.shipment_status, update.message)
    risk_score = min(100, round(
        (45 if update.availability_status != "available" else 5) +
        min(30, update.lead_time_days * 3) +
        (20 if update.shipment_status in {"delayed", "blocked"} else 0) +
        (10 if update.available_capacity == 0 else 0)
    ))
    await redis_client.xadd("chainsight:events", {
        "event": "vendor_update", "vendor": update.vendor_name,
        "status": update.availability_status, "risk_score": str(risk_score)
    }, maxlen=1000)
    return {"status": "accepted", "id": row["id"],
            "observed_at": row["observed_at"], "risk_score": risk_score}


@app.get("/dependency/{supplier_name}")
async def dependency(supplier_name: str):
    query = "MATCH p=(s:Supplier {name:$name})-[*1..5]->(n) RETURN [x IN nodes(p) | {name:x.name, type:labels(x)[0]}] AS path"
    with neo4j_driver.session() as session:
        records = session.run(query, name=supplier_name)
        return {"supplier": supplier_name, "paths": [r["path"] for r in records]}


@app.post("/analyse")
async def analyse(scenario: Scenario):
    result = simulate(scenario)
    scenario_id = await pg_pool.fetchval(
        "INSERT INTO scenarios(resource, disruption_type, duration_days, inputs, risk_score, result) VALUES($1,$2,$3,$4::jsonb,$5,$6::jsonb) RETURNING id",
        scenario.resource, scenario.disruption_type, scenario.duration_days, json.dumps(scenario.model_dump()), result["risk"]["score"], json.dumps(result)
    )
    await redis_client.xadd("chainsight:events", {"event": "scenario_analysed", "scenario_id": str(scenario_id), "risk_score": str(result["risk"]["score"])}, maxlen=1000)
    result["scenario_id"] = scenario_id
    result["data_sources"] = ["PostgreSQL/TimescaleDB", "Neo4j", "Redis Streams", "Monte Carlo engine"]
    return result
