#!/bin/bash
# Batch close old GitHub issues with comments
# Requires: gh CLI installed and authenticated

# Issues to close (old milestone issues superseded by v2.0)
ISSUES="60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113"

COMMENT="Completed and superseded by v2.0 Production Hardening EPIC #117. All functionality delivered in the v2.0 release. Closing as completed."

echo "Closing old issues with v2.0 supersession notice..."

for issue in $ISSUES; do
  echo "Closing issue #$issue..."
  gh issue close "$issue" --comment "$COMMENT" || echo "Failed to close #$issue"
  sleep 1
done

echo "Done!"
