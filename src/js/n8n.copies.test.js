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

describe('mastodon status', () => {
    test(`if post is less than 500 chars then no "…more" is added`, () => {
        let actual = n8n.mastodon(item())

        assert.strictEqual(actual, 'hello world\nhttps://example.com/123')
    })

    test(`is post is more than 500 chars then add "…more" and truncate to a total of 476 chars`, () => {
        let actual = n8n.mastodon(item({
            'content:encodedSnippet': 'a'.repeat(5000),
            'contentSnippet': 'a'.repeat(500) // used for getting the content to share
        }))

        assert.strictEqual(actual, 'a'.repeat('469') + '\n… more\nhttps://example.com/123')
        assert.strictEqual(actual.length, 500)
    })

    test(`if the link has utm_medium=feed then change it to utm_medium=mastodon`, () => {
        let actual = n8n.mastodon(item({link: 'https://example.com/?utm_medium=feed'}))

        assert.strictEqual(actual, 'hello world\nhttps://example.com/?utm_medium=mastodon')
    })

    describe(`special scrap handling`, () => {
        test(`if link contains /scrap/ but is truncated, then still include the link`, () => {
            let actual = n8n.mastodon(item({
                'content:encodedSnippet': 'a'.repeat(5000),
                'contentSnippet': 'a'.repeat(500), // used for getting the content to share
                'link': 'https://example.com/scrap/hello-world',
            }))

            assert.strictEqual(actual, 'a'.repeat('469') + '\n… more\nhttps://example.com/scrap/hello-world')
        })

        test(`if link contains /scrap/ and it's not truncated, don't include the link`, () => {
            let actual = n8n.mastodon(item({link: 'https://example.com/scrap/hello-world'}))

            assert.strictEqual(actual, 'hello world')
        })
    })
})


// bsky doesn't have to deal with any special link handling, it's attached as a card to the post.
describe('bsky status', () => {
    test(`if post is less than 300 chars then no "…more" is added`, () => {
        let actual = n8n.bsky(item())

        assert.strictEqual(actual, 'hello world')
    })

    test(`is post is more than 300 chars then add "…more" and truncate to a total of 300 chars`, () => {
        let actual = n8n.bsky(item({
            'content:encodedSnippet': 'a'.repeat(5000),
            'contentSnippet': 'a'.repeat(500) // used for getting the content to share
        }))

        assert.strictEqual(actual, 'a'.repeat('293') + '\n… more')
        assert.strictEqual(actual.length, 300)
    })

    describe(`special scrap handling`, () => {
        test(`if link contains /scrap/ but is truncated, then still include the link`, () => {
            let actual = n8n.bsky(item({
                'content:encodedSnippet': 'a'.repeat(5000),
                'contentSnippet': 'a'.repeat(500), // used for getting the content to share
                'link': 'https://example.com/scrap/hello-world',
            }))

            assert.strictEqual(actual, 'a'.repeat('293') + '\n… more')
        })
    })
})

describe('bsky link card attacher', () => {
    test(`if post is less than 300 chars but doesn't contain /scrap/ then add link`, () => {
        let actual = n8n.bskyLinkCard(item())

        assert.strictEqual(actual, 'https://example.com/123')
    })

    test(`is post is more than 300 chars then return the link`, () => {
        let actual = n8n.bskyLinkCard(item({
            'content:encodedSnippet': 'a'.repeat(5000),
            'contentSnippet': 'a'.repeat(500) // used for getting the content to share
        }))

        assert.strictEqual(actual, 'https://example.com/123')
    })

    test(`if the link has utm_medium=feed then change it to utm_medium=bsky`, () => {
        let actual = n8n.bskyLinkCard(item({
            'content:encodedSnippet': 'a'.repeat(5000),
            'contentSnippet': 'a'.repeat(500), // used for getting the content to share
            'link': 'https://example.com/?utm_medium=feed'
        }))

        assert.strictEqual(actual, 'https://example.com/?utm_medium=bsky')
    })


    describe(`special scrap handling`, () => {
        test(`if link contains /scrap/ but is truncated, then still include the link`, () => {
            let actual = n8n.bskyLinkCard(item({
                'content:encodedSnippet': 'a'.repeat(5000),
                'contentSnippet': 'a'.repeat(500), // used for getting the content to share
                'link': 'https://example.com/scrap/hello-world',
            }))

            assert.strictEqual(actual, 'https://example.com/scrap/hello-world')
        })

        test(`if link contains /scrap/ and it's not truncated, don't include the link`, () => {
            let actual = n8n.bskyLinkCard(item({link: 'https://example.com/scrap/hello-world'}))

            assert.strictEqual(actual, '')
        })
    })
})
