# Merge multiple self-hosted instances together

Inside this directory are 2 scripts:

1. Script that takes two export JSON files, each from a different self-hosted instance, and merges them into a single export JSON file. This script is expected to be run by Sentry SEs, and not by our customers. That JSON file should then be given to the Sentry ops team to complete the migration.
2. The "comparer" script validates the merged JSON file.

Note:
- These scripts have been used in real migrations, but are not exhaustively tested. You are encouraged to do some spot checking on the output merged JSON file to make sure things look good and records are associated correctly.
- The migration process run by the ops team (in any scenario, not just merging multiple self-hosted instances) does not carry over all data included in the original JSON export file. So, the merge script only combines certain types of data: Alerts, Projects, Project Options, Teams, Organization. If you are reading the script and wondering why it doesn't carry over everything, that's why.
