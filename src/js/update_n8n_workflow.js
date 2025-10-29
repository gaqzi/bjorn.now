#!/usr/bin/env node
/*
 This script's job is to:

 - Extract the mastodon and bsky functions from n8n.copies.js
 - Read the JSON file in the first argument and then replace the nodes for Mastodon and bsky respectively with their functions
 - Output the updated JSON object on stdout, pretty-printed

 Example: ./update_n8n_workflow.js ../bjorn-now-feed-distribution.json > workflow.json

 Will update the node id `e1bd320b-1222-4324-9168-22372d2e667c` so the parameter.status is `={{ (...)($('RSS Feed Trigger').item) }}
 */

import { fromFile } from './extract.js';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

// Get current directory for resolving relative paths
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Parse command line arguments
const workflowPath = process.argv[2];

if (!workflowPath) {
    console.error('Usage: update_n8n_workflow.js <workflow.json>');
    process.exit(1);
}

// Extract the mastodon function from n8n.copies.js
const mastodonCode = fromFile(resolve(__dirname, 'n8n.copies.js'), 'mastodon');

if (!mastodonCode) {
    console.error('Error: Could not extract mastodon function from n8n.copies.js');
    process.exit(1);
}

// Transform the extracted code by stripping the 'let mastodon = ' prefix
// to get just the arrow function: (item) => { ... }
const arrowFunction = mastodonCode.replace(/^\s*let\s+mastodon\s*=\s*/, '').trim();

// Wrap the arrow function in the n8n expression format
const n8nExpression = `={{ (${arrowFunction})($('RSS Feed Trigger').item) }}`;

// Read and parse the workflow JSON
const workflowContent = readFileSync(workflowPath, 'utf-8');
const workflow = JSON.parse(workflowContent);

// Find and update the Mastodon node
const mastodonNodeId = 'e1bd320b-1222-4324-9168-22372d2e667c';
let nodeFound = false;

if (workflow.nodes && Array.isArray(workflow.nodes)) {
    for (const node of workflow.nodes) {
        if (node.id === mastodonNodeId) {
            if (!node.parameters) {
                node.parameters = {};
            }
            node.parameters.status = n8nExpression;
            nodeFound = true;
            break;
        }
    }
}

if (!nodeFound) {
    console.error(`Warning: Node with id ${mastodonNodeId} not found in workflow`);
}

// Output the updated JSON to stdout
console.log(JSON.stringify(workflow, null, 2));
