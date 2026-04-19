# House AI sync + validation workflow

This project uses two repositories:

- Live runtime repo: `~/house-agent`
- Public clean repo: `~/house-ai-architecture`

## Core rule

Always work in `~/house-agent` first.

Never develop directly in the public repo.

## Mandatory flow

1. Edit only in `~/house-agent`
2. Validate in `~/house-agent`
3. Review the exact diff
4. Copy only approved public-safe files into `~/house-ai-architecture`
5. Review public diff
6. Commit and push only from `~/house-ai-architecture`

## Validation steps

Run:

```bash
cd ~/house-agent
bash tools/validate_live.sh
