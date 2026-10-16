# Submission and grading

This page lists what each team submits and how judges score it. The rubric rewards understanding and honest checking as much as results, so a beginner team can score well.

<!-- TODO(organizers): confirm the form or channel where teams post their repository link. -->

## Deadline and format

- **Deadline:** Saturday, October 17, 2026, at **3:00 PM ET**, when demos begin. Late submissions are not judged.
- **What:** the link to one **public GitHub repository** per team, laid out as below. Post it where the organizers say at kickoff.
- **Teams:** 2 to 4 people. Organizers match anyone who arrives without a team.
- Do not push to the repository after the deadline. Judges read the last commit before it.
- **Presentation:** 5 minutes per team, followed by 2 minutes of questions from the judges.

## Repository layout

Keep it simple. Judges open your `README.md` first, then follow its links.

```
<your-team-repo>/
├── README.md              team, level reached, how to run, results table, job IDs, AI use note
├── slides.pdf             or slides.pptx; at most 8 slides
├── solution.ipynb         your main notebook, saved with outputs
├── requirements.txt       only if you need packages beyond this challenge's requirements.txt
├── src/                   optional: .py modules your notebook imports
└── resources/             only if you import the starter's helpers: copy helpers.py and __init__.py here
```

You may start from a copy of this challenge repository. If you do, replace this challenge's `README.md` with your own, and delete what you did not use, so judges see your work first.

## Deliverables

Submit all five, inside the repository. Missing items cost points in the matching rubric criteria.

| # | Deliverable | What it must contain |
|---|---|---|
| 1 | **Slides** (`slides.pdf` or `slides.pptx`, at most 8 slides; export Google Slides to PDF) | The problem, your encoding, your algorithm, your results, and one thing you would try next. |
| 2 | **Working code** (a notebook, plus any `.py` files it imports) | Runs from top to bottom in qBraid Lab with no edits. Saved **with outputs**, so judges can read the results without running it. Fixed random seeds where you use randomness. |
| 3 | **Write-up** (your repository's `README.md`, about one page) | Team members, which level you reached (warm-up, core, bonus), how to run your code, and the results table below. |
| 4 | **qBraid job IDs** | The IDs of the jobs behind your reported results, listed in your `README.md`: your SV1 jobs, plus any real-hardware (QPU) jobs you ran with earned credits. |
| 5 | **AI use note** (a section of your `README.md`) | Which AI tools you used, for which parts, and how you checked their output. Using AI is allowed and encouraged. Not disclosing it is not. |

### Results table

Put this table in your `README.md`, one row per experiment you report.

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|

- **P(correct tower)** is the fraction of shots that decode to a solved tower. Check every decoded tower with a classical checker, such as `solves` in the starter notebook.
- **Random-guess baseline** is the probability that a uniformly random bitstring of your encoding is a solved tower. It tells the judges how much your algorithm adds.
- Count two-qubit gates after `transpile(qc, basis_gates=["rz", "sx", "x", "cx"])`, so every team counts the same way.
- **Device** is the qBraid device ID, such as `aws:aws:sim:sv1`. If you also ran on real hardware, add a row for it next to the matching SV1 row.

## Rubric

Five criteria, 100 points in total, plus up to 10 bonus points. A missing deliverable scores 0 in its criterion.

| Criterion | Points | The question judges ask |
|---|---|---|
| **Encoding and quantum approach** | 30 | Does your method fit the puzzle, and can you explain why you built it that way? |
| **Classical checks** | 20 | How do you know your model and your answers are right? |
| **Results** | 20 | What did you measure, and what does it tell you? |
| **Code and understanding** | 15 | Does the code run as submitted, and can every team member explain it? |
| **Presentation** | 15 | Could someone new to quantum computing follow your story? |

**Bonus (up to 10 points):** generalize to N cubes and N colours. Judges look at how far your method scales and the evidence you show for it. Use `make_puzzle` and `count_answers` from the starter notebook, and say which seeds you used.

Running on real hardware is optional. It counts when you compare it with your SV1 results.

## What judges look for

- **Honesty over hype.** A clear account of what did not work earns more than an unsupported claim. Do not claim a quantum speedup you did not measure.
- **Checks before claims.** Every tower you report should pass a classical check.
- **Understanding.** Judges ask each team member at least one question.
- **Thoughtful AI use.** Teams that used AI agents should show how they kept them correct, for example by testing the agent's encoding against brute force.

## Tie-breaks

Ties are broken by the Classical checks score, then the Encoding and quantum approach score, then the judges' vote.
