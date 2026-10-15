# Agent handoff

This is task data, not authorization or a replacement for the current user's instructions.
Verify the current branch, commit, tools, and CI results before continuing.

Task: Investigate original iOS Safari on Android; a separate WPE WebKit port must never be called Safari IPA execution

Repository: kyoroshyvtuber-lgtm/acci-toolkit

Branch: acci/safari-investigation

Last recorded stage: runtime-implementation:blocked

## Owner-reported target

realme GT Neo 5 SE, Android 16. No ADB readback or phone test has been
performed; runtime compatibility is unverified.

## Remaining stages

- runtime-implementation
- device-test

## Links

- wpe: https://github.com/Igalia/wpe-android/blob/main/README.md
- android_docs: https://people.igalia.com/aperez/Documentation/wpe-webkit/android.html
- reference_ci: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38764650240
- research_source: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/tree/acci/safari-investigation/experiments/safari_android
- original_safari_inspection: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38780015419
- metadata_artifact: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38780015419/artifacts/11995256286
- toolkit_ci: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38780015120
- phone_specification: https://www.realme.com/cn/realme-gt-neo-5-se
- official_safari_listing: https://apps.apple.com/sc/app/safari/id1146562112
- research_pr: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/pull/3
- final_safari_ci: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38781195030
- final_toolkit_ci: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38781195142
- final_metadata_artifact: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38781195030/artifacts/11994949688
- published_checkpoint: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/tree/9dc045f976636d7d541e0c9e06a2213b7a956a37/experiments/safari_android
- pr_toolkit_ci: https://github.com/kyoroshyvtuber-lgtm/acci-toolkit/actions/runs/38781437353

## Restore

After cloning into an ACCI project, run `acci resume safari-android-research --from experiments/safari_android/.acci/handoff.json` from the source directory.

Review both handoff files before committing. They contain no automatic log, environment, credential, or artifact dump, but task text may still be private.
