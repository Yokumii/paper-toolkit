# paper-toolkit Evidence Graph Schema

`paper/evidence_graph.json` stores claim, evidence, and citation nodes. Edges use `supports`, `derives_from`, `cites`, and `contradicts`. A claim is supported when evidence supports it directly or all claims it derives from are supported.
