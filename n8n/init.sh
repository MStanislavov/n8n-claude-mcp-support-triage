#!/bin/sh
# One-shot setup that runs in the n8n-init service before n8n starts:
# imports the Anthropic credential (from ANTHROPIC_API_KEY) and the workflow, then publishes the workflow.
# Generated files live in a temp dir inside the container and are deleted on exit.
set -eu

WORKFLOW_ID="SupportTriage001"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

OUT_DIR="$TMP_DIR" node <<'JS'
const fs = require('fs');
const out = process.env.OUT_DIR;
const model = process.env.ANTHROPIC_MODEL || 'claude-sonnet-5-5';

const workflow = JSON.parse(fs.readFileSync('/seed/workflows/support-triage.json', 'utf8'));
const modelNode = workflow.nodes.find((n) => n.type === '@n8n/n8n-nodes-langchain.lmChatAnthropic');
modelNode.parameters.model = { __rl: true, mode: 'id', value: model };
fs.writeFileSync(`${out}/workflow.json`, JSON.stringify(workflow));

if (process.env.ANTHROPIC_API_KEY) {
  const credentials = [{
    id: 'AnthropicCred001',
    name: 'Anthropic account',
    type: 'anthropicApi',
    data: { apiKey: process.env.ANTHROPIC_API_KEY, url: 'https://api.anthropic.com' },
  }];
  fs.writeFileSync(`${out}/credentials.json`, JSON.stringify(credentials), { mode: 0o600 });
}
console.log(`Prepared workflow with model ${model}`);
JS

if [ -f "$TMP_DIR/credentials.json" ]; then
  n8n import:credentials --input="$TMP_DIR/credentials.json"
else
  echo "WARNING: ANTHROPIC_API_KEY is empty. Skipping the Anthropic credential."
  echo "Set it in .env and run 'docker compose up -d' again before calling the webhook."
fi

# On a re-run the workflow already exists and is published. Importing over a published
# workflow fails, so unpublish it first. Skipped on the very first run.
if n8n list:workflow 2>/dev/null | grep -q "^$WORKFLOW_ID|"; then
  n8n unpublish:workflow --id="$WORKFLOW_ID"
fi

n8n import:workflow --input="$TMP_DIR/workflow.json"
n8n publish:workflow --id="$WORKFLOW_ID"
