# Academic Framework Figure Prompt Examples (SOP Format)

These examples demonstrate the SOP structure and tone for generating academic framework figure prompts.

## Example 1: Expert Choice vs Global Expert Choice (2-Panel)

```markdown
> **Goal:** Create a technical schematic diagram for an ICML paper (Figure 1) comparing two routing algorithms.
>
> **Layout:** Split into two panels: Left (Expert Choice) and Right (Global Expert Choice). Flow Left -> Right.
>
> **Panel 1: Expert Choice (Non-Causal)**
> *   **Visual:** Depict a batch of $N$ tokens entering the router.
> *   **The Math:** Show the selection set for expert $i$ as $\mathcal{T}_i = \text{TopK}(\{r_{1,i}, \ldots, r_{N,i}\}, k)$.
> *   **The Mechanism/Flaw:** Draw arrows from all token logits $r_{t,i}$ (including future ones) feeding into the decision.
> *   **Label:** "Future Information Leakage".
>
> **Panel 2: Global Expert Choice (Causal)**
> *   **Visual:** Depict a stream of tokens arriving sequentially.
> *   **The Math:** Show the routing decision as a binary threshold: $z_{t,i} = \mathbf{1}\{r_{t,i} > c_i\}$.
> *   **The Mechanism/Fix:** Show $c_i$ (cutoff) updated by an EMA loop from past history: $c_i \leftarrow \beta c_i + (1-\beta) \cdot \text{TopK}_{batch}$.
> *   **Label:** "Fully Causal".
>
> **Caption:**
> Figure 1. Comparison of Expert Choice (EC) and Global Expert Choice (GEC) routing. Left: EC selects the top-$k$ tokens for each expert within a batch, requiring access to all tokens including future ones. Right: GEC maintains an EMA of the top-$k$ cutoff threshold from historical batches and routes tokens via binary thresholding, enabling fully causal routing.
```

## Example 2: Baseline vs Proposed Method (2-Panel)

```markdown
> **Goal:** Create a technical schematic diagram for a NeurIPS paper comparing a baseline attention mechanism and a proposed sparse attention method.
>
> **Layout:** Split into two panels: Left (Baseline Dense Attention) and Right (Proposed Sparse Attention). Flow Left -> Right.
>
> **Panel 1: Baseline Dense Attention**
> *   **Visual:** Show a full $N \times N$ attention matrix with all entries highlighted.
> *   **The Math:** $A = \text{softmax}(QK^\top / \sqrt{d})$.
> *   **The Mechanism/Flaw:** Dense connections from all tokens to all tokens.
> *   **Label:** "Quadratic Cost".
>
> **Panel 2: Proposed Sparse Attention**
> *   **Visual:** Show a sparse $N \times N$ matrix with only top-$k$ entries highlighted per row.
> *   **The Math:** $A_{t,\cdot} = \text{TopK}(QK^\top)_t$.
> *   **The Mechanism/Fix:** Only top-$k$ connections per token; others dimmed.
> *   **Label:** "Sub-Quadratic Cost".
>
> **Caption:**
> Figure X. Dense attention computes a full pairwise matrix with quadratic cost, while the proposed sparse attention keeps only top-$k$ connections per token, reducing compute without changing the attention formulation.
```
