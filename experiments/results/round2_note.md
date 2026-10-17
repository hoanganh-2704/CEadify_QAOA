# Round 2 note: reduced Hamiltonian

1. The circuit starts each cube in a W state, and every XX+YY gate only swaps a 1 between two qubits of the same cube. So the state never leaves the 1,296 bitstrings that have exactly one 1 in each 6-qubit block.
2. On those bitstrings, a ZZ between two qubits of the same cube is not fixed (it is -1 when one of the two holds the cube's 1 and +1 otherwise). What is fixed is the product of their 0/1 values, which is always 0 because a block never has two 1s, so the term is the same as Z_i + Z_j - 1 there: two single-qubit terms and a constant. For each pair of cubes, adding a shift that depends on only one cube's choice is the same as adding a single-qubit term. My `reduced_hamiltonian` therefore drops the same-cube ZZ terms and moves one row and one column of every cube-pair table into Z terms, which leaves 94 ZZ terms with choice 0 as the reference and 77 when each pair picks its own reference.
3. The saved angles still work: the cost layer is diagonal, and on every reachable bitstring the new energy equals the old one (max difference 0 over all 1,296 picks). So each layer applies the same phases there, and nothing about the optimization landscape changed.
4. I loaded the angles from results/round1.json (a fresh training lands 1.96e-3 away, so I did not use it) and got these numbers:
   - Overlap with the old state: |<old|new>| = 1 to about 6e-15, both in the 6^4 subspace simulation and in real 12-qubit Qiskit circuits at N=2.
   - P(solved) at those angles: 26.246% for both the old and the reduced Hamiltonian.
   - CX with `transpile(qc, basis_gates=["rz","sx","x","cx"])`: 4590 for the old circuit, 2196 with reference 0, and 1958 with the per-pair reference.
   - Depth with the same call: 1684, 974 and 911. Depth moves by 1 or 2 between runs, because this call sets no seed.
