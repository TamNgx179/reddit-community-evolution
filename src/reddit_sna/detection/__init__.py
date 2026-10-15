"""User-community detectors: Leiden/Louvain (Phúc), temporal/consensus (Tâm).

Add algorithms as named modules, e.g. leiden.py; keep both proposed and baseline
detectors behind the same membership contract. No detectors implemented yet.

Report objective/resolution, graph identity, coverage, community sizes and
stability across seeds. Modularity alone is not evidence of a correct social
partition. Temporal detectors must freeze C_t without access to later snapshots.
"""
