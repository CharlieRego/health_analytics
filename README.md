# health_analytics

## Dashboard

`powerbi/qld-hospital-performance.pbix` is a **snapshot**. Power BI imports the data into the file, so it opens without a database connection. The date of the snapshot is shown on the Data Assurance page ("Last successful run").

Pages:

- **QLD vs National:** KPI cards and the long-run trend for the selected measure, with small multiples by triage category.
- **QLD Hospital comparison:** each Queensland hospital against its AIHW peer-group average for a chosen year (right-click a bar to drill through).
- **Hospital profile:** drill-through page, opens on Toowoomba Hospital: trend vs peers and every measure for the latest year.
- **Data Assurance:** latest dbt test results, row reconciliation (API = database) and pipeline run history.

The theme is in `powerbi/qld-hospital-theme.json`.

How the data stays current:

1. A scheduled job on the server runs the pipeline every Monday at 03:00 (AEST). It calls the AIHW MyHospitals API, loads the results into Postgres, rebuilds the dbt models and runs the data tests.
2. The dashboard reads from the `marts` schema using a read-only login (`powerbi_reader`) over an SSH tunnel.
3. To update the snapshot, open the tunnel and click **Refresh** in Power BI Desktop. Only the project owner can do this; anyone else who downloads the file sees the data as at the last refresh.

The `.pbix` is recommitted only when the dashboard itself changes, not after every weekly load.

## What I'd do next

- **Scheduled dashboard refresh:** in production, publish the report to the Power BI service with an on-premises data gateway and schedule a refresh after each weekly load, instead of refreshing the snapshot by hand.
- **Live web dashboard (stretch):** build a public, always-current dashboard on the server (for example a static site generated from the `marts` tables after each Monday run), so anyone can view the latest data without Power BI.
