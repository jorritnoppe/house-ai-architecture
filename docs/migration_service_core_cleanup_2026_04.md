# House Agent service-core migration cleanup

## Summary
Legacy root-level modules were migrated into service-core modules under `house-agent/services/`.

The application now imports the service-core modules directly, while legacy root filenames remain as compatibility wrappers.

## New core files
- `house-agent/services/apc_legacy_core.py`
- `house-agent/services/buderus_legacy_core.py`
- `house-agent/services/pdata_tools_core.py`
- `house-agent/services/sma_tools_core.py`
- `house-agent/services/crypto_tools_core.py`

## Updated runtime import points
- `house-agent/app.py`
- `house-agent/extensions.py`
- `house-agent/services/agent_query_service.py`
- `house-agent/services/apc_service.py`
- `house-agent/services/buderus_service.py`

## Wrapper files
These currently remain as compatibility shims:
- `house-agent/apc_ai.py`
- `house-agent/buderus_module.py`
- `house-agent/Pdata.py`
- `house-agent/sma_ai.py`
- `house-agent/tools_crypto.py`

## Validation completed
- compile checks passed
- live runtime health passed
- pdata endpoints passed
- SMA endpoints passed
- repo import audit passed
- GitHub migration commit pushed successfully

## Current policy
The wrapper files are compatibility-only.
They may be removed later after a final external-script/manual-usage audit and a safe observation window.

## Architectural outcome
The project now follows a cleaner structure where:
- service logic lives under `house-agent/services/`
- root legacy names no longer contain the real implementation
- runtime imports are explicit and easier to maintain
