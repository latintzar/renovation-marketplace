# Historical scripted walkthroughs

This optional historical presentation is the original product's scripted quote flow. It uses the actual React pages and shared components, with a sample contractor, homeowner and project.

```sh
make install
make doctor
make walkthrough-build
make walkthrough
```

Open `http://127.0.0.1:18260/app/quote/first?reel=set-milestones`.

The conversation builds three priced phases beside the quote document. Choose Edit to inspect the native editable canvas. The restored document includes work phases, materials, the proportional payment bar, IVA and the service-fee summary.

Other original entries:

| Entry | Local path |
| --- | --- |
| Homeowner brief | `/app/onboard/homeowner?reel=post-job` |
| Contractor quote | `/app/quote/first?reel=set-milestones` |
| Contractor proof | `/app/dashboard?reel=submit-proof` |
| Homeowner review | `/app/project/reel?reel=approve-release` |
| Profile import | `/app/onboard/pro?reel=import-profile` |

The flow switcher follows the original script. `?reel=off` clears the saved script selection. Standard sign-in and connected features use your own configured backend and providers.

These walkthroughs demonstrate interface behaviour with scripted replies and state. Payment transfers, identity verification, messages and model execution have separate integration acceptance.

## Source

- [`reel/flag.ts`](../apps/scope/product/web/src/reel/flag.ts) selects the flow.
- [`reel/engine.ts`](../apps/scope/product/web/src/reel/engine.ts) intercepts the HTTP boundary and owns sample state.
- [`reel/scripts/`](../apps/scope/product/web/src/reel/scripts/) retains the five original flows.
- [`tools/dev.py`](../tools/dev.py) serves only the built UI, bound to loopback.

## Browser proof

The optional browser check uses Playwright and a local running starter:

```sh
python -m pip install playwright
python -m playwright install chromium
python tests/browser_walkthrough.py
```

It opens all five original entries at desktop and phone sizes, blocks remote HTTP and checks the final quote's materials, IVA and €8,190 total. The captured product images use the same pages; their walkthrough switcher and narration are hidden for legibility. [Capture record](../provenance/ui-captures.json).
