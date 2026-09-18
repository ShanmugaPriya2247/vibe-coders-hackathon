# ChainSight Advanced Full-Stack App

## Version 3.1: live vendor and manager dashboards

- Select Manager dashboard or Vendor dashboard from the role selector.
- Vendors publish availability, capacity, lead-time, shipment and evidence updates.
- Updates are stored in TimescaleDB and broadcast through Redis Streams.
- The manager signal view refreshes automatically every five seconds.
- Existing installations create the additional database table automatically.

## Start the complete application

1. Install and open Docker Desktop. Wait for **Engine running**.
2. Extract this ZIP to the Desktop.
3. Open the extracted `ChainSight-Advanced-App` folder.
4. Click the File Explorer address bar, type `powershell`, and press Enter.
5. Run:

```powershell
docker compose up --build
```

The first run downloads database images and may take 5–15 minutes.

## Open the application

- ChainSight app: http://localhost:8080
- FastAPI documentation: http://localhost:8000/docs
- Database health: http://localhost:8000/health
- Neo4j Browser: http://localhost:7474

Neo4j login:

```text
Username: neo4j
Password: chainsight_demo
```

PostgreSQL/TimescaleDB:

```text
Host: localhost
Port: 5432
Database: chainsight
Username: chainsight
Password: chainsight_demo
```

## Stop the application

Press `Ctrl+C`, then run:

```powershell
docker compose down
```

## Reset all demonstration data

This deletes only the ChainSight Docker database volumes:

```powershell
docker compose down -v
docker compose up --build
```

## Architecture

- Installable PWA frontend
- FastAPI intelligence and scenario engine
- PostgreSQL for master data, risks and scenario history
- TimescaleDB for timestamped operational signals
- Neo4j for dependency and cascade paths
- Redis Streams for real-time events
- Monte Carlo uncertainty estimation
- Weighted risk scoring and mitigation ranking
