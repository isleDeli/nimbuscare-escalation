#!/usr/bin/env python3
"""Score the billing-support agent against evals/cases/*.

Usage (from anywhere):
    python3 evals/score.py                 # all cases
    python3 evals/score.py --case 04       # cases whose folder name contains "04"
    python3 evals/score.py --verbose       # also print each scored reply

For every case it runs, from the project root,
    ./run.sh --json --conversation <case>/conversation.txt --fixtures <case>/fixtures.json
saves the raw output to evals/results/<case>.json, and compares each customer
turn with <case>/expected.json. Six things are scored separately:

    decision   decision is one of the accepted values
    policy     governing_policy has all_of / at least one any_of / none of none_of (by rule number)
    article    driving_article is in the accepted set (null allowed where listed)
    numbers    every expected number or date appears among the values in `computed`
    phrases    reply matches no forbidden pattern and every required pattern
    handoff    escalate_to names Tier 2 / is null, or the reply names the right team

Only fields present in expected.json for a turn are scored.

A seventh group, "sources", proves the agent uses only the company policy and
knowledge base and never the network. It has four parts and fails the run if
any part fails:

    1 static     run.sh and agent/**: no network / model-client imports or calls, no URLs
    2 network    every case re-run via evals/sandbox_child.py with sockets replaced by
                 functions that record and raise: zero attempts, output identical
    3 files      in that same run every file open is recorded: only the two company
                 documents, the case's conversation and fixtures, and the agent's own
                 source (plus the Python installation itself) may be opened
    4 quotes     every `evidence` string is verbatim in one of the two documents, and
                 every rule / article id in the output exists in them
Exit status is 0 only if every check passes. Python 3 standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import sysconfig
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(HERE, "cases")
RESULTS = os.path.join(HERE, "results")
DIMS = ["decision", "policy", "article", "numbers", "phrases", "handoff"]
POLICY_DOC = os.path.join(ROOT, "data", "policy-bil-pol-014.md")
KB_DOC = os.path.join(ROOT, "data", "kb-billing-credits.md")
SANDBOX = os.path.join(HERE, "sandbox_child.py")

NET_PATTERNS = [
    ("network/model import", r"^\s*(?:import|from)\s+(socket|ssl|urllib\d?|http|requests|httpx|aiohttp|ftplib|smtplib|"
                             r"webbrowser|telnetlib|xmlrpc|websockets?|anthropic|openai|boto3|grpc|pycurl)\b"),
    ("network/model call", r"\b(socket|ssl|urllib\d?|requests|httpx|aiohttp|ftplib|smtplib|webbrowser|anthropic|openai)\s*\."),
    ("dynamic import", r"__import__\s*\(|importlib\b"),
    ("process start", r"^\s*(?:import|from)\s+subprocess\b|\bsubprocess\s*\.|\bos\.(system|popen|exec\w*|spawn\w*)\s*\("),
    ("external command", r"(?<![\w-])(curl|wget|claude|codex|nc|ssh|scp|ollama)(?![\w-])"),
    ("URL", r"\b(?:https?|ftp|wss?)://"),
]


def static_scan(run_sh):
    """Part 1: list (file, line, kind, text) for every suspicious line."""
    files = [run_sh]
    for base, dirs, names in os.walk(os.path.join(ROOT, "agent")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        files += [os.path.join(base, n) for n in sorted(names) if not n.endswith((".pyc", ".pyo"))]
    hits = []
    for path in files:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError as e:
            hits.append((os.path.relpath(path, ROOT), 0, "unreadable", str(e)))
            continue
        for no, line in enumerate(lines, 1):
            for kind, pat in NET_PATTERNS:
                if re.search(pat, line):
                    hits.append((os.path.relpath(path, ROOT), no, kind, line.strip()[:120]))
    return files, hits


def python_dirs():
    dirs = {sys.prefix, sys.base_prefix, sys.exec_prefix, sys.base_exec_prefix, os.path.dirname(os.__file__)}
    dirs.update(v for k, v in sysconfig.get_paths().items() if v)
    return sorted({os.path.realpath(d) for d in dirs if d})


def sandbox_run(case_dir, timeout):
    """Parts 2 and 3: same entry point as run.sh (python3 -m agent) with sockets disabled."""
    fd, log_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    conv = os.path.join(case_dir, "conversation.txt")
    fix = os.path.join(case_dir, "fixtures.json")
    cmd = [sys.executable, SANDBOX, log_path, "--json", "--conversation", conv, "--fixtures", fix]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        with open(log_path, encoding="utf-8") as f:
            log = json.load(f)
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        return None, None, "sandbox run failed: %s" % e
    finally:
        try:
            os.remove(log_path)
        except OSError:
            pass
    if p.returncode != 0:
        return p.stdout, log, "sandbox exit %d: %s" % (p.returncode, p.stderr.strip()[-300:])
    return p.stdout, log, None


def classify_opens(log, case_dir):
    """Return (knowledge files read, violations). Knowledge = anything that is not the
    agent's own code, the Python installation, or this case's conversation/fixtures."""
    allowed_docs = {os.path.realpath(POLICY_DOC), os.path.realpath(KB_DOC)}
    case_files = {os.path.realpath(os.path.join(case_dir, n)) for n in ("conversation.txt", "fixtures.json")}
    agent_dir = os.path.realpath(os.path.join(ROOT, "agent")) + os.sep
    own = {os.path.realpath(SANDBOX)}
    pydirs = [d + os.sep for d in python_dirs()]
    docs, bad = set(), set()
    for o in log.get("opens", []):
        path, mode = o["path"], o.get("mode") or "r"
        writing = any(c in mode for c in "wax+")
        if path.startswith(agent_dir):
            if writing and "__pycache__" not in path:
                bad.add("WRITE " + path)
            continue
        if path in own or any(path.startswith(d) for d in pydirs) or path == os.devnull:
            continue
        if writing:
            bad.add("WRITE " + path)
        elif path in allowed_docs:
            docs.add(path)
        elif path not in case_files:
            bad.add("READ " + path)
    return docs, bad


def norm_quote(text):
    text = re.sub(r"[*`]", "", str(text))          # markdown emphasis and code marks
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(?:\.\.\.|\u2026)\s*|\s*(?:\.\.\.|\u2026)$", "", text)
    return text.strip().strip("\"\u201c\u201d").strip()


def load_sources():
    with open(POLICY_DOC, encoding="utf-8") as f:
        policy = f.read()
    with open(KB_DOC, encoding="utf-8") as f:
        kb = f.read()
    rules = set(re.findall(r"^## Rule (\d+)\b", policy, flags=re.M))
    articles = set(re.findall(r"^### (KB-\d+)\b", kb, flags=re.M))
    return [norm_quote(policy), norm_quote(kb)], rules, articles


def check_quotes(out, sources):
    """Part 4 for one case: list of problems."""
    texts, rules, articles = sources
    problems = []
    for t in (out or {}).get("turns") or []:
        n = t.get("turn")
        ev = t.get("evidence") or []
        if isinstance(ev, str):
            ev = [ev]
        for q in ev:
            q = q.get("quote", q.get("text", "")) if isinstance(q, dict) else q
            nq = norm_quote(q)
            if not nq or not any(nq in src for src in texts):
                problems.append("turn %s: evidence not verbatim in policy or knowledge base: %r" % (n, str(q)[:160]))
        ids = []
        for key in ("governing_policy", "rejected_policy", "retrieved"):
            v = t.get(key) or []
            ids += [("%s" % key, i.get("id") if isinstance(i, dict) else i) for i in (v if isinstance(v, list) else [v])]
        if t.get("driving_article") is not None:
            ids.append(("driving_article", t.get("driving_article")))
        for key, raw in ids:
            m_rule = re.fullmatch(r"\s*(?:BIL-POL-014\s+)?Rule\s*(\d+)\s*[a-d]?\s*", str(raw), flags=re.I)
            m_kb = re.fullmatch(r"\s*(KB-\d+)\s*", str(raw))
            if not ((m_rule and m_rule.group(1) in rules) or (m_kb and m_kb.group(1) in articles)):
                problems.append("turn %s: %s id %r is not a Rule or KB id in the documents" % (n, key, raw))
    return problems


def rule_numbers(value):
    """['Rule 3', {'id': 'Rule 4b'}] -> {'3', '4'}"""
    out = set()
    if value is None:
        return out
    if not isinstance(value, (list, tuple)):
        value = [value]
    for item in value:
        if isinstance(item, dict):
            item = item.get("id", "")
        out.update(re.findall(r"Rule\s*(\d+)", str(item), flags=re.I))
    return out


def article_id(value):
    if isinstance(value, dict):
        value = value.get("id")
    if value is None:
        return None
    m = re.search(r"KB-\d+", str(value))
    return m.group(0) if m else (str(value) or None)


def leaves(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from leaves(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from leaves(v)
    else:
        yield value


def as_number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.fullmatch(r"\s*\$?\s*(-?\d[\d,]*(?:\.\d+)?)\s*", value)
        if m:
            return float(m.group(1).replace(",", ""))
    return None


def value_present(expected, computed_leaves):
    for got in computed_leaves:
        if isinstance(expected, str):
            if isinstance(got, str) and expected in got:
                return True
        else:
            n = as_number(got)
            if n is not None and abs(n - float(expected)) < 0.005:
                return True
    return False


def check_turn(exp, got):
    """Return {dim: (ok, detail)} for the dimensions this turn scores."""
    res = {}
    reply = str(got.get("reply") or "")

    if "decision" in exp:
        accepted = exp["decision"] if isinstance(exp["decision"], list) else [exp["decision"]]
        actual = got.get("decision")
        res["decision"] = (actual in accepted, "expected %s, got %r" % (" or ".join(accepted), actual))

    if "governing_policy" in exp:
        want = exp["governing_policy"]
        have = rule_numbers(got.get("governing_policy"))
        problems = []
        missing = rule_numbers(want.get("all_of")) - have
        if missing:
            problems.append("missing Rule " + ", Rule ".join(sorted(missing)))
        anyof = rule_numbers(want.get("any_of"))
        if anyof and not (anyof & have):
            problems.append("needs one of Rule " + ", Rule ".join(sorted(anyof)))
        bad = rule_numbers(want.get("none_of")) & have
        if bad:
            problems.append("must not include Rule " + ", Rule ".join(sorted(bad)))
        res["policy"] = (not problems, "%s; got %r" % ("; ".join(problems) or "ok", got.get("governing_policy")))

    if "driving_article" in exp:
        actual = article_id(got.get("driving_article"))
        accepted = exp["driving_article"]
        res["article"] = (actual in accepted,
                          "expected %s, got %r" % (" or ".join("null" if a is None else a for a in accepted), actual))

    if "computed" in exp:
        got_leaves = list(leaves(got.get("computed") or {}))
        missing = [e["label"] for e in exp["computed"]
                   if not any(value_present(v, got_leaves) for v in e["any_of"])]
        res["numbers"] = (not missing, "not in computed: %s; computed was %s"
                          % (", ".join(missing) or "-", json.dumps(got.get("computed"), sort_keys=True)))

    if "computed_if_answer" in exp and got.get("decision") == "answer":
        got_leaves = list(leaves(got.get("computed") or {}))
        missing = [e["label"] for e in exp["computed_if_answer"]
                   if not any(value_present(v, got_leaves) for v in e["any_of"])]
        res["numbers"] = (not missing, "answered, but not in computed: %s; computed was %s"
                          % (", ".join(missing) or "-", json.dumps(got.get("computed"), sort_keys=True)))

    if "reply_must_not_match" in exp or "reply_must_match" in exp:
        problems = []
        for pat in exp.get("reply_must_not_match", []):
            m = re.search(pat, reply, flags=re.I)
            if m:
                problems.append("forbidden %r found: %r" % (pat, reply[max(0, m.start() - 40):m.end() + 40]))
        for pat in exp.get("reply_must_match", []):
            if not re.search(pat, reply, flags=re.I):
                problems.append("required %r not in reply" % pat)
        res["phrases"] = (not problems, "; ".join(problems) or "ok")

    if "handoff" in exp:
        h = exp["handoff"]
        esc = got.get("escalate_to")
        problems = []
        if "escalate_to_contains" in h and h["escalate_to_contains"].lower() not in str(esc or "").lower():
            problems.append("escalate_to should name %r, got %r" % (h["escalate_to_contains"], esc))
        if h.get("escalate_to_not_null") and esc in (None, "", []):
            problems.append("escalate_to should name who takes over, got %r" % (esc,))
        if h.get("escalate_to_null") and esc not in (None, "", []):
            problems.append("escalate_to should be null, got %r" % (esc,))
        if "reply_or_escalate_to_contains_any" in h:
            hay = (reply + " " + str(esc or "")).lower()
            if not any(w.lower() in hay for w in h["reply_or_escalate_to_contains_any"]):
                problems.append("reply/escalate_to should name one of %r" % h["reply_or_escalate_to_contains_any"])
        res["handoff"] = (not problems, "; ".join(problems) or "ok")
    return res


def run_agent(run_sh, case_dir, timeout):
    run_agent.last_stdout = None
    cmd = [run_sh, "--json", "--conversation", os.path.join(case_dir, "conversation.txt"),
           "--fixtures", os.path.join(case_dir, "fixtures.json")]
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "could not run: %s" % e
    run_agent.last_stdout = p.stdout
    if p.returncode != 0:
        return None, "exit %d: %s" % (p.returncode, (p.stderr or p.stdout).strip()[-400:])
    try:
        return json.loads(p.stdout), None
    except ValueError as e:
        return None, "stdout is not JSON (%s): %s" % (e, p.stdout.strip()[:200])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--case", help="only cases whose folder name contains this text")
    ap.add_argument("--run-sh", default=os.path.join(ROOT, "run.sh"))
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--verbose", action="store_true", help="print each scored reply")
    args = ap.parse_args()

    if not os.path.exists(args.run_sh):
        print("run.sh not found at %s: nothing was scored." % args.run_sh)
        return 2
    names = sorted(n for n in os.listdir(CASES)
                   if os.path.isdir(os.path.join(CASES, n)) and (not args.case or args.case in n))
    if not names:
        print("no cases matched")
        return 2
    os.makedirs(RESULTS, exist_ok=True)

    totals = {d: [0, 0] for d in DIMS}
    rows, failures, summary = [], [], []
    sources = load_sources()
    src = {"network": [], "files": [], "quotes": [], "docs_read": set(), "runs": 0}
    for name in names:
        case_dir = os.path.join(CASES, name)
        with open(os.path.join(case_dir, "expected.json"), encoding="utf-8") as f:
            expected = json.load(f)
        out, err = run_agent(args.run_sh, case_dir, args.timeout)
        if out is not None:
            with open(os.path.join(RESULTS, name + ".json"), "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2)
        normal_stdout = run_agent.last_stdout
        sb_stdout, sb_log, sb_err = sandbox_run(case_dir, args.timeout)
        src["runs"] += 1
        if sb_log is None:
            src["network"].append("%s: %s" % (name, sb_err))
            src["files"].append("%s: %s" % (name, sb_err))
        else:
            for a in sb_log["network_attempts"] + sb_log["process_attempts"]:
                src["network"].append("%s: attempted %s %s" % (name, a["call"], a["args"]))
            if sb_err:
                src["network"].append("%s: %s" % (name, sb_err))
            if sb_stdout != normal_stdout:
                src["network"].append("%s: output with network disabled differs from the normal run" % name)
            docs, bad = classify_opens(sb_log, case_dir)
            src["docs_read"] |= docs
            src["files"] += ["%s: %s" % (name, b) for b in sorted(bad)]
        if out is None:
            src["quotes"].append("%s: no output to check (%s)" % (name, err))
        src["quotes"] += ["%s: %s" % (name, q) for q in check_quotes(out, sources)]
        turns = {}
        if isinstance(out, dict):
            for i, t in enumerate(out.get("turns") or [], start=1):
                if isinstance(t, dict):
                    turns[t.get("turn", i)] = t
        per = {d: [0, 0] for d in DIMS}
        for exp in expected["turns"]:
            got = turns.get(exp["turn"])
            if got is None:
                # Count every scored dimension of a missing turn as failed.
                res = {d: (False, err or "turn %d missing from output" % exp["turn"])
                       for d in check_turn(exp, {})}
                got = {}
            else:
                res = check_turn(exp, got)
                if exp.get("time") and got.get("time") not in (None, exp["time"]):
                    res = {d: (False, "turn %d is time %r, expected %r (turn numbering differs)"
                               % (exp["turn"], got.get("time"), exp["time"])) for d in res}
            if args.verbose:
                print("--- %s turn %d [%s] %s\n    %s" % (name, exp["turn"], got.get("decision"),
                                                          got.get("driving_article"), got.get("reply")))
            for d, (ok, detail) in res.items():
                per[d][1] += 1
                totals[d][1] += 1
                if ok:
                    per[d][0] += 1
                    totals[d][0] += 1
                else:
                    failures.append({"case": name, "turn": exp["turn"], "time": exp.get("time"),
                                     "check": d, "detail": detail, "note": exp.get("note", ""),
                                     "customer": got.get("customer"), "reply": got.get("reply")})
        passed = sum(p for p, _ in per.values())
        total = sum(t for _, t in per.values())
        rows.append((name, per, passed, total))
        summary.append({"case": name, "passed": passed, "total": total,
                        "by_check": {d: per[d] for d in DIMS}, "run_error": err})

    scanned, hits = static_scan(args.run_sh)
    parts = [
        ("1 static scan: no network or model-client code in run.sh and agent/ (%d files)" % len(scanned),
         ["%s:%d: %s: %s" % h for h in hits]),
        ("2 run time: no network or process attempt with sockets disabled, output identical (%d runs)" % src["runs"],
         src["network"]),
        ("3 files: knowledge read only from the two company documents (read: %s)"
         % (", ".join(sorted(os.path.relpath(d, ROOT) for d in src["docs_read"])) or "none"), src["files"]),
        ("4 quotes: every evidence string verbatim, every rule/article id real", src["quotes"]),
    ]
    src_pass = sum(1 for _, probs in parts if not probs)
    for title, probs in parts:
        for pr in probs:
            failures.append({"case": "sources", "turn": "-", "time": None, "check": title.split(":")[0],
                             "detail": pr, "note": "", "customer": None, "reply": None})

    cell = lambda pt: ("%d/%d" % tuple(pt)) if pt[1] else "-"
    width = max(len(n) for n in names + ["TOTAL"])
    head = "%-*s  " % (width, "case") + "  ".join("%-8s" % d for d in DIMS) + "  all     result"
    print(head)
    print("-" * len(head))
    for name, per, passed, total in rows:
        print("%-*s  " % (width, name) + "  ".join("%-8s" % cell(per[d]) for d in DIMS)
              + "  %-6s  %s" % ("%d/%d" % (passed, total), "PASS" if passed == total else "FAIL"))
    print("-" * len(head))
    gp = sum(p for p, _ in totals.values())
    gt = sum(t for _, t in totals.values())
    cases_ok = sum(1 for r in rows if r[2] == r[3])
    print("%-*s  " % (width, "TOTAL") + "  ".join("%-8s" % cell(totals[d]) for d in DIMS)
          + "  %-6s  %d/%d cases pass" % ("%d/%d" % (gp, gt), cases_ok, len(rows)))
    print("%-*s  %d/%d parts pass" % (width, "sources", src_pass, len(parts)))
    print("\nchecks passed: %d/%d (%.1f%%)" % (gp, gt, 100.0 * gp / gt if gt else 0.0))
    print("sources check: %s (%d/%d parts)" % ("PASS" if src_pass == len(parts) else "FAIL", src_pass, len(parts)))
    for title, probs in parts:
        print("  [%s] %s" % ("PASS" if not probs else "FAIL", title))

    if failures:
        print("\nFAILURES")
        for f in failures:
            print("- %s | turn %s %s | %s | %s" % (f["case"], f["turn"],
                                                    "[%s]" % f["time"] if f["time"] else "", f["check"], f["detail"]))
    with open(os.path.join(RESULTS, "summary.json"), "w", encoding="utf-8") as f:
        json.dump({"checks_passed": gp, "checks_total": gt, "cases_passed": cases_ok,
                   "cases_total": len(rows), "by_check": totals, "cases": summary,
                   "sources": [{"part": t, "pass": not pr, "problems": pr} for t, pr in parts],
                   "failures": failures}, f, indent=2)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
