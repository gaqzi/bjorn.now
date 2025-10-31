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

function extractCode(name) {
    const code = fromFile(resolve(__dirname, 'n8n.copies.js'), name);

    if (!code) {
        console.error(`Error: Could not extract ${name} function from n8n.copies.js`);
        process.exit(1);
    }

    return code;
}

const mastodonCode = extractCode('mastodon'),
    bskyCode = extractCode('bsky'),
    bskyLinkCardCode = extractCode('bskyLinkCard'),
    telegramChannelCode = extractCode('telegramChannel');

// Transform the extracted code by stripping the 'let mastodon = ' prefix
// to get just the arrow function: (item) => { ... }
const removePrefix = /^\s*let\s+[^=]+\s*=\s*/;
const mastodonPost = mastodonCode.replace(removePrefix, '').trim(),
    bskyPost = bskyCode.replace(removePrefix, '').trim(),
    bskyLinkCard = bskyLinkCardCode.replace(removePrefix, '').trim(),
    telegramChannel = telegramChannelCode.replace(removePrefix, '').trim();

// Wrap the arrow function in the n8n expression format
const n8nExpression = `={{ (${mastodonPost})($('RSS Feed Trigger').item) }}`;

// Read and parse the workflow JSON
const workflowContent = readFileSync(workflowPath, 'utf-8');
const workflow = JSON.parse(workflowContent);

// Find and update the Mastodon node
const mastodonNodeId = 'e1bd320b-1222-4324-9168-22372d2e667c',
    bskyNodeId = `73f029c7-e8a0-43b0-8bf8-e3be9a09f7d6`,
    telegramNodeId = `ea2afc1b-8446-40ae-a9f1-46f008d8a7a4`;
let mastodonNodeFound = false,
    bskyNodeFound = false,
    telegramNodeFound = false;

if (workflow.nodes && Array.isArray(workflow.nodes)) {
    for (const node of workflow.nodes) {
        switch (node.id) {
            case mastodonNodeId:
                if (!node.parameters) {
                    node.parameters = {};
                }

                node.parameters.status = `={{ (${mastodonPost})($('RSS Feed Trigger').item) }}`;

                mastodonNodeFound = true;
                break;
            case bskyNodeId:
                if (!node.parameters) {
                    node.parameters = {};
                }

                node.parameters.postText = `={{ (${bskyPost})($('RSS Feed Trigger').item) }}`;
                node.parameters.websiteCard.details.uri = `={{ (${bskyLinkCard})($('RSS Feed Trigger').item) }}`;

                bskyNodeFound = true;
                break
            case telegramNodeId:
                if (!node.parameters) {
                    node.parameters = {};
                }

                node.parameters.text = `={{ (${telegramChannel})($('RSS Feed Trigger').item) }}`;

                telegramNodeFound = true;
                break;
        }

        if (mastodonNodeFound && bskyNodeFound && telegramNodeFound) {
            break;
        }
    }
}

if (![bskyNodeFound, mastodonNodeFound, telegramNodeFound].every((x) => x)) {
    console.error(
        `Warning: all notes not found: ` +
        `mastodon node found=${mastodonNodeFound} (id=${mastodonNodeId}), ` +
        `bsky node found = ${ bskyNodeFound} (id=${bskyNodeId}), ` +
        `telegram node found = ${telegramNodeFound} (id=${telegramNodeId})`
    );
    process.exit(1);
}

// Output the updated JSON to stdout
console.log(JSON.stringify(workflow, null, 2));
