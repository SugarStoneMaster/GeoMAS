import duckdb
import json

conn = duckdb.connect("data/simulation.duckdb")
# Find a single envelope where Foreign action IDLE was executed at turn 1 for VALKYR
res = conn.execute("SELECT envelope_json FROM envelopes WHERE simulation_id=60 AND turn=1 AND nation_id='VALKYR'").fetchone()

if res:
    env = json.loads(res[0])
    print("FOREIGN PAYLOAD RAW:")
    print(json.dumps(env.get('foreign_payload'), indent=2))
