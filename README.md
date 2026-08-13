# Open iCloud Passwords for Chrome

> Open-source iCloud Keychain autofill for Chrome and Edge on macOS

![platform](https://img.shields.io/badge/platform-macOS%2014%2B-black)
![browser](https://img.shields.io/badge/browser-Chrome%20%7C%20Edge-4285F4)
![manifest v3](https://img.shields.io/badge/manifest-v3-brightgreen)
![license](https://img.shields.io/badge/license-Apache--2.0-blue)

---

Apple's official iCloud Passwords Chrome extension sits at **2.3 / 5** across roughly 2,600 ratings. It forgets the session every few hours and re-asks for the 6-digit code, pops an "enable autofill" bubble on one-time-code inputs, and fights with Chrome's built-in password manager. **This project is a replacement client for it.**

It speaks the same native-messaging protocol as Apple's extension (`com.apple.passwordmanager`): a single SRP-6a handshake in which the 6-digit code shown on your Mac is the shared secret, followed by an AES-GCM encrypted channel for password queries. Same vault, same system authorization — just a client that behaves sensibly.

Connect to the live vault, prompt for the PIN once, list the logins for the current site, and fill.

## Table of Contents

- [Features](#features)
  - [Overview: what it fixes](#overview-what-it-fixes)
  - [Full comparison with Apple's official extension](#full-comparison-with-apples-official-extension)
  - [What it does not fix](#what-it-does-not-fix)
- [Install and use](#install-and-use)
  - [Requirements](#requirements)
  - [Installation](#installation)
  - [Optional: hide the browser's built-in password manager](#optional-hide-the-browsers-built-in-password-manager)
- [How it works](#how-it-works)
- [Extension identity and limits](#extension-identity-and-limits)
  - [What you must know first](#what-you-must-know-first)
  - [Why a version with its own ID cannot work](#why-a-version-with-its-own-id-cannot-work)
  - [Apple public-key reference](#apple-public-key-reference)
- [Security and audit](#security-and-audit)
  - [Security notes](#security-notes)
  - [Verification and audit log](#verification-and-audit-log)
- [Credits and license](#credits-and-license)

---

## Features

### Overview: what it fixes

| Common complaint about Apple's extension | What this project does |
| --- | --- |
| Re-asks for the 6-digit code on every restart, sometimes every few hours | A keep-alive timer keeps the MV3 worker and the session alive, so you enter the code once per real session ([`background.js`](src/background.js)) |
| Pops an "enable autofill" bubble on every field, including OTP boxes | The inline dropdown appears only on genuine login fields, never on one-time-code inputs ([`content.js`](src/content.js)) |
| 100% CPU / typing lag | The content script has zero per-keystroke overhead and only reacts when you focus a login field |
| Re-downloads every image on hover to scan for QR codes | No image or QR scanning at all |
| Fills the wrong field or the wrong origin | Fills are pinned to the page origin and skip hidden / clickjacked fields |

Two ways to fill: an **inline dropdown** when you focus a login field, or the **toolbar popup**. Both take the same origin-checked, system-authorized path.

### Full comparison with Apple's official extension

This maps 18 documented complaints about Apple's official iCloud Passwords Chrome / Edge extension, one by one, to what this project does. "Verified" means there is an automated headless test in `test-harness/` proving it (real Chrome loading the real extension). Sources are user reports on the Chrome Web Store, Apple Communities, Google / Brave forums, GitHub, AppleInsider, and Macworld.

Legend: ✅ fixed · 🟡 partially fixed · ⛔ inherent limit (no extension can fix it)

| # | Complaint | Apple's behavior | This project | Status |
| --- | --- | --- | --- | --- |
| 1 | Repeatedly asks for the 6-digit code (top complaint) | Re-pairs on every restart, often every few hours; every capabilities reload resets the session | A keep-alive keeps the MV3 worker and the live session alive, and benign reconnects never reset it, so the frequent mid-session re-asks disappear. Only a full browser restart re-pairs (the session key is bound to the connection; both Apple and au2001 re-handshake per connection) | ✅/⛔ |
| 2 | Verification code never arrives | The helper deadlocks; it says a code was generated but nothing appears | Replaced with an 8-second timeout plus a clear error; a broken helper is a helper-side problem | 🟡 |
| 3 | "Cannot verify your identity" | The server / helper rejects the browser | Helper-side / Apple gate | ⛔ |
| 4 | An "enable autofill" bubble on every OTP box and random field | Pops on one-time-code boxes and non-login fields | Never appears on OTP fields, search, tags, comments, etc. Verified: 22/22 adversarial pages with no bubble; no bubble on OTP pages | ✅ |
| 5 | High CPU / typing lag | Rescans the DOM and re-attaches listeners on every keystroke | Zero per-keystroke, zero DOM-scan overhead, a single `focusin` listener. Typing is free | ✅ |
| 6 | Double popup with Chrome's manager | Two managers fight over the same field | Suppresses only Chrome's password autofill (see #7), leaving one clean dropdown | ✅ |
| 7 | Breaks Google Pay / payment autofill | Apple's "disable Chrome autofill" also kills credit-card and address autofill | Suppresses only `passwordSavingEnabled`; Chrome's payment and address autofill keep working | ✅ |
| 8 | Two-step (username-then-password) logins fail | Does not re-detect a dynamically revealed password field | `autocomplete="username"` plus full-page password detection handles Google / Microsoft-style two-step logins. Verified in the UI test suite | ✅ |
| 9 | Fills, but you must change one character before login works | Programmatic fill does not dispatch `input`/`change`, so page JS never sees the value | Every fill dispatches real `input` and `change` events. Verified: both events fire on both fields | ✅ |
| 10 | Subdomain / domain matching fails | Strict exact-host matching | Hands the full hostname to the helper, which does Apple's own associated-domain matching | 🟡 |
| 11 | Popup blocks the screen / can't be dismissed | Overlay z-index and positioning bugs, dismisses too early | The dropdown anchors below the field, closes on outside click / scroll / zoom, and never blocks the field | ✅ |
| 12 | "Never save" flag gets stuck, can't be cleared away from the Mac | No UI to clear it | No save-flag management yet (no save feature) | ⛔/n/a |
| 13 | Saving a new password auto-saves without consent | Aggressive auto-capture | No auto-save, no silent capture; there is also no save prompt yet | 🟡 |
| 14 | No Linux support | Requires the macOS / Windows helper | Same limit; the helper only exists on macOS / Windows | ⛔ |
| 15 | Repeated Touch ID prompt friction | Prompts on every fill | The biometric gate is controlled by the system (`RequiresUserAuthenticationToFill`) and cannot be removed | ⛔ |
| 16 | Toolbar icon invisible in dark mode | Monochrome icon | The UI uses `Canvas`/`CanvasText` system colors (theme-aware); the icon is a to-do | 🟡 |
| 17 | Windows version coupling | Locked to a specific iCloud for Windows build | Helper-side | ⛔ |
| 18 | Clickjacking / autofill UI spoofing (Marek Tóth 2025; affects Apple, 1Password, Bitwarden) | Autofills into invisible / covered fields | Requires visible fields (size / opacity / off-screen checks), an explicit user click, and origin pinning. Verified: an off-screen hidden password field is not filled | ✅ |

#### What it fixes that Apple did not

- OTP bubbles and false triggers (#4): 22/22 adversarial pages clean
- Frequent mid-session re-asks (#1): keep-alive plus no reset
- The "change one character to log in" bug (#9): correct input events
- Breaking Google Pay (#7): payment autofill untouched
- Typing lag (#5): zero per-keystroke overhead
- Clickjacking theft (#18): visibility, intent, and origin checks

#### What it cannot fix

- Linux (#14), Windows helper coupling (#17), "unsupported browser" rejections (#3), and the helper-side part of #2 all require Apple's native helper, which no extension controls.
- The Touch ID prompt (#15) and the one-per-browser-restart re-pairing (#1): both the system and the protocol require them, and Apple's own extension does the same.

#### Not built yet

- A prompt to save new passwords (#13), and a settings UI to clear "never save" (#12).

Every ✅ above is backed by an automated test in `test-harness/automation/`. The last run totaled: 22/22 adversarial, 17/17 UI, 4/4 PIN, plus multi-account, input events (#9), and clickjacking (#18).

### What it does not fix

- **The macOS authorization prompt.** When the helper reads a password, macOS itself asks for Touch ID or the login password. That is the `RequiresUserAuthenticationToFill` flag the vault sets per credential. Chrome's built-in manager skips it only because it stores passwords in its own database rather than the iCloud vault; removing it means giving up live-vault access.
- **No Linux support.** Like Apple, the native helper only exists on macOS and Windows.
- **No passkey or TOTP management.** Out of scope; this project only reads passwords and login names.
- **It still depends on Apple's helper.** If Apple changes or breaks it (past macOS updates have), this project breaks with it.

---

## Install and use

### Requirements

- macOS 14 (Sonoma) or later, signed into iCloud with Passwords enabled
- Chrome or Edge
- Apple's official iCloud Passwords extension removed or disabled

### Installation

```bash
git clone https://github.com/enjoychaim/open-icloud-passwords.git
```

1. Disable Apple's official iCloud Passwords extension (it occupies the same ID)
2. Open `chrome://extensions` (Edge: `edge://extensions`) and turn on **Developer mode** at the top right
3. Click **Load unpacked** and select the `open-icloud-passwords` folder
4. Confirm the ID matches your browser (to switch keys, see [Apple public-key reference](#apple-public-key-reference)):
   - Chrome → `pejdijmoenmkgeppbflobdenhhabjlaj`
   - Edge → `mfbcdcnpokpoajjciilocoachedjkima`
5. Click the toolbar icon, enter the 6-digit code shown on your Mac, and you're done
6. Open a site with a saved login and fill

### Optional: hide the browser's built-in password manager

The popup alone can suppress the browser's competing save bubble and autofill dropdown (toggles in the footer). To also remove the browser's **entire** password manager — the key icon in the address bar and the built-in autofill — there is a one-time helper, because the extension itself cannot write a macOS policy:

```bash
./native/install.sh   # registers a tiny native helper, macOS only
```

Then quit and reopen the browser completely (`Cmd+Q`). The **Hide browser password manager entirely** toggle in the popup takes effect at that point; it sets `PasswordManagerEnabled=false` for all your Chromium browsers. Undo it anytime with `./native/uninstall.sh`. The helper runs only three fixed `defaults` commands and accepts messages only from this extension's ID.

---

## How it works

```
popup.js / content.js
        │  runtime messages
        ▼
background.js  ──  keep-alive timer keeps the session alive
        │
        ▼
protocol.js  ──  chrome.runtime.connectNative("com.apple.passwordmanager")
        │            GET_CAPABILITIES → m0 (challenge/PIN) → m2 (verify) → query
        ▼
srp.js + crypto.js   SRP-6a (RFC 5054, 3072-bit) + AES-GCM session
        ▼
PasswordManagerBrowserExtensionHelper (macOS native, talks to iCloud Keychain)
```

Module responsibilities:

| File | Responsibility |
| --- | --- |
| [`popup.js`](src/popup.js) / [`popup.html`](src/popup.html) / [`popup.css`](src/popup.css) | Toolbar popup UI: enter the PIN, list and fill logins, feature toggles |
| [`content.js`](src/content.js) | Content script: detect login fields, render the inline dropdown, perform the fill |
| [`background.js`](src/background.js) | MV3 service worker: keep-alive, message routing, origin / tab resolution |
| [`protocol.js`](src/protocol.js) | Native-messaging client: handshake state machine, request serialization |
| [`srp.js`](src/srp.js) / [`crypto.js`](src/crypto.js) | SRP-6a handshake and AES-GCM session encryption/decryption |
| [`passkey-bridge.js`](src/passkey-bridge.js) / [`passkey-guard.js`](src/passkey-guard.js) | Passkey-related page bridge and guard |

---

## Extension identity and limits

### What you must know first

> **⚠️ Important:** This is a tool that you **sideload** from GitHub. It **cannot be published to the Chrome Web Store**, and the reason lies in macOS itself.

macOS 14+ ships with a native helper, `PasswordManagerBrowserExtensionHelper`. On macOS 15.4 and later, that helper accepts connections only from two **hard-coded extension IDs** — Apple's own Chrome and Edge extensions. Those IDs are compiled into the signed system binary and everything else is refused.

So, to be able to connect, this extension's `manifest.json` carries Apple's extension public `key`, which makes the browser assign it the ID the helper recognizes. The two usable keys and their derived IDs are recorded in [Apple public-key reference](#apple-public-key-reference):

| Browser | Extension ID |
| --- | --- |
| Chrome | `pejdijmoenmkgeppbflobdenhhabjlaj` |
| Edge | `mfbcdcnpokpoajjciilocoachedjkima` |

This is the only way a Chromium extension can reach that helper on current macOS. For you it means:

- ✅ Works when loaded unpacked for **personal use**
- ❌ **Cannot be published to the Web Store**, because those IDs and keys belong to Apple
- ⚠️ You must **disable Apple's official iCloud Passwords extension first**, because two extensions cannot share one ID in the same profile

> **💡 Tip:** If you want a **publishable** browser client, Firefox is a viable path — see [au2001/icloud-passwords-firefox](https://github.com/au2001/icloud-passwords-firefox). Chrome is locked to Apple's IDs.

### Why a version with its own ID cannot work

On macOS 15.4+, reading the live vault requires either Apple's native helper (which recognizes only Apple's two IDs) or Apple-exclusive keychain authorization. Every other path is a dead end:

| Route | Result |
| --- | --- |
| Launch the helper through a proxy native host | Killed by the helper's parent-process launch constraint; the parent must be a whitelisted browser |
| Inject your own extension ID into the helper | Refused; the allowed IDs are hard-coded in the signed binary |
| `security` CLI / `Security.framework` | Returns 0 syncable items; cannot see the iCloud vault |
| Read `keychain-2.db` directly | The SQLite is readable, but the password blobs are encrypted and the key is locked behind an Apple-exclusive entitlement |
| Apple's [`password-manager-resources`](https://github.com/apple/password-manager-resources) contribution process | Authorizes browsers only by signed identity via OS updates; there is no entry point for third-party extensions |

Borrowing Apple's key is the only way in. On-device verification also found that the helper's whitelist file is a symlink into the signed system volume (SSV, read-only sealed), so even root cannot append a custom ID with SIP enabled.

### Apple public-key reference

These two are the manifest `key` of Apple's official iCloud Passwords extensions (public key, base64 / DER SubjectPublicKeyInfo). Putting one of them in this project's `manifest.json` `key` field makes the browser derive the corresponding extension ID at load time.

#### Why they are needed

The macOS native helper `PasswordManagerBrowserExtensionHelper` decides who may connect via the `allowed_origins` whitelist in its native-messaging host manifest. That manifest lives on the signed system volume — read-only and immutable. You can view the actual on-device contents with:

```bash
cat "/System/Cryptexes/App/Library/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json"
```

```
# /Library/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json is a symlink
# pointing to the real file on the signed system volume (SSV, read-only sealed) below:
/System/Cryptexes/App/Library/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json
  ↳ real volume path /System/Volumes/Preboot/Cryptexes/App/Library/Google/Chrome/NativeMessagingHosts/...

{
    "name": "com.apple.passwordmanager",
    "description": "PasswordManagerBrowserExtensionHelper",
    "path": "/System/Cryptexes/App/System/Library/CoreServices/PasswordManagerBrowserExtensionHelper.app/Contents/MacOS/PasswordManagerBrowserExtensionHelper",
    "type": "stdio",
    "allowed_origins": [
        "chrome-extension://pejdijmoenmkgeppbflobdenhhabjlaj/",   # Apple Chrome extension
        "chrome-extension://mfbcdcnpokpoajjciilocoachedjkima/"    # Apple Edge extension
    ]
}
```

The whitelist recognizes only these two IDs. To reach the helper, this extension's ID must be one of them, and the ID is derived from the `key` hash:

```
extension ID = first 16 bytes of SHA256(DER public key), each nibble mapped to a-p
```

So you can only borrow one of the two Apple public keys below; a self-generated key yields an ID that is not on the whitelist and cannot reach the helper (verified on-device: the whitelist file is on the read-only signed system volume, SIP enabled, no custom ID can be appended).

#### Chrome public key → ID `pejdijmoenmkgeppbflobdenhhabjlaj`

Source: Apple's official iCloud Passwords Chrome extension. Use this one when loading in Chrome.

```
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAk4xPYZla5XqlDN0PPiLCQAYRqdaR06jSl3sntEE5jHoe7XldFqhsdBSp4L8mozwjCwi6z5YtEpTV1L2k4WYmDuiwoH7YKGlQD/YbC8QMcPvGLWOr8WYfXWtECKv0Nx7Tahk8nCIDWgJVm8YmPIDhPv4o5VVrq6aUveCKvTOskHWFyRzSTC2VKpzIVX7F65UzqqOmqLfMpo6lfaLcKSC7G6oQLA/wS7hcGZEwZ11si6XWR4o/hDuUSt6zdacy/sc7H80eH3lMnEmvb6HoB7+KvxfGIU7dqRmhA/w/X0qkiIJYeoo4tZrNxBj7TTLz9hnHUbMRwJqsoIU+pkoprgFWDQIDAQAB
```

#### Edge public key → ID `mfbcdcnpokpoajjciilocoachedjkima`

Source: Apple's official iCloud Passwords Edge extension, extracted on-device from `~/Library/Application Support/Microsoft Edge/Default/Extensions/mfbcdcnpokpoajjciilocoachedjkima/3.3.0_0/manifest.json`. Use this one when loading in Edge.

```
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA+TQP8e6VgCOUmwbwfJF+tIh99O9CkdErBGzk1KUxRetfXX6MuJVo10DEDE3e94WHwzzBiy9izP9q9zfNOGoT+9FkB3ebOQ8oZWaKMP8Y4070OC0u4csPb7ScL0LF3VbcotaKuLRYgZxtzj4QTtntsfdi2nhjx/liTk3hQDQyCMFcCZjT9ZfGnVtPcgYrbRrkfdX756p14wzSFvS6VgrsoiJCpbBOLOT66S7hj0fveP1w0swSU31mHdnX9VRkQSBKkEf7ScahE0P6sx8wdza+hp/z5KUsiM/ejJ8MAyPWcCMsyxqf+SmmmB0FpT0q6RA6cTtzQ/bfQJhO40raxSWiewIDAQAB
```

#### Verify

Confirm a key derives the expected ID:

```bash
python3 -c "
import base64,hashlib
k=base64.b64decode('<paste key>')
h=hashlib.sha256(k).hexdigest()[:32]
print(''.join(chr(ord('a')+int(c,16)) for c in h))
"
```

Both were verified on-device: Chrome key → `pejdij...`, Edge key → `mfbcdc...`.

#### Notes

- Within one profile, your extension and Apple's official same-ID extension cannot coexist; disable / remove Apple's corresponding extension before loading.
- These two IDs / keys belong to Apple, so this extension cannot be published to the Web Store — borrowing them is for local sideloading only.

---

## Security and audit

### Security notes

- The session key exists only in worker memory and never touches disk
- Every password query is end-to-end AES-GCM encrypted with the helper
- The PIN is used only to derive the SRP shared secret and is not stored
- Reading a password may trigger a Touch ID prompt — that is the helper, not this extension

### Verification and audit log

This extension went through an independent audit (protocol correctness, security, and a real-world complaint study), and the findings have all been addressed. This section records them, including one error in the original "100/100 passing" claim.

#### A correction to the original test

The first crypto test reported "100/100 handshakes passing." That test was self-consistent but wrong: it ran the client against a server mock that used the same broken group prime and the same IV frame format, so both were non-standard yet consistent with each other. The audit caught two real bugs the test could not, because it never checked against the RFC or the helper's actual reply format. The test was rewritten to assert that the prime equals the RFC 5054 standard value, and to decrypt replies the way the helper frames them (IV first) rather than the way requests are framed.

#### Key fixes

| # | Problem | Resolution |
| --- | --- | --- |
| **C3** | The SRP group prime was corrupted: an extra `9` made it 3076-bit, non-standard and weak | Replaced with the exact RFC 5054 3072-bit prime; added a startup assertion (768 hex digits). [`srp.js`](src/srp.js) |
| **—** | AES-GCM decryption read the IV from the wrong end. The helper sends replies as `iv ‖ ciphertext` (confirmed against Apple's decompiled `SecretSession.decrypt` and the Firefox reference implementation) | `decrypt()` takes the first 16 bytes as the IV; `encrypt()` keeps the IV at the end for requests (Apple deliberately made it asymmetric). [`srp.js`](src/srp.js) |
| **C1** | Any in-extension message could retrieve or fill a password for an attacker-specified origin | The background rejects messages not from its own UI (`sender.tab === undefined && sender.id === runtime.id`), removes the original `getPassword` path, and resolves the target tab / origin from the real active tab, never trusting caller input. [`background.js`](src/background.js) |
| **C2** | The content script filled without checking origin or visibility; a hidden field on evil.com could capture the fill | Filling requires the page host to match the pinned `expectedHost`, requires an in-extension sender, skips invisible / zero-size / hidden fields, and the background rejects non-HTTPS pages. [`content.js`](src/content.js), [`background.js`](src/background.js) |

#### Other hardening

- **SRP range checks (H1):** reject server public keys outside `(0, N)`, reject `u == 0`. [`srp.js`](src/srp.js)
- **Downgrade resistance (H2):** validate the `PROTO` field on every handshake; the capabilities flag is treated leniently because a real helper may omit it (consistent with the reference implementation), so the mode is negotiated via PROTO.
- **Concurrent-query collisions:** the native protocol echoes the same `cmd` with no correlation id, so overlapping requests could cross wires or hang. All exchanges are serialized behind a single mutex (verified: max concurrency = 1). [`protocol.js`](src/protocol.js)
- AES keys are imported with `extractable: false`.
- **Minimal permissions:** the manifest requests only `nativeMessaging`, `alarms`, and `storage`, plus a statically declared content script — no `tabs`, `scripting`, `activeTab`, or `privacy`.

#### A fill suggestion that was not adopted

One audit suggested padding all SRP hash inputs in `computeM` for consistency. But Apple's decompiled extension `_calculateM` / `createSessionKey` pads only `g` (and pads `A`, `B` only for the hash of `u`), leaving `A`, `B`, `salt`, `K` unpadded in `M`. This code matches Apple; padding would break interoperability with the real helper.

#### Verified vs unverified

**Verified (automated):**

- The group prime equals the RFC 5054 standard value (384 bytes / 768 hex digits)
- 100/100 SRP handshakes agree on the shared secret against a correct server mock
- `decrypt()` parses AES-GCM replies in the helper's frame format (IV first)
- SRP range checks reject `B=0` and `B=N`
- Request serialization: 5 overlapping calls execute strictly one at a time
- Manifest references, ES module import graph, content-script classic-script safety, icons

**Unverified (needs a Mac and the PIN on screen):**

- End-to-end connect → PIN → list → fill against the real helper
- Side-by-side behavior comparison with Apple's extension on real sites (via `test-harness/`)

---

## Credits and license

The protocol implementation is derived from [au2001/icloud-passwords-firefox](https://github.com/au2001/icloud-passwords-firefox) (Apache-2.0). See [`NOTICE`](./NOTICE).

License: **Apache-2.0**, see [`LICENSE`](./LICENSE).

> Not affiliated with or endorsed by Apple Inc.
