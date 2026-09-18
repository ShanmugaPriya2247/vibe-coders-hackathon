CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS suppliers (
  id BIGSERIAL PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  material TEXT NOT NULL,
  availability NUMERIC NOT NULL,
  lead_time_days INTEGER NOT NULL,
  reliability NUMERIC NOT NULL,
  emergency_capacity INTEGER NOT NULL,
  unit_cost NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS inventory (
  id BIGSERIAL PRIMARY KEY,
  material TEXT NOT NULL,
  warehouse TEXT NOT NULL,
  quantity NUMERIC NOT NULL,
  safety_stock NUMERIC NOT NULL,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
SELECT create_hypertable('inventory','observed_at',if_not_exists=>TRUE);

CREATE TABLE IF NOT EXISTS operational_signals (
  id BIGSERIAL,
  source TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  entity_name TEXT NOT NULL,
  value NUMERIC,
  status TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (id, observed_at)
);
SELECT create_hypertable('operational_signals','observed_at',if_not_exists=>TRUE);

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
SELECT create_hypertable('vendor_updates','observed_at',if_not_exists=>TRUE);

CREATE TABLE IF NOT EXISTS risks (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  score INTEGER NOT NULL,
  severity TEXT NOT NULL,
  evidence JSONB NOT NULL,
  detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scenarios (
  id BIGSERIAL PRIMARY KEY,
  resource TEXT NOT NULL,
  disruption_type TEXT NOT NULL,
  duration_days INTEGER NOT NULL,
  inputs JSONB NOT NULL,
  risk_score INTEGER NOT NULL,
  result JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO suppliers(name,material,availability,lead_time_days,reliability,emergency_capacity,unit_cost) VALUES
('Supplier A','Microchip X',0,12,72,0,950),
('Supplier B','Microchip X',100,3,93,650,1120),
('Supplier C','Battery Cell',100,5,89,900,730)
ON CONFLICT(name) DO NOTHING;

INSERT INTO inventory(material,warehouse,quantity,safety_stock,observed_at) VALUES
('Microchip X','Warehouse W1',500,200,NOW()),
('Microchip X','Warehouse W2',200,80,NOW()),
('Battery Cell','Warehouse W1',1200,300,NOW());

INSERT INTO operational_signals(source,signal_type,entity_name,value,status,metadata,observed_at) VALUES
('Supplier portal','supplier_availability','Supplier A',0,'critical','{"message":"10-day outage reported"}',NOW()),
('ERP','inventory','Microchip X',500,'warning','{"warehouse":"W1"}',NOW()),
('GPS/TMS','transport_delay','Mumbai-Pune R3',8,'high','{"unit":"hours"}',NOW()),
('Demand model','demand_variance','Product P1',8,'warning','{"unit":"percent"}',NOW()),
('External feed','weather_risk','Chennai',22,'normal','{}',NOW());

INSERT INTO risks(name,category,score,severity,evidence) VALUES
('Supplier A interruption','supplier',86,'CRITICAL','{"availability":0,"dependent_material":"Microchip X","duration_days":10}'),
('Mumbai-Pune route congestion','transport',68,'HIGH','{"delay_hours":8,"shipments":2}'),
('Product P1 demand variance','demand',51,'MEDIUM','{"forecast_change_percent":8}');
