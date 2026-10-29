# DhanPulse Stable signing

Build 56 begins a stable installation lineage using application ID `in.dhanpulse.personal.stable`. It installs alongside the old `in.dhanpulse.personal.flowpreview` app. Local settings are not migrated; log in again.

Do not generate a new signing key for updates. The private key is preserved in the owner private backup named DhanPulse_Stable_Signing_Backup.zip. Never commit or upload it to public artifacts. The public certificate is stable-signing-certificate.pem.

CI produces an UNSIGNED release APK, not an installable download. Sign it with the preserved key using apksigner, then verify the signer certificate matches the checked in certificate. Increment versionCode for every update. Never distribute unsigned CI artifacts or substitute a temporary debug key.

Signing example, with private backup extracted outside the repository:
```sh
java -jar apksigner.jar sign --ks /private/dhanpulse-stable.p12 --ks-key-alias dhanpulse-stable --ks-pass file:/private/store-password.txt --out DhanPulse-Stable.apk app-release-unsigned.apk
java -jar apksigner.jar verify --verbose --print-certs DhanPulse-Stable.apk
```

This packaging change does not change broker routes, API keys, backend deployments or strategy rules.
