# Notebook 01 — Corpus overview

SQL:
```sql
SELECT source, COUNT(*) FROM candidates WHERE status='downloaded' GROUP BY source ORDER BY COUNT(*) DESC;
SELECT license, COUNT(*) FROM candidates WHERE status='downloaded' GROUP BY license ORDER BY COUNT(*) DESC;
```
