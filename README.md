# Control Core

Control Core is a daemon-based automation framework that lets you install “scripts” (small Python tasks) and run them automatically based on **time schedules** or **system events** (e.g., app open/close, idle, network changes). It’s designed to centralize recurring maintenance, data acquisition, and workflow automation into one consistent system.

---

## Why...

As projects grow, automation tends to fragment:
- ad-hoc cron jobs
- one-off scripts
- manual “run this when I open X”
- scattered logs and no shared tooling

**Control Core solves this by providing one place to:**
- install & manage scripts
- set schedules and event triggers
- run and inspect execution history
- enforce safety controls (cooldowns / reentrancy)
- extend the platform with new triggers and pipelines later

---

## What it does (basics)

**Working triggers**
- **Time scheduling**: daily times, optional day-of-week, optional month/day-of-month constraints  
- **Interval scheduling**: run every N seconds  
- **Event triggers**:
  - `app_open`, `app_close` (filterable by app name)
  - `idle` (run when idle ≥ threshold)
  - `network_up`, `network_down`
- **File watch**: run when a file changes (poll-based)

**Operational features**
- Persistent daemon loop (runs continuously)
- Script enable/disable and manual triggering
- Structured JSONL logging
- CLI tooling for status/history/stats/export
- Debounce + cooldown protections to prevent duplicate event firing

---

## System design (overall architecture)

Control Core is intentionally structured like a small internal platform:

- **Registry / Manifest-driven scripts**
  - Each script is a folder with a `script.json` manifest defining:
    - `id`, `entrypoint`, `enabled`, `schedule`
- **Daemon runtime**
  - A single long-running process detects events + checks schedules
  - Executes scripts via a runner with structured payloads
- **Scheduler state**
  - Persistent state stored on disk so scheduled jobs don’t “forget” what fired after restart
- **Event engine**
  - Detects app open/close by sampling running GUI applications (macOS)
  - Detects idle time via system APIs
  - Detects network state changes by checking local routing IP
  - Applies debouncing/cooldowns to avoid rapid duplicate triggers

---

## Tradeoffs

This project attemps to make some optimizations but still has some tradeoffs

- **Polling vs OS hooks**
  - Uses a lightweight polling loop (simple, reliable, portable enough for MVP)
  - Leaves room to swap in OS-level event subscriptions later if needed

- **GUI-app focus vs full process monitoring**
  - App events are based on GUI application processes to avoid noise from background helpers
  - Process-level monitoring is intentionally deferred as a future security-focused extension

- **Debounce + cooldown**
  - Debouncing reduces duplicate “same app” events caused by transient helpers
  - Per-script cooldowns prevent rapid repeated execution during event storms

- **Manifest schema design**
  - Schedules are normalized on load to enforce consistency even if users edit JSON manually

---

## Quickstart

### Run the daemon
```bash
python -m control_core.daemon
