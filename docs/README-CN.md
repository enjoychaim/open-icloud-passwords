# Open iCloud Passwords for Chrome

> macOS 上用于 Chrome 与 Edge 的开源 iCloud 钥匙串自动填充

![platform](https://img.shields.io/badge/platform-macOS%2014%2B-black)
![browser](https://img.shields.io/badge/browser-Chrome%20%7C%20Edge-4285F4)
![manifest v3](https://img.shields.io/badge/manifest-v3-brightgreen)
![license](https://img.shields.io/badge/license-Apache--2.0-blue)

---

Apple 官方的 iCloud Passwords Chrome 扩展在约 2600 条评分里只有 **2.3 / 5**。它每隔几小时就忘记会话、重新索要 6 位验证码,在一次性验证码输入框上弹出「启用自动填充」气泡,还和 Chrome 自带的密码管理器互相打架。**本项目是它的替代客户端。**

它使用与 Apple 扩展相同的 native-messaging 协议(`com.apple.passwordmanager`):一次 SRP-6a 握手,其中 Mac 显示给你的 6 位码就是共享密钥,随后建立一条 AES-GCM 加密通道来做密码查询。同一个金库、同一套系统授权,只是客户端行为更合理。

连接实时金库,只提示一次 PIN,列出当前站点的登录项并完成填充。

## 目录

- [功能特性](#功能特性)
  - [概览:它修复了什么](#概览它修复了什么)
  - [与 Apple 官方扩展的完整对照](#与-apple-官方扩展的完整对照)
  - [它不修复什么](#它不修复什么)
- [安装与使用](#安装与使用)
  - [环境要求](#环境要求)
  - [安装步骤](#安装步骤)
  - [可选:隐藏浏览器自带的密码管理器](#可选隐藏浏览器自带的密码管理器)
- [工作原理](#工作原理)
- [扩展身份与限制](#扩展身份与限制)
  - [你必须先知道的前提](#你必须先知道的前提)
  - [为什么用自己 ID 的版本做不到](#为什么用自己-id-的版本做不到)
  - [Apple 公钥参考](#apple-公钥参考)
- [安全与审计](#安全与审计)
  - [安全说明](#安全说明)
  - [验证与审计日志](#验证与审计日志)
- [致谢与许可](#致谢与许可)

---

## 功能特性

### 概览:它修复了什么

| Apple 扩展被吐槽的问题 | 本项目的做法 |
| --- | --- |
| 每次重启、有时每隔几小时就重新索要 6 位码 | keep-alive 定时器保活 MV3 worker 与会话,每个真实会话只输一次码（[`background.js`](src/background.js)） |
| 每个字段（包括 OTP 框）都弹「启用自动填充」气泡 | 内联下拉只在真正的登录字段出现,绝不出现在一次性验证码框上（[`content.js`](src/content.js)） |
| 100% CPU / 打字卡顿 | 内容脚本零逐键开销,只在你聚焦登录字段时响应 |
| 悬停时重新下载每张图片去扫描二维码 | 完全没有图片或二维码扫描 |
| 填错字段或填错来源 | 填充被钉死在页面来源上,并跳过隐藏 / 被点击劫持的字段 |

两种填充方式:聚焦登录字段时的**内联下拉**,或**工具栏弹窗**。二者都走同一条经过来源校验、系统授权的路径。

### 与 Apple 官方扩展的完整对照

这里把关于 Apple 官方 iCloud Passwords Chrome / Edge 扩展的 18 条有据可查的吐槽,逐条映射到本项目的做法。「已验证」指 `test-harness/` 里有一个自动化的 headless 测试证明它(真实 Chrome 加载真实扩展)。来源是 Chrome Web Store、Apple Communities、Google / Brave 论坛、GitHub、AppleInsider、Macworld 上的用户报告。

图例:✅ 已修复 · 🟡 部分修复 · ⛔ 固有限制(任何扩展都无法修复)

| # | 吐槽 | Apple 的表现 | 本项目 | 状态 |
| --- | --- | --- | --- | --- |
| 1 | 反复索要 6 位码(头号吐槽) | 每次重启都重新配对,常常每隔几小时一次;每次 capabilities 重载都重置会话 | keep-alive 保活 MV3 worker 与实时会话,良性重连绝不重置,因此会话中途的频繁重新索要消失了。只有整个浏览器重启才重新配对(会话密钥绑定连接;Apple 与 au2001 都是每连接重新握手) | ✅/⛔ |
| 2 | 验证码始终收不到 | 助手死锁;说已生成验证码,却什么都不出现 | 用 8 秒超时加清晰报错替代挂起;助手本身坏了属于助手侧问题 | 🟡 |
| 3 | 「无法验证你的身份」 | 服务器 / 助手拒绝该浏览器 | 助手侧 / Apple 门禁 | ⛔ |
| 4 | 每个 OTP 框和随机字段都弹「启用自动填充」气泡 | 在一次性验证码框和非登录字段上弹出 | 绝不在 OTP 字段、搜索、标签、评论等上出现。已验证:22/22 对抗性页面无任何弹出;OTP 页面无弹出 | ✅ |
| 5 | 高 CPU / 打字卡顿 | 每次按键都重扫 DOM、重挂监听器 | 零逐键、零 DOM 扫描开销,只有一个 `focusin` 监听器。打字无成本 | ✅ |
| 6 | 与 Chrome 管理器双弹窗 | 两个管理器争抢同一字段 | 只压制 Chrome 的密码自动填充(见 #7),于是只剩一个干净的下拉 | ✅ |
| 7 | 破坏 Google Pay / 支付自动填充 | Apple 的「禁用 Chrome 自动填充」连信用卡与地址自动填充一起干掉 | 只压制 `passwordSavingEnabled`;Chrome 的支付与地址自动填充照常工作 | ✅ |
| 8 | 两步式(先用户名后密码)登录失败 | 不重新检测动态显示的密码字段 | `autocomplete="username"` 加全页密码检测,处理 Google / Microsoft 式两步登录。已在 UI 测试套件验证 | ✅ |
| 9 | 能填,但要手动改一个字符登录才成功 | 程序化填充不派发 `input`/`change`,页面 JS 看不到值 | 每次填充都派发真实的 `input` 与 `change` 事件。已验证:两个字段上事件都触发 | ✅ |
| 10 | 子域 / 域名匹配失败 | 严格精确 host 匹配 | 把完整 hostname 交给助手,由助手做 Apple 自己的关联域匹配 | 🟡 |
| 11 | 弹窗遮挡屏幕 / 无法关闭 | 覆盖层 z-index 与定位 bug,过早关闭 | 下拉锚定在字段下方,点击外部 / 滚动 / 缩放即关,绝不遮挡字段 | ✅ |
| 12 | 「永不保存」标志卡死,离开 Mac 无法清除 | 没有清除它的 UI | 尚无保存标志管理(无保存功能) | ⛔/不适用 |
| 13 | 保存新密码未经同意就自动保存 | 激进的自动捕获 | 无自动保存、无静默捕获;目前也还没有保存提示 | 🟡 |
| 14 | 不支持 Linux | 需要 macOS / Windows 助手 | 相同限制,助手只存在于 macOS / Windows | ⛔ |
| 15 | Touch ID 反复提示的摩擦 | 每次填充都提示 | 生物识别门禁由系统控制(`RequiresUserAuthenticationToFill`),无法移除 | ⛔ |
| 16 | 深色模式下工具栏图标看不见 | 单色图标 | UI 使用 `Canvas`/`CanvasText` 系统颜色(随主题);图标待办 | 🟡 |
| 17 | Windows 版本耦合 | 绑死到特定的 iCloud for Windows 构建 | 助手侧 | ⛔ |
| 18 | 点击劫持 / 自动填充 UI 伪装(Marek Tóth 2025;影响 Apple、1Password、Bitwarden) | 自动填充进不可见 / 被覆盖的字段 | 要求字段可见(尺寸 / 不透明度 / 屏外检查)、显式用户点击、来源钉定。已验证:屏外隐藏密码字段不被填充 | ✅ |

#### 它修复了 Apple 没修的

- OTP 气泡与误触发(#4):22/22 对抗性页面干净
- 会话内的频繁重新索要(#1):keep-alive 加不重置
- 「改一个字符才能登录」bug(#9):正确的 input 事件
- 破坏 Google Pay(#7):支付自动填充不受影响
- 打字卡顿(#5):零逐键开销
- 点击劫持窃取(#18):可见性、意图与来源检查

#### 它修不了的

- Linux(#14)、Windows 助手耦合(#17)、「不支持的浏览器」拒绝(#3),以及 #2 的助手侧部分,全都需要 Apple 的原生助手,任何扩展都控制不了。
- Touch ID 提示(#15)与每次浏览器重启一次的重新配对(#1):系统与协议都要求它们,Apple 的扩展同样如此。

#### 尚未构建

- 保存新密码的提示(#13),以及清除「永不保存」的设置 UI(#12)。

上面每个 ✅ 都有 `test-harness/automation/` 里的自动化测试支撑。最近一次运行的总计:22/22 对抗性、17/17 UI、4/4 PIN,外加多账户、input 事件(#9)与点击劫持(#18)。

### 它不修复什么

- **macOS 授权提示。** 助手读取密码时,macOS 自身会索要 Touch ID 或登录密码。那是金库为每条凭据设置的 `RequiresUserAuthenticationToFill` 标志。Chrome 自带管理器之所以能跳过,只因为它把密码存在自己的数据库里而非 iCloud 金库;去掉它就等于放弃实时金库访问。
- **不支持 Linux。** 与 Apple 一样,原生助手只存在于 macOS 与 Windows。
- **不做 passkey 或 TOTP 管理。** 超出范围,本项目只读密码与登录名。
- **它仍然依附于 Apple 的助手。** 若 Apple 改动或弄坏它(过往 macOS 更新有过),本项目也会跟着坏。

---

## 安装与使用

### 环境要求

- macOS 14 (Sonoma) 或更高,已登录 iCloud 且开启 Passwords
- Chrome 或 Edge
- 已移除或禁用 Apple 官方 iCloud Passwords 扩展

### 安装步骤

```bash
git clone https://github.com/ManiForoughi2/open-icloud-passwords.git
```

1. 禁用 Apple 官方 iCloud Passwords 扩展(它占用同一个 ID)
2. 打开 `chrome://extensions`（Edge 用 `edge://extensions`),开启右上角**开发者模式**
3. 点击**加载已解压的扩展程序**,选择 `open-icloud-passwords` 文件夹
4. 确认 ID 与你所用浏览器匹配(切换 key 见 [Apple 公钥参考](#apple-公钥参考)):
   - Chrome → `pejdijmoenmkgeppbflobdenhhabjlaj`
   - Edge → `mfbcdcnpokpoajjciilocoachedjkima`
5. 点工具栏图标,输入 Mac 显示的 6 位码,完成
6. 打开一个有已保存登录的站点并填充

### 可选:隐藏浏览器自带的密码管理器

弹窗自己就能压制浏览器竞争性的保存气泡与自动填充下拉(页脚有开关)。若还想移除浏览器**整个**密码管理器 —— 地址栏钥匙图标与内置自动填充 —— 有一个一次性助手,因为扩展本身无法写入 macOS 策略:

```bash
./native/install.sh   # 注册一个极小的 native 助手,仅 macOS
```

然后彻底退出并重开浏览器(`Cmd+Q`)。弹窗里的 **彻底隐藏浏览器密码管理器** 开关此时生效;它为你所有 Chromium 浏览器设置 `PasswordManagerEnabled=false`。随时用 `./native/uninstall.sh` 撤销。该助手只运行三条固定的 `defaults` 命令,且只接受来自本扩展 ID 的消息。

---

## 工作原理

```
popup.js / content.js
        │  runtime messages
        ▼
background.js  ──  keep-alive 定时器保活会话
        │
        ▼
protocol.js  ──  chrome.runtime.connectNative("com.apple.passwordmanager")
        │            GET_CAPABILITIES → m0(challenge/PIN)→ m2(verify)→ 查询
        ▼
srp.js + crypto.js   SRP-6a (RFC 5054, 3072-bit) + AES-GCM 会话
        ▼
PasswordManagerBrowserExtensionHelper(macOS 原生,连 iCloud 钥匙串)
```

模块职责:

| 文件 | 职责 |
| --- | --- |
| [`popup.js`](src/popup.js) / [`popup.html`](src/popup.html) / [`popup.css`](src/popup.css) | 工具栏弹窗 UI:输入 PIN、列出并填充登录项、功能开关 |
| [`content.js`](src/content.js) | 内容脚本:检测登录字段、渲染内联下拉、执行填充 |
| [`background.js`](src/background.js) | MV3 service worker:keep-alive 保活、消息路由、来源 / 标签页解析 |
| [`protocol.js`](src/protocol.js) | native-messaging 客户端:握手状态机、请求序列化 |
| [`srp.js`](src/srp.js) / [`crypto.js`](src/crypto.js) | SRP-6a 握手与 AES-GCM 会话加解密 |
| [`passkey-bridge.js`](src/passkey-bridge.js) / [`passkey-guard.js`](src/passkey-guard.js) | passkey 相关的页面桥接与守卫 |

---

## 扩展身份与限制

### 你必须先知道的前提

> **⚠️ 重要:** 这是一个从 GitHub **侧载(sideload)** 的工具,**无法上架 Chrome Web Store**,原因出在 macOS 本身。

macOS 14+ 自带一个原生助手 `PasswordManagerBrowserExtensionHelper`。在 macOS 15.4 及以后,该助手只接受两个**硬编码扩展 ID** 的连接,即 Apple 自己的 Chrome 与 Edge 扩展。这些 ID 编译在签名的系统二进制里,拒绝其他一切。

因此,要能连上,本扩展的 `manifest.json` 携带 Apple 扩展的公钥 `key`,使浏览器给它分配助手认可的那个 ID。两把可用的 key 及其派生 ID 记录在 [Apple 公钥参考](#apple-公钥参考):

| 浏览器 | 扩展 ID |
| --- | --- |
| Chrome | `pejdijmoenmkgeppbflobdenhhabjlaj` |
| Edge | `mfbcdcnpokpoajjciilocoachedjkima` |

这是当前 macOS 上 Chromium 扩展够到该助手的唯一办法。对你意味着:

- ✅ 以未打包方式加载、供**个人使用**时可用
- ❌ **无法发布到 Web Store**,因为那些 ID 与 key 归 Apple 所有
- ⚠️ 你必须**先禁用 Apple 官方 iCloud Passwords 扩展**,因为同一 profile 里两个扩展不能共用一个 ID

> **💡 提示:** 若想要一个**可发布**的浏览器客户端,Firefox 是走得通的路,见 [au2001/icloud-passwords-firefox](https://github.com/au2001/icloud-passwords-firefox)。Chrome 被锁死在 Apple 的 ID 上。

### 为什么用自己 ID 的版本做不到

在 macOS 15.4+,读取实时金库要么靠 Apple 的原生助手(它只认 Apple 那两个 ID),要么靠 Apple 专属的钥匙串授权。其他每条路都是死胡同:

| 路线 | 结果 |
| --- | --- |
| 通过代理 native host 启动助手 | 被助手父进程的 launch constraint 杀掉,父进程必须是白名单浏览器 |
| 把自己的扩展 ID 塞进助手 | 被拒,允许的 ID 硬编码在签名二进制里 |
| `security` CLI / `Security.framework` | 返回 0 个可同步项,看不到 iCloud 金库 |
| 直接读 `keychain-2.db` | SQLite 可读,但密码 blob 是加密的,密钥被 Apple 专属 entitlement 锁死 |
| Apple 的 [`password-manager-resources`](https://github.com/apple/password-manager-resources) 贡献流程 | 只按签名身份、通过 OS 更新授权浏览器,没有给第三方扩展的入口 |

借用 Apple 的 key 是唯一的入口。本机验证还发现:助手的白名单文件是指向签名系统卷(SSV,只读密封)的符号链接,在 SIP 开启下即便 root 也无法追加自定义 ID。

### Apple 公钥参考

这两把是 Apple 官方 iCloud Passwords 扩展的 manifest `key`(公钥,base64 / DER SubjectPublicKeyInfo)。把其中一把填进本项目 `manifest.json` 的 `key` 字段,浏览器加载时会据此派生出对应的扩展 ID。

#### 为什么需要它们

macOS 原生助手 `PasswordManagerBrowserExtensionHelper` 通过其 native-messaging host manifest 的 `allowed_origins` 白名单决定谁能连接。该 manifest 位于签名系统卷,只读、不可改。可用下面命令查看本机实际内容:

```bash
cat "/System/Cryptexes/App/Library/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json"
```

```
# /Library/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json 是一个符号链接,
# 指向下面签名系统卷(SSV, 只读密封)上的真实文件:
/System/Cryptexes/App/Library/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json
  ↳ 真实卷路径 /System/Volumes/Preboot/Cryptexes/App/Library/Google/Chrome/NativeMessagingHosts/...

{
    "name": "com.apple.passwordmanager",
    "description": "PasswordManagerBrowserExtensionHelper",
    "path": "/System/Cryptexes/App/System/Library/CoreServices/PasswordManagerBrowserExtensionHelper.app/Contents/MacOS/PasswordManagerBrowserExtensionHelper",
    "type": "stdio",
    "allowed_origins": [
        "chrome-extension://pejdijmoenmkgeppbflobdenhhabjlaj/",   # Apple Chrome 扩展
        "chrome-extension://mfbcdcnpokpoajjciilocoachedjkima/"    # Apple Edge 扩展
    ]
}
```

白名单只认这两个 ID。要连上助手,本扩展的 ID 必须是其中之一,而 ID 由 `key` 哈希派生:

```
扩展 ID = SHA256(DER 公钥) 前 16 字节，每个 nibble 映射到 a-p
```

因此只能借用下面两把 Apple 公钥之一;换成自建 key 会得到不在白名单里的 ID,连不上助手(已在本机验证:白名单文件在只读签名系统卷,SIP enabled,无法追加自定义 ID)。

#### Chrome 公钥 → ID `pejdijmoenmkgeppbflobdenhhabjlaj`

来源:Apple 官方 iCloud Passwords Chrome 扩展。在 Chrome 中加载时用这把。

```
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAk4xPYZla5XqlDN0PPiLCQAYRqdaR06jSl3sntEE5jHoe7XldFqhsdBSp4L8mozwjCwi6z5YtEpTV1L2k4WYmDuiwoH7YKGlQD/YbC8QMcPvGLWOr8WYfXWtECKv0Nx7Tahk8nCIDWgJVm8YmPIDhPv4o5VVrq6aUveCKvTOskHWFyRzSTC2VKpzIVX7F65UzqqOmqLfMpo6lfaLcKSC7G6oQLA/wS7hcGZEwZ11si6XWR4o/hDuUSt6zdacy/sc7H80eH3lMnEmvb6HoB7+KvxfGIU7dqRmhA/w/X0qkiIJYeoo4tZrNxBj7TTLz9hnHUbMRwJqsoIU+pkoprgFWDQIDAQAB
```

#### Edge 公钥 → ID `mfbcdcnpokpoajjciilocoachedjkima`

来源:Apple 官方 iCloud Passwords Edge 扩展,本机提取自 `~/Library/Application Support/Microsoft Edge/Default/Extensions/mfbcdcnpokpoajjciilocoachedjkima/3.3.0_0/manifest.json`。在 Edge 中加载时用这把。

```
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA+TQP8e6VgCOUmwbwfJF+tIh99O9CkdErBGzk1KUxRetfXX6MuJVo10DEDE3e94WHwzzBiy9izP9q9zfNOGoT+9FkB3ebOQ8oZWaKMP8Y4070OC0u4csPb7ScL0LF3VbcotaKuLRYgZxtzj4QTtntsfdi2nhjx/liTk3hQDQyCMFcCZjT9ZfGnVtPcgYrbRrkfdX756p14wzSFvS6VgrsoiJCpbBOLOT66S7hj0fveP1w0swSU31mHdnX9VRkQSBKkEf7ScahE0P6sx8wdza+hp/z5KUsiM/ejJ8MAyPWcCMsyxqf+SmmmB0FpT0q6RA6cTtzQ/bfQJhO40raxSWiewIDAQAB
```

#### 校验

确认某把 key 派生出预期 ID:

```bash
python3 -c "
import base64,hashlib
k=base64.b64decode('<粘贴 key>')
h=hashlib.sha256(k).hexdigest()[:32]
print(''.join(chr(ord('a')+int(c,16)) for c in h))
"
```

两把均已在本机验证:Chrome key → `pejdij...`,Edge key → `mfbcdc...`。

#### 注意

- 同一 profile 内,你的扩展与 Apple 官方同 ID 扩展不能共存,加载前需先禁用 / 移除 Apple 官方对应扩展。
- 这两个 ID / key 归 Apple 所有,因此本扩展无法发布到 Web Store —— 借用它们仅用于本地 sideload。

---

## 安全与审计

### 安全说明

- 会话密钥只存在于 worker 内存,绝不落盘
- 每次密码查询都与助手做端到端 AES-GCM 加密
- PIN 只用于派生 SRP 共享密钥,不做存储
- 读取密码可能触发 Touch ID 提示,那是助手,不是本扩展

### 验证与审计日志

本扩展经过了独立审计(协议正确性、安全性,以及一次真实世界的吐槽研究),相关发现均已解决。本节记录这些内容,包括原始「100/100 通过」说法中的一个错误。

#### 对原始测试的更正

第一版 crypto 测试报告「100/100 握手通过」。该测试自洽但错误:它让客户端对着一个使用了同样被破坏的群素数、同样 IV 帧格式的服务器模拟运行,于是双方虽都非标准却彼此一致。审计抓出了两个该测试抓不到的真实 bug,因为它从未对照 RFC 或助手实际回复格式。测试被重写为:断言素数等于 RFC 5054 标准值,并按助手的帧方式(IV 在前)解密回复,而非按请求的帧方式。

#### 关键修复

| # | 问题 | 解决 |
| --- | --- | --- |
| **C3** | SRP 群素数被破坏:一个多出的 `9` 让它变成 3076 位,非标准且弱 | 换成精确的 RFC 5054 3072 位素数;加了启动断言(768 个十六进制位)。[`srp.js`](src/srp.js) |
| **—** | AES-GCM 解密从错误的一端读 IV。助手把回复发为 `iv ‖ ciphertext`(对照 Apple 反编译的 `SecretSession.decrypt` 与 Firefox 参考实现确认) | `decrypt()` 把前 16 字节作为 IV;`encrypt()` 对请求保持 IV 在后(Apple 有意做成不对称)。[`srp.js`](src/srp.js) |
| **C1** | 任意扩展内消息都能为攻击者指定的来源取出或填充密码 | 后台拒绝非本 UI 的消息(`sender.tab === undefined && sender.id === runtime.id`),移除了原始 `getPassword` 路径,并从真实活动标签页解析目标标签 / 来源,绝不采信调用方输入。[`background.js`](src/background.js) |
| **C2** | 内容脚本不校验来源或可见性就填充;evil.com 上一个隐藏字段即可捕获填充 | 填充要求页面 host 匹配钉死的 `expectedHost`,要求扩展内发送者,跳过不可见 / 零尺寸 / 隐藏字段,且后台拒绝非 HTTPS 页面。[`content.js`](src/content.js)、[`background.js`](src/background.js) |

#### 其他加固

- **SRP 范围检查(H1):** 拒绝落在 `(0, N)` 之外的服务器公钥,拒绝 `u == 0`。[`srp.js`](src/srp.js)
- **抗降级(H2):** 校验每次握手的 `PROTO` 字段;capabilities 标志被宽松对待,因为真实助手可能省略它(与参考实现一致),故模式由 PROTO 协商决定。
- **并发查询冲突:** 原生协议回显相同的 `cmd` 且无关联 id,重叠请求可能串线或挂起。所有交换都被序列化在一把互斥锁后(已验证:最大并发 = 1)。[`protocol.js`](src/protocol.js)
- AES 密钥以 `extractable: false` 导入。
- **精简权限:** 去掉 `tabs` 与 `scripting`,改用 `activeTab` 加一个静态声明的内容脚本。

#### 一个未采纳的填充建议

一次审计建议在 `computeM` 里对所有 SRP 哈希输入做填充以求一致。但 Apple 反编译扩展里的 `_calculateM` / `createSessionKey` 只填充 `g`(并仅为 `u` 的哈希填充 `A`、`B`),在 `M` 中保持 `A`、`B`、`salt`、`K` 不填充。本代码已与 Apple 一致,填充反而会破坏与真实助手的互操作。

#### 已验证 vs 未验证

**已验证(自动化):**

- 群素数等于 RFC 5054 标准值(384 字节 / 768 十六进制位)
- 100/100 SRP 握手在正确的服务器模拟下就共享密钥达成一致
- `decrypt()` 能解析助手帧格式(IV 在前)的 AES-GCM 回复
- SRP 范围检查拒绝 `B=0` 与 `B=N`
- 请求序列化:5 个重叠调用严格逐个执行
- manifest 引用、ES 模块导入图、内容脚本经典脚本安全性、图标

**未验证(需要一台 Mac 与屏幕上的 PIN):**

- 对真实助手的端到端 连接 → PIN → 列表 → 填充
- 在真实站点上与 Apple 扩展的并排行为对比(用 `test-harness/`)

---

## 致谢与许可

协议实现衍生自 [au2001/icloud-passwords-firefox](https://github.com/au2001/icloud-passwords-firefox)(Apache-2.0)。见 [`NOTICE`](./NOTICE)。

许可:**Apache-2.0**,见 [`LICENSE`](./LICENSE)。

> 与 Apple Inc. 无关联,亦未获其背书。
