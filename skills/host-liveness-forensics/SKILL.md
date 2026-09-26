---
name: host-liveness-forensics
description: Decide whether a machine is DOWN, HUNG, or merely UNREACHABLE when you cannot log into it — and find the time of death — using the layers below SSH (switch link, port counters, ARP, firmware logs). Use for "the PC is down", "I can't reach the robot/server", any silent host, any post-mortem of an unattended freeze, and any dead-link/wrong-cable/no-DHCP question (NO-CARRIER, which port is which, is the port or the cable at fault). Includes the multi-homed routing traps that make scans lie.
---

# Host liveness forensics

**"Unreachable" and "down" are different verdicts.** Conflating them sends someone to
power-cycle a healthy machine, or leaves a frozen one sitting for nine hours. This is the
method for separating them without logging in, plus the traps that make the evidence lie.

## The ladder — climb from the bottom, stop at the first honest answer

| Layer | Question it answers | How to ask | What it proves |
|---|---|---|---|
| 1. Switch port link **and speed** | Is the NIC powered, and from which rail? | router/switch: `swconfig dev switch0 show`, `ethtool <if>`, port LED | link up = NIC has power. **Not** that the OS runs. **`1000baseT` = main power; `10baseT` = standby/soft-off** — the speed, not the link, separates hung from off |
| 2. Port counters, twice | Is it *transmitting*? | `swconfig dev switch0 port N get mib` sampled 15 s apart; `ethtool -S` | **Zero RX from the host over 15 s = no running OS.** A live Linux never goes silent (ARP/mDNS/NTP) |
| 3. ARP / neighbour | Is the kernel alive? | Linux `ip neigh`, `/proc/net/arp` (flag `0x2` = complete, `0x0` = incomplete); Windows `netsh interface ip show neighbors` (**Reachable** vs Stale) | ARP is answered by the kernel. A reply = the kernel runs. **Beats firewalls** — it is below them |
| 4. ICMP | — | `ping` | Weakest layer. Many hosts drop ICMP by policy; a timeout proves nothing |
| 5. TCP | Which services live, and is it filtered? | connect to several ports | **RST/refused = host alive, port closed.** Timeout = filtered or dead. The distinction is the evidence |
| 6. Login | Everything else | ssh | — |
| 7. Wake-on-LAN | Is it soft-off with standby power? | `etherwake -i <br> <mac>` from a router on the same L2 | Wakes a soft-off machine; silence means no standby power **or** WoL disabled |

**Verdict table**

| link | transmits | ARP | verdict |
|---|---|---|---|
| down | — | — | powered off, or cable/port fault |
| up | no | no | **hung** (or soft-off with standby power — WoL test separates them) |
| up | yes | yes | alive; everything above is firewall/routing/service |
| up | yes | yes, TCP refused | alive, service down |
| up | yes | yes, TCP timeout | alive, **firewalled** — find the allowed source |

## Ask the infrastructure, not your laptop

The router or switch is a second witness that was awake the whole time, and it is not
subject to your laptop's routing. Harvest, in this order:

- `/proc/net/arp` + `brctl showmacs` / `bridge fdb` — is the host's MAC still being learned, or aged out?
- `logread` / syslog — **the time of death**. Anything the host did periodically (a cron login,
  a DHCP renew, a UPnP mapping) gives you its last heartbeat to the second.
- WAN/uplink state and counters — proves whether the outage was connectivity or the host.
- DHCP leases — who is meant to be on this network at all.

## Traps that have already burned real hours

1. **A subnet route on a VPN silently beats the local cable.** Tailscale (or any subnet router)
   advertising `192.168.x.0/24` outranks your directly-attached interface by metric. Your scan then
   answers about *someone else's* network — and fleets reuse the same internal subnet on every robot,
   so the results look plausible. **Check `Get-NetRoute -DestinationPrefix <subnet>` / `ip route get <ip>`
   before believing any scan**, and bind every probe: `socket.bind((local_ip, 0))`, and for paramiko
   `SSHClient.connect(..., sock=my_bound_socket)`.
