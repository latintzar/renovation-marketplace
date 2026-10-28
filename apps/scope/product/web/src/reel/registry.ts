/**
 * Reel script registry. Adding a flow = add one script file + one entry here.
 * Flows not yet scripted are simply absent (the switcher disables them).
 */

import type { ReelScript } from './engine';
import { reelFlowId, type ReelFlowId } from './flag';
import { postJobScript } from './scripts/post-job';
import { setMilestonesScript } from './scripts/set-milestones';
import { approveReleaseScript } from './scripts/approve-release';
import { submitProofScript } from './scripts/submit-proof';
import { importProfileScript } from './scripts/import-profile';

export const REEL_SCRIPTS: Partial<Record<ReelFlowId, ReelScript>> = {
  'post-job': postJobScript,
  'set-milestones': setMilestonesScript,
  'submit-proof': submitProofScript,
  'approve-release': approveReleaseScript,
  'import-profile': importProfileScript,
};

/** The script for the active reel flow, or undefined when reel mode is off. */
export function activeScript(): ReelScript | undefined {
  const id = reelFlowId();
  return id ? REEL_SCRIPTS[id] : undefined;
}
