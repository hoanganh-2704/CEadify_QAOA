# Submission and grading

This page lists what each team submits and how judges score it. The rubric rewards understanding and honest checking as much as results, so a beginner team can score well.

<!-- TODO(organizers): confirm the submission deadline time and the form or channel where teams post their repository link. -->

## Deadline and format

- **Deadline:** Saturday, October 17, 2026, at the time the organizers announce at kickoff. Late submissions are not judged.
- **What:** the link to one **public GitHub repository** per team, laid out as below. Post it where the organizers say at kickoff.
- **Teams:** 2 to 4 people. Organizers match anyone who arrives without a team.
- Do not push to the repository after the deadline. Judges read the last commit before it.
- **Presentation:** 5 minutes per team, followed by 2 minutes of questions from the judges.

## Repository layout

Keep it simple. Judges open `SUBMISSION.md` first, then follow its links.

```
<your-team-repo>/
├── SUBMISSION.md          team, level reached, how to run, results table, job IDs, AI use note
├── slides.pdf             or slides.pptx; at most 8 slides
├── solution.ipynb         your main notebook, saved with outputs
├── requirements.txt       only if you need packages beyond this challenge's requirements.txt
└── src/                   optional: .py modules your notebook imports
```

You may start from a copy of this challenge repository. If you do, delete what you did not use, so judges see your work first.

## Deliverables

Submit all five, inside the repository. Missing items cost points in the matching rubric criteria.

| # | Deliverable | What it must contain |
|---|---|---|
| 1 | **Slides** (`slides.pdf` or `slides.pptx`, at most 8 slides; export Google Slides to PDF) | The problem, your encoding, your algorithm, your results, and one thing you would try next. |
| 2 | **Working code** (a notebook, plus any `.py` files it imports) | Runs from top to bottom in qBraid Lab with no edits. Saved **with outputs**, so judges can read the results without running it. Fixed random seeds where you use randomness. |
| 3 | **Write-up** (a `SUBMISSION.md`, one page) | Team members, which level you reached (warm-up, core, bonus), how to run your code, and the results table below. |
| 4 | **qBraid job IDs** | The IDs of the jobs behind your reported results, listed in `SUBMISSION.md`: your SV1 jobs, plus any real-hardware (QPU) jobs you ran with earned credits. |
| 5 | **AI use note** (a section of `SUBMISSION.md`) | Which AI tools you used, for which parts, and how you checked their output. Using AI is allowed and encouraged. Not disclosing it is not. |

### Results table

Put this table in `SUBMISSION.md`, one row per experiment you report.

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|

- **P(correct tower)** is the fraction of shots that decode to a solved tower. Check every decoded tower with a classical checker, such as `solves` in the starter notebook.
- **Random-guess baseline** is the probability that a uniformly random bitstring of your encoding is a solved tower. It tells the judges how much your algorithm adds.
- Count two-qubit gates after `transpile(qc, basis_gates=["rz", "sx", "x", "cx"])`, so every team counts the same way.
- **Device** is the qBraid device ID, such as `aws:aws:sim:sv1`. If you also ran on real hardware, add a row for it next to the matching SV1 row.

## Rubric

Five criteria, 100 points in total, plus up to 10 bonus points. Judges can give any score from 0 up to a criterion's points. The three columns describe roughly a third, two thirds and full marks. A missing deliverable scores 0 in its criterion.

| Criterion | Points | Starting | Solid | Excellent |
|---|---|---|---|---|
| **Encoding and quantum approach** | 30 | Runs the warm-up, or encodes only part of the puzzle. | A correct encoding of the full puzzle that finds a solved tower on SV1, above the random baseline. | Finds towers reliably and explains why its design choices help, or uses a smaller encoding than the starter's. |
| **Classical checks** | 20 | Checks the final answer by eye. | Confirms that the known answer is the unique lowest cost, and reports the random baseline. | Also compares honestly with brute force or a classical method, including where classical wins. |
| **Results** | 20 | A success rate with no context. | A complete results table. | Shows how results change with one design choice (depth, shots, encoding, or SV1 against real hardware) and explains why. |
| **Code and understanding** | 15 | Code needs edits to run, or the team can explain only parts of it. | Runs top to bottom with saved outputs, and every member can explain each block. | Also explains limits and failure cases, and answers "what if" questions with confidence. |
| **Presentation** | 15 | Hard to follow, or runs long. | A clear problem, method and result in 5 minutes. | A beginner in the room could follow it, and the takeaways are honest. |

A real-hardware run is optional. It earns credit through the **Results** row when you compare it with SV1, not by itself.

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

Ties are broken by the Classical checks score, then the Encoding and quantum approach score, then the judges' vote.
