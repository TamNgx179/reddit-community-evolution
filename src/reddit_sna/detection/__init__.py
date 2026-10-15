"""User-community detectors: Leiden/Louvain, temporal/consensus.

Add algorithms as named modules, e.g. leiden.py; keep both proposed and baseline
detectors behind the same membership contract. Independent Leiden is implemented in leiden.py; temporal/consensus detectors remain planned.

Report objective/resolution, graph identity, coverage, community sizes and
stability across seeds. Modularity alone is not evidence of a correct social
partition. Temporal detectors must freeze C_t without access to later snapshots.
"""
