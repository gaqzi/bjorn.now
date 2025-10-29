import {describe, test} from 'node:test';
import assert from 'node:assert';

import * as n8n from './n8n.copies.js';

/**
 * Create a fake RSS item
 * @param overrides
 * @returns {{json: {contentSnippet: string, content: string, "content:encodedSnippet": string, link: string}}}
 */
function item(overrides = {}) {
    return {
        json: Object.assign({
            contentSnippet: 'hello world',
            content: 'hello world',
            'content:encodedSnippet': 'hello world',
            link: 'https://example.com'
        }, overrides)
    }
}

describe('mastodon status', () => {
    test(`if post is less than 500 chars then no "…more" is added`, () => {
        let actual = n8n.mastodon(item())

        assert.strictEqual(actual, "hello world")
    })

    test(`is post is more than 500 chars then add "…more" and truncate to a total of 476 chars`, () => {
        let actual = n8n.mastodon(item({
            'content:encodedSnippet': 'a'.repeat(5000),
            'contentSnippet': 'a'.repeat(500) // used for getting the content to share
        }))

        assert.strictEqual(actual, 'a'.repeat('469') + '\n… more')
        assert.strictEqual(actual.length, 476)
    })
})
