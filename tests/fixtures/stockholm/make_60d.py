"""Build a 60-day Stockholm 5-minute chart from one real Volvo B session: every weekday
before it (skipping Nasdaq Stockholm holidays) gets the same bar shapes with seeded noise,
timestamped at 09:00-17:25 Stockholm time (DST-correct), so the replay pool and the clock
are exercised the way a real range=60d answer would."""
import datetime as dt, gzip, json, random, sys
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src)); r = d["chart"]["result"][0]; q = r["indicators"]["quote"][0]
HOL = {"2026-01-01","2026-01-06","2026-04-03","2026-04-06","2026-05-01","2026-05-14","2026-06-19"}
HALF = {"2026-10-30"}
def off(day):  # Stockholm UTC offset for a date
    def last_sun(m):
        x = dt.date(day.year, m, 31); return x - dt.timedelta(days=(x.weekday() + 1) % 7)
    return 2 if last_sun(3) <= day < last_sun(10) else 1
rng = random.Random(7)
real_day = dt.date(2026, 11, 9)
days, x = [], real_day
while len(days) < 44:
    x -= dt.timedelta(days=1)
    if x.weekday() < 5 and x.isoformat() not in HOL:
        days.append(x)
days = sorted(days) + [real_day]
T, O, H, L, C, V = [], [], [], [], [], []
price = 300.0
for day in days:
    n = 54 if day.isoformat() in HALF else 102   # half day: 09:00-13:25
    base = int((dt.datetime.combine(day, dt.time(9, 0)) - dt.timedelta(hours=off(day)) - dt.datetime(1970, 1, 1)).total_seconds())
    if day == real_day:
        for i in range(102):
            T.append(base + 300 * i); O.append(q["open"][i]); H.append(q["high"][i]); L.append(q["low"][i]); C.append(q["close"][i]); V.append(q["volume"][i])
        continue
    prev = price
    for i in range(n):
        ref = q["close"][i - 1] if i else 311.5
        k = q["close"][i] / ref * (1 + rng.gauss(0, 0.0015))
        o = prev * (q["open"][i] / ref); c = prev * k
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.0008))); l = min(o, c) * (1 - abs(rng.gauss(0, 0.0008)))
        T.append(base + 300 * i); O.append(round(o, 2)); H.append(round(h, 2)); L.append(round(l, 2)); C.append(round(c, 2)); V.append(q["volume"][i])
        prev = c
    price = prev
doc = {"chart": {"result": [{"meta": dict(r["meta"], range="60d"), "timestamp": T,
       "indicators": {"quote": [{"open": O, "high": H, "low": L, "close": C, "volume": V}]}}], "error": None}}
with gzip.open(out, "wt") as fh:
    json.dump(doc, fh)
print(len(days), "sessions,", len(T), "bars")
