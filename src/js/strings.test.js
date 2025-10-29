import { describe, test } from 'node:test';
import assert from 'node:assert';

import * as strings from './strings.js';

describe('wordTruncate', () => {
    test(`returns str if less than n `, () => {
        assert.strictEqual(strings.wordTruncate('', 5), '');
        assert.strictEqual(strings.wordTruncate('hello', 10), 'hello');
    });

    test(`returns the truncated word up until n if str[n] is a space`, () => {
        assert.strictEqual(strings.wordTruncate('hello world', 5), 'hell');
        assert.strictEqual(strings.wordTruncate('hello  world', 7), 'hello', 'always trimEnd in case there are multiple spaces');
    })

    describe(`when n is within a word`, () => {
        test(`return the str at the word before the current`, () => {
            assert.strictEqual(strings.wordTruncate('hello world', 8), 'hello');
        })

        test(`when it's one giant word, cut and keep indicator length in mind`, () => {
            assert.strictEqual(strings.wordTruncate('hello', 4), 'hel');
        })
    })

    test(`returns indicator if n is 0`, () => {
        assert.strictEqual(strings.wordTruncate('hello', 0, '… blupp'), '');
    });

    test(`returns str unchanged when length is exactly`, () => {
        assert.strictEqual(strings.wordTruncate('hello', 5), 'hello');
    })

    describe(`with a custom truncation indicator`, () => {
        test(`includes it in the str length`, () => {
            assert.strictEqual(strings.wordTruncate('hello world!', 11, '… more'), 'hello');
        })
    })
});
