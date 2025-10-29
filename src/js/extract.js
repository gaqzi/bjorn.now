import {readFileSync} from 'node:fs';

/**
 * Extract the content between <EXTRACT:name></EXTRACT:name> tags in a file.
 * The lines with the markers are removed the output.
 *
 * @param filePath {string} path to the file
 * @param name {string} the part after the colon in the marker
 * @returns {string} the content between the markers or an empty string if nothing found
 */
export function fromFile(filePath, name) {
    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n');

    const startMarker = `<EXTRACT:${name}>`;
    const endMarker = `</EXTRACT:${name}>`;

    const startIndex = lines.findIndex(line => line.includes(startMarker));
    const endIndex = lines.findIndex(line => line.includes(endMarker));

    if (startIndex === -1 || endIndex === -1) {
        return '';
    }
    if (startIndex >= endIndex) {
        throw new Error(`Invalid marker: ${startMarker} not found before ${endMarker}`);
    }

    // Extract lines between markers (excluding the marker lines)
    const extractedLines = lines.slice(startIndex + 1, endIndex);
    return extractedLines.join('\n') + (extractedLines.length > 0 ? '\n' : '');
}
