// Test IPv6 CIDR Matching Logic
// Run with: node test-ipv6.js

function isIPv6(str) {
    return str.includes(':');
}

function normalizeIPv6(ip) {
    ip = ip.replace(/^\[|\]$/g, '');

    if (ip.includes('::')) {
        const sides = ip.split('::');
        const leftGroups = sides[0] ? sides[0].split(':') : [];
        const rightGroups = sides[1] ? sides[1].split(':') : [];
        const missingGroups = 8 - leftGroups.length - rightGroups.length;
        const middleGroups = Array(missingGroups).fill('0000');
        const allGroups = [...leftGroups, ...middleGroups, ...rightGroups];
        ip = allGroups.join(':');
    }

    return ip.split(':').map(g => g.padStart(4, '0')).join(':');
}

function ipv6ToBigInt(ip) {
    const normalized = normalizeIPv6(ip);
    const groups = normalized.split(':');
    let result = BigInt(0);

    for (let i = 0; i < groups.length; i++) {
        const value = BigInt(parseInt(groups[i], 16));
        result = (result << BigInt(16)) | value;
    }

    return result;
}

function isIPInCIDR(ip, cidr) {
    if (!cidr.includes('/')) return false;

    const [range, bits] = cidr.split('/');

    if (!isIPv6(ip) || !isIPv6(range)) {
        console.log('Not IPv6');
        return false;
    }

    try {
        const ipInt = ipv6ToBigInt(ip);
        const rangeInt = ipv6ToBigInt(range);
        const prefixLen = parseInt(bits, 10);

        // Compare first prefixLen bits by shifting right
        const shift = BigInt(128 - prefixLen);
        return (ipInt >> shift) === (rangeInt >> shift);
    } catch (e) {
        console.error('[ERROR]', e.message);
        return false;
    }
}

// Test cases
console.log('='.repeat(60));
console.log('IPv6 CIDR Matching Tests');
console.log('='.repeat(60));

const tests = [
    // Test 1: Exact match /128
    { ip: '2001:470:1:332::4', cidr: '2001:470:1:332::4/128', expected: true, desc: 'Exact /128 match' },

    // Test 2: Different IP in same /64 subnet
    { ip: '2001:470:1:332::5', cidr: '2001:470:1:332::/64', expected: true, desc: 'IP in /64 subnet' },

    // Test 3: IP NOT in /64 subnet
    { ip: '2001:470:1:333::1', cidr: '2001:470:1:332::/64', expected: false, desc: 'IP NOT in /64 subnet' },

    // Test 4: Compressed IPv6 address
    { ip: '2001:db8::1', cidr: '2001:db8::/32', expected: true, desc: 'Compressed IPv6 in /32' },

    // Test 5: IP in /48 subnet (first 48 bits must match)
    { ip: '2001:db8:0:1234::1', cidr: '2001:db8:0::/48', expected: true, desc: 'IP in /48 subnet' },

    // Test 6: Loopback
    { ip: '::1', cidr: '::1/128', expected: true, desc: 'Loopback exact match' },
];

tests.forEach((test, idx) => {
    const result = isIPInCIDR(test.ip, test.cidr);
    const status = result === test.expected ? '✓ PASS' : '✗ FAIL';
    const color = result === test.expected ? '\x1b[32m' : '\x1b[31m';

    console.log(`\nTest ${idx + 1}: ${test.desc}`);
    console.log(`  IP: ${test.ip}`);
    console.log(`  CIDR: ${test.cidr}`);
    console.log(`  Expected: ${test.expected}, Got: ${result}`);
    console.log(`  ${color}${status}\x1b[0m`);
});

console.log('\n' + '='.repeat(60));
console.log('Test Complete');
console.log('='.repeat(60));
