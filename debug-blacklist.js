// Exact copy of functions from index.html
function ipToInt(ip) {
    return ip.split('.').reduce((int, octet) => (int << 8) + parseInt(octet, 10), 0) >>> 0;
}

function isIPInCIDR(ip, cidr) {
    if (!cidr.includes('/')) return false;

    const [range, bits] = cidr.split('/');
    const mask = ~(2 ** (32 - parseInt(bits, 10)) - 1);

    return (ipToInt(ip) & mask) === (ipToInt(range) & mask);
}

function isValidIP(str) {
    const ipRegex = /^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/;
    if (!ipRegex.test(str)) return false;

    const parts = str.split('.');
    return parts.every(part => {
        const num = parseInt(part, 10);
        return num >= 0 && num <= 255;
    });
}

// Simulate the exact blacklist checking logic
async function testBlacklistLogic() {
    const rawInput = '1.34.200.229'.toLowerCase();
    const isIPQuery = isValidIP(rawInput);

    console.log('='.repeat(80));
    console.log('DEBUGGING BLACKLIST CHECK');
    console.log('='.repeat(80));
    console.log('rawInput:', rawInput);
    console.log('isIPQuery:', isIPQuery);
    console.log('');

    // Fetch blacklist data
    const url = 'https://raw.githubusercontent.com/diskominfojabar/Panaros/refs/heads/main/data/blacklist-specific.txt';
    console.log('Fetching:', url);

    try {
        const response = await fetch(url, { cache: 'no-cache' });
        const text = await response.text();

        console.log('Response status:', response.status);
        console.log('Data length:', text.length, 'bytes');

        const lines = text.split('\n');
        console.log('Total lines:', lines.length);
        console.log('');

        let foundMatches = [];
        let lineNumber = 0;

        for (let line of lines) {
            lineNumber++;
            let cleanLine = line.trim();

            // Skip comments and empty lines
            if (cleanLine.startsWith('#') || cleanLine.startsWith(';') || cleanLine === "") continue;

            // Extract pattern and reason
            let pattern, fullLine = cleanLine;
            const parts = cleanLine.split(/\s+/);

            // Check if it's hosts format (0.0.0.0 domain) or IP format (IP # comment)
            if (parts[0] === '0.0.0.0' || parts[0] === '127.0.0.1') {
                pattern = parts[1]; // hosts format
            } else {
                // Check for comment marker #
                if (cleanLine.includes(' # ')) {
                    pattern = cleanLine.split(' # ')[0].trim();
                } else {
                    pattern = parts[0];
                }
            }

            if (!pattern) continue;
            pattern = pattern.toLowerCase();

            // Check if this is the line we're looking for
            if (pattern.includes('1.34.200.229')) {
                console.log(`Line ${lineNumber}: ${cleanLine}`);
                console.log('  Extracted pattern:', pattern);
                console.log('  Pattern includes /:', pattern.includes('/'));
                console.log('  isIPQuery:', isIPQuery);
            }

            let matched = false;
            if (pattern.includes('*')) {
                // Wildcard matching for domains
                const escapedPattern = pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
                const regexString = '^' + escapedPattern.replace(/\*/g, '.*') + '$';
                const regex = new RegExp(regexString);
                matched = regex.test(rawInput);
            } else if (pattern.includes('/') && isIPQuery) {
                // CIDR range matching for IPs
                matched = isIPInCIDR(rawInput, pattern);

                if (pattern.includes('1.34.200.229')) {
                    console.log('  Trying CIDR match...');
                    console.log('  Result:', matched);
                }
            } else {
                // Exact match or domain suffix
                matched = (pattern === rawInput) || rawInput.endsWith('.' + pattern);
            }

            if (matched) {
                console.log('');
                console.log('✓ MATCH FOUND!');
                console.log('  Line:', lineNumber);
                console.log('  Pattern:', pattern);
                console.log('  Full line:', cleanLine);
                foundMatches.push({ line: lineNumber, pattern, fullLine: cleanLine });
                break; // Stop after first match
            }
        }

        console.log('');
        console.log('='.repeat(80));
        console.log('RESULT');
        console.log('='.repeat(80));
        if (foundMatches.length > 0) {
            console.log('✓ IP IS BLOCKED');
            console.log('Matches:', foundMatches);
        } else {
            console.log('✗ IP IS NOT BLOCKED');
        }

    } catch (e) {
        console.error('ERROR:', e.message);
        console.error(e);
    }
}

// Run the test
testBlacklistLogic();
