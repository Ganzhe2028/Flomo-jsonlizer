# Sample Data

Use this directory to test the pipeline without importing private flomo exports.

## Build a sample store

```bash
python scripts/build_store.py --raw-root examples/raw --store-root tmp/example-store
python scripts/validate_store.py --store-root tmp/example-store
```

The generated `tmp/example-store` directory is local output and should not be committed.
