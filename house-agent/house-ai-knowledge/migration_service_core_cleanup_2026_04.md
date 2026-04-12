# House Agent service-core migration cleanup

## Summary
Legacy root-level modules were migrated into service-core modules under `services/`.

The application now imports the service-core modules directly. The temporary root-level compatibility wrappers used during migration have been fully retired and removed.

## New core files
- `services/apc_legacy_core.py`
- `services/buderus_legacy_core.py`
- `services/pdata_tools_core.py`
- `services/sma_tools_core.py`
- `services/crypto_tools_core.py`

## Updated runtime import points
- `app.py`
- `extensions.py`
- `services/agent_query_service.py`
- `services/apc_service.py`
- `services/buderus_service.py`

## Wrapper retirement
The following temporary migration wrappers were removed after validation:
- `apc_ai.py`
- `buderus_module.py`
- `Pdata.py`
- `sma_ai.py`
- `tools_crypto.py`

## Validation completed
- compile checks passed
- live runtime health passed
- pdata endpoints passed
- SMA endpoints passed
- repo import audit passed
- GitHub migration commits pushed successfully
- final wrapper filename audit passed
- final import audit passed, with only false positives from `pdata_tools_core`

## Current policy
The service-core files are now the only supported implementation path.

## Architectural outcome
The project now follows a cleaner structure where:
- service logic lives under `services/`
- legacy root modules are gone
- runtime imports are explicit and easier to maintain
- live runtime, sanitized repo, and public app tree are aligned
