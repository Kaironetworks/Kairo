'use strict';
const { Contract } = require('fabric-contract-api');

class KairoTrustContract extends Contract {
  async Anchor(ctx, anchorId, documentId, version, evidenceHash, custodyHash, actor, action, timestamp) {
    if (!anchorId || !documentId || !evidenceHash) throw new Error('anchorId, documentId and evidenceHash are required');
    const exists = await ctx.stub.getState(anchorId);
    if (exists && exists.length) throw new Error(`Anchor ${anchorId} already exists`);
    const record = {
      anchorId, documentId, version: Number(version), evidenceHash,
      custodyHash: custodyHash || '', actor: actor || '', action: action || '',
      timestamp: timestamp || new Date().toISOString(),
      txId: ctx.stub.getTxID()
    };
    await ctx.stub.putState(anchorId, Buffer.from(JSON.stringify(record)));
    return JSON.stringify(record);
  }

  async ReadAnchor(ctx, anchorId) {
    const data = await ctx.stub.getState(anchorId);
    if (!data || data.length === 0) throw new Error(`Anchor ${anchorId} does not exist`);
    return data.toString();
  }

  async AnchorExists(ctx, anchorId) {
    const data = await ctx.stub.getState(anchorId);
    return !!(data && data.length);
  }
}

module.exports = { KairoTrustContract };
