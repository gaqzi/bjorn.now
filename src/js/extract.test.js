import {describe, test} from 'node:test';
import assert from 'node:assert';

import * as extract from './extract.js';

describe('extract.fromFile', () => {
    test(`if the markers aren't found, then nothing is returned`, () => {
        let actual = extract.fromFile('./testdata/no-markers.txt', 'test')

        assert.strictEqual(actual, '', 'expected an empty string when no match found')
    })

    test(`if the markers are found, the content is returned`, () => {
        let actual = extract.fromFile('./testdata/plain-text.txt', 'test')

        assert.strictEqual(actual, 'Hello, World!\n', 'expected the content between the markers')
    })

    test(`that anything else on the same line as the markers is ignored`, () => {
        let actual = extract.fromFile('./testdata/marker-with-noise.txt', 'test')

        assert.strictEqual(
            actual,
            'Hello, Signal!\n',
            'expected the content between the marker lines, ignoring trailing/leading info on the marker lines',
        )
    })

    test(`if the end marker is before the start marker, then raise an exception telling us that`, () => {
        assert.throws(() => {
            extract.fromFile('./testdata/end-before-the-beginning.txt', 'test')
        }, new Error(`Invalid marker: <EXTRACT:test> not found before </EXTRACT:test>`))
    })
})