2. **Windows `arp -a` only lists hosts you actually exchanged traffic with.** An ICMP sweep populates
   nothing for hosts that drop ICMP, so "empty ARP table" is not "nothing is alive". Force resolution
   with a bound UDP send, then read `netsh interface ip show neighbors` and trust the **state**, not the
   presence of a row.
3. **`netsh interface ip add address` takes the adapter off DHCP** and drops the existing lease. It will
   kill the link you are working over. Use a second adapter.
4. **A firewalled host looks identical to a dead one above layer 3.** If ARP answers but every port times
   out, take the IP of the host it does trust (its gateway, its peer) and retry — that flips the verdict.
5. **A machine hung hard writes nothing to disk.** No panic, no OOM line, no last words. Absence of a crash
   log is evidence *for* a hard lock, not against a crash.

## Base rate before correlation — the discipline that catches false patterns

Before calling "X happened right before every crash" a cause, **measure how often X happens anyway**:

```
journalctl -b -1 | grep -c "<the thing>"      # how many per boot?
journalctl -b -1 -o short-iso | grep "<thing>" | cut -c1-16 | uniq -c | tail
```

Two leads died this way in one session: a cron job that appeared as "the last line before every
freeze" ran **every 30 s**, and an X-server display re-probe that "preceded every crash" fired
**78 lines every minute, 40,169 times per boot**. Anything periodic and frequent will precede
every event you ever investigate. A pattern is only evidence when the base rate is low.

## Post-mortem of a silent freeze — what to collect once it is back

```
journalctl --list-boots                    # crash vs clean shutdown; count the repeats
journalctl -b -1 -n 40                     # last words (often nothing useful)
journalctl -k -b -1 | grep -iE "oom|panic|mce|hardware error|thermal|hung task|soft lockup|BUG"
dmesg | grep -iE "BERT|machine check|edac"                 # firmware's own crash record
cat /sys/devices/system/edac/mc/mc*/{ce,ue}_count          # memory errors
sar -f /var/log/sysstat/sa<DD> -s <HH:MM>   # CPU/mem/load right up to the hang (survives it)
sar -r / -q -f ...                          # memory and run-queue
grep -A2 "^Start-Date" /var/log/apt/history.log   # what changed before instability began
sensors; smartctl -a /dev/<disk>
```

**If all of that is clean, stop guessing and instrument for the next one:**
- **Hardware watchdog** (`modprobe iTCO_wdt`, systemd `RuntimeWatchdogSec=30`) — turns a nine-hour
  hang into a one-minute reboot.
- **netconsole** to a machine on the same LAN — the kernel's last words leave the box before it dies,
  which is the only way to catch a hang that never reaches disk.
- Strip anything that has no business on an unattended box (a desktop session, an idle GUI), then
  re-test one variable at a time.

## Link, cable and port faults

When the answer is "link up but silent", or the host is unreachable and wiring is in
question, use this checklist:

- negotiated **speed as a power-state discriminator** (1000baseT = running or hung · 10baseT = soft-off)
- `UP` vs `NO-CARRIER` vs `LOWER_UP` — why `ip link set up` fixes nothing
- mapping cable → interface by **unplug-and-watch** on kernel link events
- wiring that is the exact opposite of the IP config and still works, because a neighbour forwards
- **one variable at a time**: reseat → known-good cable → different port → then suspect the NIC
- error counters that separate a **dead port** from an **intermittent contact**
- switch MAC tables: `PORTMAP` is a bitmask, and several MACs on one port = a downstream switch
- DHCP `OFFER` with no `REQUEST`/`ACK` = a **one-directional** link fault, not a DHCP problem
- why two default routes are **not** failover when the far host hangs with its link up
- RUTX11 panel → `swconfig` port mapping, and LAN/WAN being configured rather than sensed
