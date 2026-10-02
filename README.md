[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/yw6HfzWl)
# ECE 60827 — Project: Register File Caching and Two-Level Warp Scheduling

---

## Background

Read the paper: M. Gebhart, D. Johnson, D. Tarjan, S. Keckler, W. Dally, E. Lindholm, and K. Skadron, "Energy-efficient Mechanisms for Managing Thread Context in Throughput Processors," ISCA 2011.

In this project you will implement two microarchitectural enhancements in GPGPU-Sim and evaluate them on the Rodinia benchmark suite:

1. **Register File Cache (RFC)** — a small, per-warp FIFO cache that sits between the operand collector and the main register file (MRF). Recently written destination registers are cached so that subsequent reads can be served without accessing the MRF, reducing bank conflicts and energy.

2. **Two-Level Warp Scheduler + RFC Integration** — GPGPU-Sim already contains a two-level warp scheduler (`two_level_active_scheduler`). You will integrate the RFC with this scheduler so that when a warp is demoted from the active set to the pending set, its RFC entries are flushed back to the MRF.

Submit your report and code on Brightspace.

---

## Academic Integrity and AI Usage Policy

You are **allowed** to use AI tools (e.g. ChatGPT, Claude, Copilot, etc.) for this assignment. AI is becoming a standard part of how software is written, and learning to use it effectively is a valuable skill.

**You must declare your choice (AI or no AI) in advance — within one week of the assignment being released.** If you change your mind later, you must email the instructors to explain why and request approval before proceeding.

However, there are boundaries:

**AI may be used for:**
- Understanding the simulator codebase (e.g. "what does this function do?", "how does the operand collector work in GPGPU-Sim?")
- Navigating and searching the code (e.g. asking AI to explain call chains or data structures)
- Generating plots and figures from your collected data
- Writing scripts for data collection or post-processing
- Writing the RFC and scheduler integration implementation code

**AI may NOT be used for:**
- Writing the analysis or explanations in your report (the thinking must be yours)
- Writing the research proposal (Part 2, if applicable)

The goal of this assignment is for **you** to understand GPU microarchitecture by reading and modifying simulator code. If AI writes all the code and analysis for you, you learn nothing.

### If You Used AI: Additional Requirements (Part 2)

If you used AI tools for **any part** of this assignment (implementation, code navigation, plotting, etc.), you must complete **all** of the following additional requirements. If you did not use AI at all, you may skip Part 2.

#### (A) Research Proposal (2 pages)

Using AI as a research collaborator is likely the future of doing research in computer architecture. To practice this skill:

