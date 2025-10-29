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
            'content:encodedSnippet': 'hello world',
            link: 'https://example.com/123' // only to force it to 23chars to make life easier for me
        }, overrides)
    }
}

function statusCreatorTest(for_, func, characterLength, linkLength) {
    return () => {
        test(`if post is less than ${characterLength} chars then no "…more" is added`, () => {
            let actual = func(item())

            assert.strictEqual(actual, 'hello world\nhttps://example.com/123')
        })

        test(`is post is more than ${linkLength} chars then add "… more" and truncate to a total of ${characterLength-linkLength-1} chars`, () => {
            let actual = func(item({
                'content:encodedSnippet': 'a'.repeat(characterLength*10),
                'contentSnippet': 'a'.repeat(characterLength) // used for getting the content to share
            }))

            assert.strictEqual(actual, 'a'.repeat(characterLength-linkLength-8) + '\n… more\nhttps://example.com/123')
            assert.strictEqual(actual.length, characterLength)
        })

        test(`if the link has utm_medium=feed then change it to utm_medium=${for_}`, () => {
            let actual = func(item({link: 'https://example.com/?utm_medium=feed'}))

            assert.strictEqual(actual, `hello world\nhttps://example.com/?utm_medium=${for_}`)
        })

        describe(`special scrap handling`, () => {
            test(`if link contains /scrap/ but is truncated, then still include the link`, () => {
                let actual = func(item({
                    'content:encodedSnippet': 'a'.repeat(characterLength*10),
                    'contentSnippet': 'a'.repeat(characterLength), // used for getting the content to share
                    'link': 'https://example.com/scrap/hello-world',
                }))

                assert.strictEqual(actual, 'a'.repeat(characterLength-linkLength-8) + '\n… more\nhttps://example.com/scrap/hello-world')
            })

            test(`if link contains /scrap/ and it's not truncated, don't include the link`, () => {
                let actual = func(item({link: 'https://example.com/scrap/hello-world'}))

                assert.strictEqual(actual, 'hello world')
            })
        })
    }
}

describe('mastodon status', statusCreatorTest('mastodon', n8n.mastodon, 500, 23))
