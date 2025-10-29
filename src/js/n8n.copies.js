/* Poor man's version control: I don't feel like doing an n8n package yet,
 * so let's start by making some easy to copy/paste things that I can keep in here instead.
 *
 *
 */

/**
 *
 * @param item { json: { contentSnippet: string, content: string, 'content:encodedSnippet': string, link: string } }
 * @returns {string}
 */
let mastodon = (item) => {
    let msg = item.json.contentSnippet,
        msgLength = 500-23-1, // the default mastodon post size is 500, -23 chars for the link, and -1 char for newline
        isTruncated = item.json['content:encodedSnippet'] !== item.json.contentSnippet,
        truncateIndicator = '\n… more';

    let wordTruncate = (str, n, indicator) => {
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

    msg = wordTruncate(msg, msgLength, truncateIndicator);
    return isTruncated ? msg + truncateIndicator : msg;
}
// )($('RSS Feed Trigger').item)

let bsky = (item) => {
    let msg = item.json.contentSnippet,
        msgLength = 300, // length of a bsky post
        isTruncated = item.json['content:encodedSnippet'] !== item.json.contentSnippet,
        truncateIndicator = '\n… more';

    let wordTruncate = (str, n, indicator) => {
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

    msg = wordTruncate(msg, msgLength, truncateIndicator);
    return isTruncated ? msg + truncateIndicator : msg;
}
// )($('RSS Feed Trigger').item)

module.exports = {
    bsky,
    mastodon
}
