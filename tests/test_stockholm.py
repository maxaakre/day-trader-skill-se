"""The Stockholm profile (TRADER_MARKET=SE): clock, calendar, symbols, kronor and the whole
one-trade path on a real Volvo B session (2026-11-09, Yahoo 5-minute bars)."""

import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest

from _load import FIX, ROOT, load

SE = os.path.join(FIX, "stockholm")
VOLV = os.path.join(SE, "VOLV-B.ST-2026-11-09-5m.json")
VOLV60 = os.path.join(SE, "VOLV-B.ST-60d5m-synthetic.json.gz")


def run(folder, script, *args, cwd):
    env = dict(os.environ, TRADER_MARKET="SE")
    p = subprocess.run([sys.executable, os.path.join(ROOT, folder, script)] + list(args),
                       cwd=cwd, env=env, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


class Clock(unittest.TestCase):
    def setUp(self):
        self.m = load("trader-alerts", "alerts", market="SE")

    def test_summer_and_winter_offset(self):
        u = datetime.datetime
        self.assertEqual(self.m.eastern_offset(u(2026, 7, 1, 12)), 2)
        self.assertEqual(self.m.eastern_offset(u(2026, 11, 9, 12)), 1)
        # summer time ends 01:00 UTC on the last Sunday of October (2026-10-25)
        self.assertEqual(self.m.eastern_offset(u(2026, 10, 25, 0, 59)), 2)
        self.assertEqual(self.m.eastern_offset(u(2026, 10, 25, 1, 0)), 1)
        # and starts 01:00 UTC on the last Sunday of March (2026-03-29)
        self.assertEqual(self.m.eastern_offset(u(2026, 3, 29, 0, 59)), 1)
        self.assertEqual(self.m.eastern_offset(u(2026, 3, 29, 1, 0)), 2)

    def test_session_hours_holidays_and_half_days(self):
        d = datetime.date
        self.assertEqual(self.m.session(d(2026, 11, 9)), (datetime.time(9, 0), datetime.time(17, 30)))
        self.assertEqual(self.m.session(d(2026, 4, 30)), (datetime.time(9, 0), datetime.time(13, 0)))
        for closed in ("2026-01-06", "2026-06-19", "2026-12-24", "2026-12-31", "2027-03-26"):
            self.assertIsNone(self.m.session(d.fromisoformat(closed)), closed)
        # US holidays are ordinary trading days in Stockholm
        self.assertIsNotNone(self.m.session(d(2026, 11, 26)))

    def test_local_time_round_trip(self):
        utc = self.m.parse_now("2026-11-09 09:20")
        self.assertEqual(utc, datetime.datetime(2026, 11, 9, 8, 20))


class Symbols(unittest.TestCase):
    def test_yahoo_symbols(self):
        m = load("trader-scanner", "scan", market="SE")
        self.assertEqual(m.to_yahoo("VOLV-B"), "VOLV-B.ST")
        self.assertEqual(m.to_yahoo("volv b"), "VOLV-B.ST")
        self.assertEqual(m.to_yahoo("ERIC-B.ST"), "ERIC-B.ST")
        self.assertEqual(m.to_yahoo("AZN"), "AZN.ST")

    def test_universe_file(self):
        with open(os.path.join(ROOT, "trader-scanner", "universe_se.json"), encoding="utf-8") as fh:
            doc = json.load(fh)
        syms = [s["symbol"] for s in doc["stocks"]]
        self.assertEqual(len(syms), len(set(syms)))
        self.assertTrue(all(s.endswith(".ST") for s in syms))
        segs = {s["segment"] for s in doc["stocks"]}
        self.assertEqual(segs, {"Large Cap", "Mid Cap"})
        for must in ("VOLV-B.ST", "ERIC-B.ST", "SSAB-B.ST", "NDA-SE.ST", "AZN.ST", "INVE-B.ST"):
            self.assertIn(must, syms)

    def test_risk_accepts_swedish_tickers(self):
        m = load("trader-risk", "check", market="SE")
        for ok in ("VOLV-B.ST", "VOLV-B", "TEL2-B.ST", "8TRA.ST", "AZN.ST"):
            self.assertTrue(m.TICKER.match(ok), ok)
        self.assertFalse(m.TICKER.match("BTC/USD"))

    def test_kronor(self):
        self.assertEqual(load("trader-risk", "check", market="SE").money(58.75), "58.75 kr")
        self.assertEqual(load("trader-budget", "size", market="SE").money(20000), "20,000 kr")
        self.assertEqual(load("trader-risk", "check", market="US").money(58.75), "$58.75")


class OneTrade(unittest.TestCase):
    """scanner -> entry -> exit -> timemachine -> budget -> risk -> broker, offline."""

    def test_volvo_b_opening_range_breakout(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "trader"))
            with open(os.path.join(ROOT, "trader-budget", "config.example.se.json")) as fh:
                cfg = fh.read()
            with open(os.path.join(d, "trader", "config.json"), "w") as fh:
                fh.write(cfg)

            rc, out = run("trader-scanner", "scan.py", "orb", "--offline", VOLV, "--now", "2026-11-09 09:40", cwd=d)
            self.assertEqual(rc, 0, out)
            self.assertIn("09:20  VOLV-B.ST  313.30 kr", out)
            self.assertIn("(9:00 to 09:15)", out)

            rc, out = run("trader-entry", "entry.py", "check", "VOLV-B", "--offline", VOLV,
                          "--now", "2026-11-09 09:21", "--write", cwd=d)
            self.assertEqual(rc, 0, out)
            self.assertIn("TRIGGERED 09:20 at 313.30 kr", out)

            rc, out = run("trader-exit", "exit.py", "plan", "--from", "trader/entry.json", "--offline", VOLV,
                          "--now", "2026-11-09 09:21", "--write", cwd=d)
            self.assertEqual(rc, 0, out)
            plan = json.load(open(os.path.join(d, "trader", "plan.json")))
            self.assertEqual((plan["entry"], plan["stop"], plan["target"], plan["flat_by"]),
                             (313.3, 312.05, 315.8, "17:15"))

            rc, out = run("trader-timemachine", "timemachine.py", "run", "--offline", VOLV60,
                          "--now", "2026-11-09 09:21", cwd=d)
            self.assertEqual(rc, 0, out)
            self.assertIn("09:20 to 17:30 (98 five-minute bars)", out)
            self.assertIn("Left out 1 short session(s) (half days or gaps): 2026-10-30", out)

            rc, out = run("trader-budget", "size.py", "--now", "2026-11-09 09:21", "--write", cwd=d)
            self.assertEqual(rc, 0, out)
            self.assertIn("Size: 47 shares of VOLV-B.ST = 14,725.10 kr", out)

            rc, out = run("trader-risk", "check.py", "--now", "2026-11-09 09:21", cwd=d)
            self.assertEqual(rc, 0, out)
            self.assertIn("max loss 58.75 kr (limit 200 kr)", out)

            rc, out = run("trader-broker", "ticket.py", "show", "--now", "2026-11-09 09:22", cwd=d)
            self.assertEqual(rc, 0, out)
            self.assertIn("manual (you place it)", out)
            self.assertIn("BUY 47 VOLV B", out)
            self.assertIn("stop-loss SELL of 47 VOLV B, trigger 312.05", out)
            self.assertNotIn("place_stock_order with exactly", out)

    def test_risk_blocks_after_the_entry_window(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "trader"))
            with open(os.path.join(d, "trader", "config.json"), "w") as fh:
                json.dump({"budget": 20000}, fh)
            run("trader-entry", "entry.py", "check", "VOLV-B", "--offline", VOLV, "--now", "2026-11-09 09:21",
                "--write", cwd=d)
            run("trader-exit", "exit.py", "plan", "--from", "trader/entry.json", "--offline", VOLV,
                "--now", "2026-11-09 09:21", "--write", cwd=d)
            rc, out = run("trader-budget", "size.py", "--now", "2026-11-09 09:21", "--write", cwd=d)
            self.assertEqual(rc, 0, out)
            rc, out = run("trader-risk", "check.py", "--now", "2026-11-09 17:05", cwd=d)
            self.assertNotEqual(rc, 0, out)
            self.assertIn("BLOCK", out)
            self.assertIn("17:00", out)


class Alerts(unittest.TestCase):
    def test_clock_on_julafton(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("trader-alerts", "alerts.py", "clock", "--now", "2026-12-24 10:00", cwd=d)
            self.assertIn("julafton", out)
            self.assertIn("Next open: 2026-12-28 09:00 Stockholm", out)

    def test_stooq_is_refused(self):
        m = load("trader-alerts", "alerts", market="SE")
        with self.assertRaises(m.AlertError):
            m.stooq_url("VOLV-B.ST")


class News(unittest.TestCase):
    def test_report_dates_and_no_sec(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = run("trader-news", "news.py", "--tickers", "VOLV-B", "--no-moves", "--offline", d,
                          "--now", "2027-01-20T09:00:00Z", "--dry-run", cwd=d)
            self.assertIn("Report: VOLV-B.ST Volvo B on 2027-01-27  (in 7 days)", out)
            self.assertNotIn("SEC", out)


if __name__ == "__main__":
    unittest.main()
