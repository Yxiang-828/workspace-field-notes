# Lessons that changed how the work gets done

These notes distill repeated work across agents, media tools, interfaces, and host operations. Each lesson links to the method or code that implements it.

1. **Put durable obligations in a ledger.** Scheduled jobs, reminders, detected defects, and owner decisions all need IDs, states, retry rules, and occurrence history. A prompt can help an agent reason, but it cannot guarantee a wake after a process restart. See [durable-work-ledger](skills/durable-work-ledger/SKILL.md).

2. **Make maintenance runnable without the agent.** Backup, restore, and version listing should be ordinary commands with a daily trigger. An online SQLite database must be copied through its backup API, then read back. A retention test should prove the oldest snapshot is pruned. See [agent-ops-hygiene](skills/agent-ops-hygiene/SKILL.md).

3. **Treat every push as a release decision.** The quality gate must pass against the actual project, and the staged files must pass a secret check. A dated version should be restorable without discarding the current state. The export itself was reviewed this way; raw logs and credential files stayed local. See [agent-ops-hygiene](skills/agent-ops-hygiene/SKILL.md).

4. **Read the owner of a behavior in full.** Documentation and search results locate code; they do not prove what the code does. Trace the entry point, read the whole owning subsystem and its tests, then try to falsify the conclusion. See [repo-absorb](skills/repo-absorb/SKILL.md).

5. **Carry creative judgment forward as data.** A video timeline needs asset facts, a layer by layer decision log, and explicit rejected alternatives. That lets the next pass improve pacing or sound without losing the reason for the previous cut. See [video-editor](skills/video-editor/SKILL.md) and its [factory script](skills/video-editor/scripts/factory.py).

6. **Verify the output at its real viewing size.** A slide's source markup can be valid while its PNG export clips text or loses an image. An interface can pass code checks while failing at narrow width or Windows scaling. Inspect rendered artifacts and the main user path. See [html-deck](skills/html-deck/SKILL.md) and [motion-ui-workbench](skills/motion-ui-workbench/SKILL.md).

7. **Separate reachability from liveness.** A failed SSH connection can mean a down process, a firewall, a wrong route, a bad cable, or a frozen host. Link speed, switch counters, ARP, and TCP refusal answer different questions. Use the cheapest decisive signal first. See [host-liveness-forensics](skills/host-liveness-forensics/SKILL.md).

8. **Keep service adapters small and owner controlled.** A Telegram bot around a local CLI should authenticate the owner, serialize work, redact logs, and hand off result files. It should expose a check command before deployment. See [build-telegram-cli-agent](skills/build-telegram-cli-agent/SKILL.md).

9. **Use media generation where it adds information.** Search stock for findable real imagery. Generate only when the scene is specific or imagined, then appraise the image before placing it. A media recipe and source manifest matter as much as the finished frame. See [image-gen](skills/image-gen/SKILL.md).

10. **Keep API calls narrow and reproducible.** Choose the exact endpoint and small field mask, log enough non-secret request context to repeat the result, and cap bulk calls. See [google-maps-platform](skills/google-maps-platform/SKILL.md).

The [source archive builder](scripts/build_source_archive.py) makes a local ZIP of code, docs, small logs, and other files when a complete workspace archive will not fit on disk. Its `MANIFEST.json` lists exclusions, so a source snapshot is never mistaken for a full backup.
