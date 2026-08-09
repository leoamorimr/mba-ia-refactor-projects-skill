// Payment-approval rule extracted out of the route handler and out of a
// bare magic-number check, and card masking so raw PANs never hit logs.

// Stand-in for a real payment-gateway integration: cards whose number
// starts with this prefix are treated as approved test cards. This mirrors
// the original behavior (`cc.startsWith("4")`) but names the rule instead
// of leaving it as an unexplained literal in a route handler.
const APPROVED_TEST_CARD_PREFIX = '4';

const CARD_MASK_VISIBLE_DIGITS = 4;

function isApprovedCard(cardNumber) {
    return typeof cardNumber === 'string' && cardNumber.startsWith(APPROVED_TEST_CARD_PREFIX);
}

function maskCard(cardNumber) {
    if (typeof cardNumber !== 'string' || cardNumber.length <= CARD_MASK_VISIBLE_DIGITS) {
        return '****';
    }
    return `**** **** **** ${cardNumber.slice(-CARD_MASK_VISIBLE_DIGITS)}`;
}

module.exports = { isApprovedCard, maskCard, APPROVED_TEST_CARD_PREFIX };
