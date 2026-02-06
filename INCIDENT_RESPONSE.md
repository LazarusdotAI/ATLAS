# Incident Response Playbook — StockBotFree

## 1. Emergency: Stop All Trading Immediately

### Via API (fastest)
```bash
curl -X POST http://localhost:8000/kill-switch \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Manual emergency stop"}'
```

### Via Frontend
Click the **Kill Switch** button on the Dashboard page.

### Via Terminal (if server is reachable)
```bash
python -c "
import asyncio, httpx
async def stop():
    async with httpx.AsyncClient() as c:
        r = await c.post('http://localhost:8000/kill-switch',
            json={'reason':'emergency'}, headers={'X-API-Key':'YOUR_KEY'})
        print(r.json())
asyncio.run(stop())
"
```

### What Kill Switch Does
1. Cancels **all open orders** via Alpaca API
2. Closes **all positions** at market
3. Sets a module-level flag blocking new trades
4. Logs the event to `logs/audit.jsonl`

### To Resume Trading
```bash
curl -X POST http://localhost:8000/kill-switch/reset \
  -H "X-API-Key: $API_KEY"
```

---

## 2. Revoke API Keys

### Alpaca Keys
1. Log into [Alpaca Dashboard](https://app.alpaca.markets)
2. Navigate to **API Keys** → **Regenerate**
3. Update `.env` with new keys
4. Restart the server

### StockBotFree API Key
1. Change `API_KEY` in `.env`
2. Restart the server — old keys immediately invalid

### LLM Provider Key
1. Rotate the key at your provider (OpenAI/Anthropic dashboard)
2. Update `LLM_API_KEY` in `.env`
3. Restart

---

## 3. Anomaly Auto-Disable Triggers

The `AnomalyDetector` automatically triggers the kill switch when:
- **Slippage** > 2.0% on any fill
- **P&L swing** > $50 within 60 seconds
- **API errors** > 5 within 60 seconds

When triggered, check `logs/audit.jsonl` for `anomaly_detected` events.

---

## 4. Post-Mortem Process

After any incident:

1. **Preserve evidence**
   ```bash
   cp logs/audit.jsonl logs/audit_incident_$(date +%Y%m%d_%H%M).jsonl
   ```

2. **Review audit log**
   ```bash
   # Find all events in the incident window
   python -c "
   import json
   for line in open('logs/audit.jsonl'):
       e = json.loads(line)
       print(e['timestamp'], e['event'], e.get('level','info'))
   "
   ```

3. **Check for**
   - Orders placed after anomaly detection
   - Risk violations that were logged but not blocked
   - LLM prompts/responses that led to bad trades
   - Fill quality issues (slippage, partial fills)

4. **Document findings** — timeline, root cause, remediation steps

5. **Update thresholds** if anomaly detection was too sensitive/insensitive

---

## 5. Contact / Escalation

| Severity | Action | Response Time |
|----------|--------|---------------|
| **P0** — Active losses | Kill switch + close positions | Immediate |
| **P1** — System down | Restart server, check logs | < 5 min |
| **P2** — Degraded | Check `/health/detailed`, review logs | < 30 min |
| **P3** — Cosmetic | Log issue for next session | Next session |

---

## 6. Daily Loss Limit

The **only hard global stop** is **-$100 net P&L**.
Once reached, no new trades are accepted regardless of kill switch state.
This is enforced in `app/risk/limits.py::check_daily_loss_limit()`.

