/**
 * Truncate a string to n characters at word boundaries with no trailing spaces or indicator for truncation.
 * Indicator is removed from n to ensure string length, but it's on the caller to attach the indicator.
 * If there is no space, then truncate the word where needed.
 *
 * Edge case: if the indicator is longer than n, will return an empty string. Felt better than exception.
 *
 * @param str the string to truncate
 * @param n the number of characters max allowed to be returned
 * @param indicator the indicator to use when truncating, default '…'.
 * @returns {string} the truncated string
 */
export function wordTruncate(str, n, indicator) {
    if (indicator === undefined) indicator = '…';
    if(str.length <= n) return str.trimEnd();

    n -= indicator.length;
    if(str[n] === ' ') return str.substring(0, n).trimEnd();

    let ret = str.substring(0, n).trimEnd(),
        i = ret.lastIndexOf(' ');

    // when there's no spaces at all, just cut in the middle of the text.
    if (i === -1) return ret.substring(0, n);

    return ret.substring(0, i).trimEnd();
}
