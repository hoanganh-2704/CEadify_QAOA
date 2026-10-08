# Submission and grading

This page lists what each team submits and how judges score it. The rubric rewards understanding and honest checking as much as results, so a beginner team can score well.

<!-- TODO(organizers): confirm the submission deadline time, the submission channel, the team size cap and the judging slot. -->

## Deadline and format

- **Deadline:** Saturday, October 17, 2026, at the time the organizers announce at kickoff. Late submissions are not judged.
- **Where:** the submission link the organizers share at kickoff.
- **Teams:** solo or a team. Organizers match anyone who arrives without a team.
- **Presentation:** 5 minutes per team, followed by 2 minutes of questions from the judges.

## Deliverables

Submit all five. Missing items cost points in the matching rubric rows.

| # | Deliverable | What it must contain |
|---|---|---|
| 1 | **Slides** (PowerPoint, Google Slides or PDF, at most 8 slides) | The problem, your encoding, your algorithm, your results, and one thing you would try next. |
| 2 | **Working code** (a notebook, plus any `.py` files it imports) | Runs from top to bottom in qBraid Lab with no edits. Saved **with outputs**, so judges can read the results without running it. Fixed random seeds where you use randomness. |
| 3 | **Write-up** (a `SUBMISSION.md`, one page) | Team members, which level you reached (warm-up, core, bonus), how to run your code, and the results table below. |
| 4 | **qBraid job IDs** | The IDs of the SV1 jobs behind your reported results, listed in `SUBMISSION.md`. |
| 5 | **AI use note** (a section of `SUBMISSION.md`) | Which AI tools you used, for which parts, and how you checked their output. Using AI is allowed and encouraged. Not disclosing it is not. |

### Results table

Put this table in `SUBMISSION.md`, one row per experiment you report.

| Puzzle (N cubes) | Encoding | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|

- **P(correct tower)** is the fraction of shots that decode to a solved tower. Check every decoded tower with a classical checker, such as `solves` in the starter notebook.
- **Random-guess baseline** is the probability that a uniformly random bitstring of your encoding is a solved tower. It tells the judges how much your algorithm adds.
- Count two-qubit gates after `transpile(qc, basis_gates=["rz", "sx", "x", "cx"])`, so every team counts the same way.

## Rubric

Judges score each row from 1 to 4 and multiply by the weight. The maximum is 100 points, plus up to 10 bonus points.

| Row | Weight | 1 · Beginning | 2 · Developing | 3 · Proficient | 4 · Exemplary |
|---|---|---|---|---|---|
| **Problem understanding and encoding** | 5 | Restates the puzzle but the encoding is missing or wrong. | Encoding works for part of the puzzle, such as the warm-up half. | A correct encoding of the full puzzle, with a clear qubit count. | A correct encoding that is smaller or more natural than the starter's, with the reasoning shown. |
| **Quantum approach** | 6 | A circuit runs but does not target the puzzle. | Runs the warm-up, or a full-puzzle attempt that rarely finds a tower. | Finds a full solved tower on SV1, measurably above the random baseline. | Finds a tower reliably, and explains why the design choices (initial state, mixer, ansatz, optimizer) help. |
| **Classical benchmarking and verification** | 4 | No classical check. | Checks the final answer by hand or by eye. | Confirms classically that the known answer is the lowest cost and that nothing wrong ties with it. Reports the random baseline. | Also compares cost and time against brute force or a classical heuristic, honestly, including where classical wins. |
| **Results and analysis** | 3 | Reports a number with no context. | Reports success rates without resource counts. | Fills the results table: qubits, gates, depth, shots, success rate and baseline. | Shows how results change with a design choice (depth p, shots, encoding) and explains the trend. |
| **Code understanding** | 3 | Cannot explain the code in the Q&A. | Explains parts, relies on the starter for the rest. | Every team member can explain what each block does. | Explains limits and failure cases, and answers "what if" questions with confidence. |
| **Clarity of presentation** | 3 | Slides are hard to follow or run long. | The story is there but key steps are missing. | Clear problem, method and results in 5 minutes. | A clear story that a beginner in the room could follow, with honest takeaways. |
| **Code quality and reproducibility** | 1 | Code does not run. | Runs with edits or missing outputs. | Runs top to bottom in qBraid Lab with saved outputs and seeds. | Also clean and commented where it helps, with reusable functions. |

Row weights sum to 25, so a row's points are weight times level, and four times 25 gives the 100-point maximum.

### Bonus: N cubes and N colours (up to 10 points)

| Points | What it takes |
|---|---|
| 3 | Your method runs on at least one puzzle with N = 5 and finds a correct tower on SV1 or a local simulator. |
| 6 | It works for at least two values of N, and you report how qubits, depth and success rate grow with N. |
| 10 | It also scales better than the one-hot starter encoding (6N qubits) in qubits or depth, with evidence. |

Use `make_puzzle` and `count_answers` from the starter notebook to make puzzles, and say which seeds you used.

## What judges look for

- **Honesty over hype.** A clear account of what did not work earns more than an unsupported claim. Do not claim a quantum speedup you did not measure.
- **Checks before claims.** Every tower you report should pass a classical check.
- **Understanding.** Judges ask each team member at least one question.
- **Thoughtful AI use.** Teams that used AI agents should show how they kept them correct, for example by testing the agent's encoding against brute force.

## Tie-breaks

Ties are broken by the Classical benchmarking row, then the Quantum approach row, then the judges' vote.
