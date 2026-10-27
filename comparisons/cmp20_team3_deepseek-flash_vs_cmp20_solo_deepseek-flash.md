# cmp20_team3_deepseek-flash vs cmp20_solo_deepseek-flash

20 BrowseComp-Plus queries, judge: deepseek-flash. Not run / not judged counts as wrong. Search calls are summed over a team's agents.

| setting | agents | correct | completed | avg time (s) | avg search calls | avg tokens (in+out) | avg board posts |
|---|---|---|---|---|---|---|---|
| cmp20_team3_deepseek-flash | 3 | 16/20 (80.0%) | 20/20 | 310 | 150.0 | 8152k | 7.0 |
| cmp20_solo_deepseek-flash | 1 | 13/20 (65.0%) | 19/20 | 364 | 101.0 | 5894k | 0.0 |

Correctness patterns (order: cmp20_team3_deepseek-flash, cmp20_solo_deepseek-flash): ✓✓ 12 · ✓✗ 4 · ✗✓ 1 · ✗✗ 3

| query | cmp20_team3_deepseek-flash | cmp20_solo_deepseek-flash |
|---|---|---|
| 769 | ✗ (293) | ✗ (218) |
| 770 | ✓ (158) | ✗ (107) |
| 771 | ✓ (23) | ✓ (39) |
| 772 | ✓ (382) | ✓ (185) |
| 773 | ✗ (330) | ✗ (159) |
| 774 | ✓ (124) | ✓ (161) |
| 775 | ✗ (238) | ✗ (137) |
| 776 | ✓ (56) | ✓ (32) |
| 778 | ✓ (291) | ✗ incomplete (206) |
| 781 | ✓ (59) | ✓ (27) |
| 783 | ✓ (23) | ✓ (15) |
| 784 | ✓ (31) | ✗ (117) |
| 785 | ✓ (54) | ✓ (20) |
| 786 | ✓ (148) | ✓ (91) |
| 787 | ✓ (148) | ✓ (56) |
| 788 | ✓ (107) | ✓ (42) |
| 790 | ✓ (68) | ✓ (47) |
| 791 | ✓ (55) | ✗ (152) |
| 792 | ✓ (103) | ✓ (158) |
| 793 | ✗ (309) | ✓ (50) |
