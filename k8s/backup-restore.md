# Backup and restore

The CronJob writes compressed snapshots to the `fakebric-backups` PVC. A
restore is intentionally a separate, reviewed operation; never unpack over a
live `/data` volume.

1. Stop API and session controller:

   ```powershell
   kubectl -n fakebric-system scale deployment/fakebric-api --replicas=0
   kubectl -n fakebric-system scale deployment/fakebric-session-controller --replicas=0
   ```

2. Mount `fakebric-data` and `fakebric-backups` in a temporary restore pod,
   verify the selected archive checksum, and extract it into the data mount:

   ```sh
   sha256sum /backup/fakebric-<UTC>.tar.gz
   tar -xzf /backup/fakebric-<UTC>.tar.gz -C /data
   ```

3. Scale the deployments back up and verify `/readyz`, item counts and a
   representative notebook/lakehouse file before reopening traffic.

In production, copy snapshots to versioned object storage and require an
independent checksum plus approval before promotion.