1. Feel free to read this paper for inspiration: [Computer Architecture's AlphaZero Moment: Automated Discovery in an Encircled World](https://arxiv.org/abs/2604.03312)
2. Using AI as a brainstorming partner, **come up with a research question** related to GPU microarchitecture (it can build on the RFC/scheduling work from this project, or be a different topic).
3. Write a **2-page research proposal** that includes:
   - A clear problem statement
   - Motivation: include **data** (from your simulations, the paper, or other sources) showing why this problem matters
   - A proposed approach
   - Expected outcomes

**The proposal text must be written entirely by you — no AI-generated prose.** You may use AI to brainstorm ideas, find related work, or discuss feasibility, but the writing must be your own.

#### (B) AI Usage Documentation

Include a section in your report (does not count toward any page limit) describing:

1. What AI tools you used
2. What you used them for (be specific — e.g. "asked Claude to explain the operand collector pipeline", "used Copilot for the RFC FIFO data structure")
3. How it helped (or didn't help) your understanding

#### (C) Chat History

Attach your AI chat history as a supplementary file.

- **Claude Code**: conversation logs are stored at `~/.claude/projects/<project-path>/`. Look for JSONL files in that directory.
- **Other tools** (ChatGPT, Copilot Chat, etc.): most tools have an export or history feature. If you can't find it, try asking the AI itself: "where is my chat history?" — it usually knows.

**Be honest** — there is no penalty for using AI within the allowed boundaries. There **is** a penalty for misrepresenting your use of AI or for submitting AI-generated analysis as your own.

---

## What to Implement

- A configurable RFC (on/off, number of entries per warp) integrated into the operand collector (`opndcoll_rfu_t`).
- On **writeback**: insert the destination register into the warp's RFC (FIFO replacement if full). The MRF write still occurs (write-through).
- On **operand read**: check the RFC before issuing a bank-arbitration request. On a hit, the operand is immediately available (no bank access). On a miss, the normal MRF read path is taken.
- On **warp demotion** (two-level scheduler): flush the demoted warp's RFC entries.
- Add the statistics counters described in the questions below.

### Configuration Flags

Add at minimum:
- `-gpgpu_rfc_enabled` (bool, default 0)
- `-gpgpu_rfc_entries_per_warp` (unsigned, default 6)

The two-level scheduler is already configurable via `-gpgpu_scheduler <type>` (e.g., `two_level_active:8:0:1`).

### Configurations to Run

You will evaluate the following configurations across **all Rodinia benchmarks**. All questions reference subsets of these runs:

| Label | Scheduler | RFC | Notes |
|-------|-----------|-----|-------|
| **Baseline** | GTO (single-level) | Disabled | Q1 baseline |
| **RFC-2** | GTO | 2 entries/warp | Q2 sweep |
| **RFC-6** | GTO | 6 entries/warp | Q2, Q3, Q7 |
| **RFC-12** | GTO | 12 entries/warp | Q2 sweep |
| **TwoLevel** | `two_level_active:8:0:1` | Disabled | Q4 |
| **TwoLevel+RFC** | `two_level_active:8:0:1` | 6 entries/warp | Q5 |
| **RFC-6, MRF-lat=2** | GTO | 6 entries/warp | Q7, `-gpgpu_mrf_extra_latency 2` |
| **RFC-6, MRF-lat=4** | GTO | 6 entries/warp | Q7, `-gpgpu_mrf_extra_latency 4` |
| **No-RFC, MRF-lat=2** | GTO | Disabled | Q7, `-gpgpu_mrf_extra_latency 2` |
| **No-RFC, MRF-lat=4** | GTO | Disabled | Q7, `-gpgpu_mrf_extra_latency 4` |

---

## Part 1: Analysis Questions

### Question 1: Instrumentation and Baseline

Before enabling the RFC, you need a baseline. Add the following **per-kernel** statistics counters to GPGPU-Sim. Report their values for all Rodinia benchmarks using the **Baseline** configuration:

| Counter | Description |
|---------|-------------|
| `mrf_reads` | Total MRF read accesses (operands served from the register file) |
| `mrf_writes` | Total MRF write accesses (writebacks to the register file) |
| `mrf_bank_conflicts` | Number of times an operand read request was denied by the bank arbiter because the target bank was already allocated that cycle |

**(a)** Present a table of these three counters (totals across all SMs) for each Rodinia benchmark. Identify the three benchmarks with the highest and three with the lowest `mrf_bank_conflicts / mrf_reads` ratio.

**(b)** For the benchmark with the **highest** bank conflict rate: examine its SASS instructions (look at the trace files or use `cuobjdump`). How many source register operands does a typical instruction use? How does this relate to the bank conflict rate? (Hint: more source operands per instruction means more simultaneous bank requests per collector unit.)

**(c)** For the benchmark with the **lowest** bank conflict rate: why are bank conflicts rare? Is it because the benchmark has few register accesses overall, or because accesses are spread evenly across banks? Use the `mrf_reads` and `mrf_bank_conflicts` counters to support your argument.

---

### Question 2: RFC Effectiveness

Enable the RFC with the default single-level GTO scheduler. Add these counters:

| Counter | Description |
|---------|-------------|
| `rfc_read_hits` | Number of operand reads served from the RFC (no MRF access needed) |
| `rfc_read_misses` | Number of operand reads that missed in the RFC and went to the MRF |
| `rfc_evictions` | Number of FIFO evictions from the RFC |

Report results for the **RFC-2**, **RFC-6**, and **RFC-12** configurations.

**(a)** For each benchmark, report the RFC hit rate (`rfc_read_hits / (rfc_read_hits + rfc_read_misses)`) at all three RFC sizes. Present this as a single bar chart (benchmarks on x-axis, grouped bars for 2/6/12 entries).

**(b)** The paper reports that 6 entries captures most of the benefit (knee of the curve). Identify benchmarks where going from 6→12 entries still provides a significant (>5%) hit rate improvement. For these benchmarks, explain why 6 entries is insufficient — what is it about the register usage pattern (e.g., number of live registers, instruction distance between definition and last use) that causes more RFC capacity to help?

**(c)** Report the **percentage reduction in MRF reads** at 6 entries for all benchmarks (compare `mrf_reads` in **RFC-6** vs. **Baseline**). The paper reports 45–75% reduction on their workloads. Sort your benchmarks by this metric. For the top-3 and bottom-3 benchmarks, explain what characteristics drive high vs. low RFC effectiveness.

---

### Question 3: Bank Conflicts and Operand Lifecycle

**(a)** Using the **RFC-6** configuration, report the `mrf_bank_conflicts` counter for all benchmarks and compare to the **Baseline** from Question 1. Present a bar chart showing bank conflicts with and without RFC, side by side. Compute the average percentage reduction across all benchmarks. Explain the mechanism: why does the RFC reduce bank conflicts even though it does not change the bank mapping function or the number of banks?

**(b)** Consider a scenario where two instructions in the same warp execute back-to-back: the first writes register R5, and the second reads R5 as a source operand. Trace the lifecycle of R5 through your implementation:
1. Where is R5 when the first instruction completes writeback?
2. When the second instruction enters the operand collector, where does R5 come from?
3. What happens at the MRF bank for R5 during step 2 — is a bank slot consumed?

If you removed the RFC, what would happen differently in step 2? Under what conditions would this cause an observable performance difference (i.e., added stall cycles)?

**(c)** A student proposes: *"Instead of a FIFO, use LRU replacement for the RFC."* Would this help or hurt for GPU workloads compared to FIFO? Justify your answer by considering the SIMT execution model — all threads in a warp execute the same instruction sequence in program order. You do **not** need to implement LRU — a reasoned argument is sufficient.

---

### Question 4: Two-Level Scheduler

Use the **TwoLevel** configuration (RFC disabled, 8 active warps).

Add the following counter:

| Counter | Description |
|---------|-------------|
| `warp_demotions` | Number of times a warp is moved from the active set to the pending set |

**(a)** Report IPC for all Rodinia benchmarks under both the **Baseline** and **TwoLevel** configurations. Present a bar chart comparing the two. Compute the geometric mean IPC change across all benchmarks.

**(b)** Identify the benchmark(s) that lose the most IPC when switching to 8 active warps. For each, report the `warp_demotions` count and the total number of warps launched. Explain why these benchmarks are more sensitive to the active warp count. (Hint: consider the ratio of long-latency memory operations to short-latency compute operations, and how many warps are needed to hide the memory latency.)

**(c)** The paper states that greedy scheduling outperforms round-robin for the inner level. Explain why in the context of GPU workloads. Specifically, consider a warp that encounters a cache miss: under greedy, what happens to the scheduler's behavior? Under round-robin, what happens? Why does the greedy approach better utilize the cache?

---

### Question 5: Combined Architecture and Flush Overhead

Use the **TwoLevel+RFC** configuration (RFC 6 entries, 8 active warps).

Add the following counter:

| Counter | Description |
|---------|-------------|
| `rfc_flush_entries` | Total number of valid RFC entries discarded across all flush events (when a warp is demoted) |

**(a)** Report the RFC hit rate for all benchmarks under **TwoLevel+RFC**. Compare to the **RFC-6** results from Question 2. The paper reports that combining RFC with two-level scheduling reduces RFC effectiveness by ~10% due to flushing on demotion. Report the average hit-rate reduction you observe.

**(b)** For each benchmark, report: (i) total `rfc_flush_entries`, (ii) total `rfc_evictions` (from normal FIFO replacement), and (iii) the ratio `rfc_flush_entries / (rfc_flush_entries + rfc_evictions)`. This ratio tells you what fraction of RFC capacity loss is due to scheduler-driven flushes vs. natural replacement. Identify which benchmarks are most affected by flush overhead and explain why (connect to the `warp_demotions` count from Question 4).

**(c)** Present a 2×2 table of **MRF read accesses** for each benchmark using data from Questions 1, 2, 4, and 5:

| | Single-level (GTO) | Two-level (8 active) |
|---|---|---|
| **No RFC** | Baseline | TwoLevel |
| **RFC (6 entries)** | RFC-6 | TwoLevel+RFC |

Despite the reduced RFC hit rate, does the combined architecture still reduce total MRF reads compared to the no-RFC baseline? Explain any cases where the two-level scheduler *increases* MRF reads relative to the single-level scheduler (with or without RFC).

---

### Question 6: Edge Cases and Correctness

These questions test your understanding of the implementation. Answer based on your code — reference specific functions or line numbers where appropriate.

**(a)** What happens if you enable the RFC but forget to flush it when a warp is demoted in the two-level scheduler? Describe a concrete scenario where this bug would cause **incorrect simulation results** (not just different performance — actually wrong register values being read). (Hint: think about what happens when a new CTA is launched and a new warp is assigned to the same hardware warp slot that previously belonged to a different warp with stale RFC entries.)

**(b)** GPGPU-Sim deduplicates source operands within a single instruction (e.g., `MUL R1, R2, R2` only reads R2 once from the register file). Examine the `collector_unit_t::allocate()` function. Does your RFC correctly handle this case? Specifically, if R2 is in the RFC, does your implementation count one RFC hit or two? Show the relevant code path and explain why it is correct.

**(c)** Consider the instruction sequence: `LD R5, [addr]` followed by `ADD R1, R5, R3`. The load writes R5, but the value is not available until the memory access completes (many cycles later). Should R5 be inserted into the RFC when the load instruction is *issued*, or when it *writes back*? Which does your implementation do, and why is this the correct choice? What would go wrong if you chose the other option?

---

### Question 7: Register File Access Latency

By default, GPGPU-Sim models the MRF as having zero additional latency — operands are available the same cycle the bank arbiter grants access. In reality, the MRF is large (128KB+ per SM) and physically distant from the ALUs, while a small RFC would sit close to the execution units with much lower access latency.

Modify the operand collector so that MRF reads incur an additional configurable latency of `N` cycles after the bank arbiter grants access (i.e., the operand is not marked as "collected" until `N` cycles after the grant). Add a config flag `-gpgpu_mrf_extra_latency` (default: 0). **RFC hits should bypass this extra latency** — they are available immediately.

Use the MRF latency configurations from the table above (latency = 0, 2, 4; with and without RFC).

**(a)** For each benchmark, report IPC at all three MRF latencies with RFC enabled vs. disabled (6 data points per benchmark). Present a table or grouped bar chart. At what latency does the RFC start to provide a measurable **IPC benefit** (not just energy savings) for most benchmarks?

**(b)** The original paper focuses on **energy** reduction rather than **performance** improvement as the primary motivation for the RFC. Based on your results, explain why: at realistic MRF latencies (0–2 extra cycles), does the RFC meaningfully improve IPC? What needs to be true about the MRF latency and the benchmark's instruction mix for the RFC to provide a performance benefit?

**(c)** Identify any benchmark(s) where IPC actually **decreases** when adding MRF latency even with RFC enabled. Why would RFC hits (which bypass the latency) not fully compensate for the slower MRF misses? What does this tell you about the RFC hit rate needed to make this design performance-neutral?

---

### Question 8: Design Space Summary

**(a)** Compile a final summary table for **all benchmarks** across the four main configurations, using data collected in previous questions:

| Benchmark | Config | IPC | MRF Reads | RFC Hit Rate | Bank Conflicts |
|-----------|--------|-----|-----------|--------------|----------------|
| ... | Baseline | | | N/A | |
| ... | RFC-6 | | | | |
| ... | TwoLevel | | | N/A | |
| ... | TwoLevel+RFC | | | | |

**(b)** Based on your experiments, if you were designing a real GPU and could only pick **one** of the two techniques (RFC or two-level scheduling), which would you recommend and why? Consider both performance and energy. Your answer may differ across benchmark categories — that is fine, but explain the trade-off.

**(c)** The paper proposes a combined design with 6 RFC entries per thread and 8 active warps, requiring 192 bytes of RFC storage per SIMT lane. A modern GPU SM has 64 warps with 32 threads each. Estimate the total RFC storage required per SM for 64 warps with 6 entries per warp (assume each entry stores a 4-byte register tag plus 128-bit / 16-byte data = 20 bytes per entry). Is this a reasonable overhead compared to the 256KB main register file? Would you increase or decrease the RFC size for a modern GPU with deeper pipelines and larger register files, and why?

---
