/* Poor man's version control: I don't feel like doing an n8n package yet,
 * so let's start by making some easy to copy/paste things that I can keep in here instead.
 *
 *
 */

/**
 *
 * @param item { json: { contentSnippet: string, 'content:encodedSnippet': string, link: string } }
 * @returns {string}
 */
//<EXTRACT:mastodon>
let mastodon = (item) => {
    let msgLength = 500-23-1, // the default mastodon post size is 500, -23 chars for the link, and -1 char for newline
        truncateIndicator = '\n… more';

    let wordTruncate = (str, n, indicator) => {
        if (indicator === undefined) indicator = '…';
        if(str.length <= n) return str.trimEnd();

        n -= indicator.length;
        if(str[n] === ' ') return str.substring(0, n).trimEnd();

        let ret = str.substring(0, n).trimEnd(),
            i = ret.lastIndexOf(' ');

        // when there are no spaces at all, just cut in the middle of the text.
        if (i === -1) return ret.substring(0, n);

        return ret.substring(0, i).trimEnd();
    }

    let msg = wordTruncate(item.json.contentSnippet, msgLength, truncateIndicator),
        isTruncated = msg !== item.json.contentSnippet,
        retMsg = isTruncated ? msg + truncateIndicator : msg,
        link = item.json.link;

    // Don't link to scraps when it's all contained in the post.
    if(!isTruncated && link.includes('/scrap/')) {
        return msg;
    }

    return retMsg + `\n${item.json.link.replace('utm_medium=feed', 'utm_medium=mastodon')}`
}
//</EXTRACT:mastodon>

//<EXTRACT:bsky>
let bsky = (item) => {
    let msgLength = 300, // length of a bsky post
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

    let msg = wordTruncate(item.json.contentSnippet, msgLength, truncateIndicator),
        isTruncated = msg !== item.json.contentSnippet;

    return isTruncated ? msg + truncateIndicator : msg;
}
//</EXTRACT:bsky>

//<EXTRACT:bskyLinkCard>
let bskyLinkCard = (item) => {
    let isTruncated = item.json.contentSnippet.length > 300;

    return !isTruncated && item.json.link.includes('/scrap/') ? '' : item.json.link.replace('utm_medium=feed', 'utm_medium=bsky');
}
//</EXTRACT:bskyLinkCard>

module.exports = {
    bsky,
    bskyLinkCard,
    mastodon
}
