# Swift macOS and iOS Agent Development Standard

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/SWIFT-AGENT-STANDARD.md
**Description:** Execution standard for AI coding agents (and human reviewers) doing Swift / SwiftUI work on macOS and iOS in this repo. Applies to everything under `gui-macos/`.
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2026-06-19
**Last Updated:** 2026-06-19
**Last Updated By:** Libor Ballaty (via Claude agent)

Version: 1.0
Audience: AI coding agents, human reviewers, technical leads
Scope: Swift, SwiftUI, macOS, iOS, iPadOS, shared Apple-platform app development.

This repo's primary Swift surface today is `gui-macos/` (macOS MenuBarExtra app). Anywhere this standard says "the agent must," it applies to AI coding work in that surface.

---

## 1. Purpose

This document defines how an AI coding agent must approach Swift development for macOS and iOS.

The document is written as an execution standard, not as a general tutorial. The agent should use it to:

1. Inspect an existing Swift project.
2. Plan safe implementation changes.
3. Choose appropriate Apple-platform technologies.
4. Write maintainable Swift code.
5. Avoid common SwiftUI, concurrency, Xcode, signing, and platform-specific problems.
6. Implement tests.
7. Validate changes before reporting completion.
8. Clearly document what was done, what was tested, and what remains risky.

The agent must optimize for correctness, maintainability, native platform behavior, testability, accessibility, privacy, and security.

---

## 2. Agent Operating Rules

### 2.1 Non-Negotiable Rules

The agent must follow these rules unless the user explicitly overrides them.

1. Do not perform broad rewrites unless the user explicitly requests a refactor.
2. Do not change bundle identifiers, signing teams, entitlements, deployment targets, or app capabilities casually.
3. Do not add third-party dependencies unless Apple-native APIs are insufficient.
4. Do not hardcode secrets, API keys, tokens, passwords, or private endpoints.
5. Do not store sensitive values in `UserDefaults`, app bundle files, source files, logs, or plain local files.
6. Do not use force unwraps in production code unless the failure would indicate a programmer error and the reason is documented.
7. Do not place networking, persistence, or business logic directly in SwiftUI view bodies.
8. Do not suppress Swift concurrency warnings without explaining the cause and the safer alternative.
9. Do not use `@unchecked Sendable` unless there is a documented safety argument.
10. Do not mark work as complete unless build and test validation has been attempted or the inability to validate is clearly explained.

### 2.2 Required Work Pattern

For every implementation task, the agent must use this workflow:

1. Inspect project structure.
2. Identify targets, schemes, packages, deployment targets, Swift version, and platform support.
3. Build the current project before changing code, where practical.
4. Record pre-existing build or test failures.
5. Make a small coherent change.
6. Add or update tests.
7. Build affected targets.
8. Run relevant tests.
9. Check platform-specific behavior.
10. Report changes, validation, risks, and next steps.

### 2.3 When the Agent Encounters Ambiguity

If the ambiguity blocks safe implementation, the agent should ask for clarification.

If the ambiguity does not block safe progress, the agent should:

1. Make the least risky assumption.
2. State the assumption in the final report.
3. Avoid irreversible changes.
4. Keep the implementation easy to revise.

Examples:

| Ambiguity                       | Agent behavior                                                                                      |
| ------------------------------- | --------------------------------------------------------------------------------------------------- |
| Unknown deployment target       | Inspect project settings. Do not use APIs unavailable to the target.                                |
| Unknown architecture preference | Follow existing architecture. If no architecture exists, use simple SwiftUI plus testable services. |
| Unknown distribution path       | Do not change signing. Document App Store versus Developer ID implications.                         |
| Unknown backend API contract    | Create protocol boundaries and mock data. Do not invent production endpoints.                       |

---

## 3. Initial Project Inspection Checklist

Before coding, inspect and document the following.

### 3.1 Repository Structure

Look for:

```text
Package.swift
*.xcodeproj
*.xcworkspace
*.xctestplan
Sources/
Tests/
App/
Shared/
Features/
Resources/
*.entitlements
Info.plist
fastlane/
.github/workflows/
```

### 3.2 Xcode Project Information

Run where applicable:

```bash
xcodebuild -list
```

Record:

1. Project name.
2. Workspace name, if present.
3. Schemes.
4. App targets.
5. Unit test targets.
6. UI test targets.
7. Swift packages.
8. Deployment targets.
9. Bundle identifiers.
10. Signing configuration.

### 3.3 Swift Package Information

If `Package.swift` exists, run:

```bash
swift package describe
swift build
swift test
```

Record:

1. Package products.
2. Package targets.
3. Test targets.
4. External dependencies.
5. Platform declarations.
6. Swift tools version.

### 3.4 Platform Support

Identify whether the app supports:

1. iOS only.
2. macOS only.
3. iOS and iPadOS.
4. macOS and iOS through shared SwiftUI.
5. Mac Catalyst.
6. visionOS, watchOS, or tvOS.
7. App extensions.
8. Widgets.
9. Menu bar app behavior.
10. Background services or helper tools.

Do not assume iOS and macOS should behave identically.

---

## 4. Technology Selection Rules

### 4.1 UI Framework Decision

Use SwiftUI by default for new Apple-platform UI work.

Use SwiftUI when:

1. Building new app screens.
2. Building cross-platform iOS/macOS UI.
3. The required controls exist in SwiftUI.
4. The UI can be expressed declaratively.
5. Accessibility and dynamic type can be supported cleanly.
6. The existing project already uses SwiftUI.

Use UIKit when:

1. The existing iOS app is UIKit-heavy.
2. The required control or behavior is significantly more reliable in UIKit.
3. The team needs mature UIKit behavior for complex navigation or collection views.
4. A small UIKit bridge is safer than a full SwiftUI rewrite.

Use AppKit when:

1. Building advanced macOS window management.
2. Building menu bar utilities.
3. Implementing complex document behavior.
4. Implementing advanced tables, outline views, or text editing.
5. Handling deep macOS system integration.
6. The existing macOS app is AppKit-heavy.

Use AppKit/UIKit bridges only when needed. Isolate them in platform-specific folders.

### 4.2 State Management Decision

Use the simplest state management that fits the feature.

| Need                                   | Preferred choice                                                 |
| -------------------------------------- | ---------------------------------------------------------------- |
| View-local UI state                    | `@State`                                                         |
| Child view editing parent state        | `@Binding`                                                       |
| App or feature model observed by views | `@Observable`                                                    |
| Environment-provided app service       | `@Environment`                                                   |
| Simple user setting                    | `@AppStorage`                                                    |
| Scene-specific restoration             | `@SceneStorage`                                                  |
| Shared persistence context             | SwiftData/Core Data context                                      |
| Legacy ObservableObject project        | Continue using `ObservableObject` unless migrating intentionally |

Do not introduce Redux-style state management, custom stores, or large dependency containers unless the project already uses them or the complexity clearly requires them.

### 4.3 Persistence Decision

| Need                                | Recommended option                                                     |
| ----------------------------------- | ---------------------------------------------------------------------- |
| Non-sensitive simple setting        | `UserDefaults`, usually through `@AppStorage`                          |
| Secret or token                     | Keychain                                                               |
| Simple local relational/object data | SwiftData                                                              |
| Existing mature data model          | Core Data                                                              |
| Complex migration requirements      | Core Data or carefully designed SwiftData                              |
| User-selected files                 | File system access with security-scoped handling on macOS where needed |
| Large cache                         | File cache or database                                                 |
| Cross-device sync                   | CloudKit or explicit backend sync                                      |
| Backend source of truth             | API client plus local cache where needed                               |

Do not use SwiftData just because it is modern. Use it when its OS support, migration profile, and model complexity fit the product.

### 4.4 Testing Framework Decision

> **Project caveat (added 2026-06-24, llamaCPPManager):** This project rejects
> mock/fake-based service tests in favor of **real-stack vertical-slice E2E
> tests**. The "Service tests with mocks/fakes" item below — and the other
> mock/protocol-mocking guidance elsewhere in this standard (see lines
> referencing "mock", "fake", "protocol so it can be mocked") — does not
> apply to this codebase. Use real subprocesses, real CLI invocations, and
> real model servers; cover error paths with structured `CLIError` cases
> and `LifecycleLog` logging rather than mocks. A full rewrite of the
> testing sections (§4.4 + later "Testing" sections) is tracked as a TODO
> follow-up.

Use Swift Testing for:

1. New pure Swift unit tests.
2. Package tests.
3. Parameterized tests.
4. Domain logic tests.
5. Service tests with mocks/fakes.

Use XCTest for:

1. UI tests.
2. XCUITest.
3. Performance tests.
4. Existing XCTest-heavy projects.
5. Incremental maintenance of existing test suites.

Swift Testing and XCTest may coexist. Do not rewrite existing XCTest tests solely for style reasons.

---

## 5. Recommended Project Structure

### 5.1 Small to Medium SwiftUI App

```text
AppName/
  AppName.xcodeproj
  App/
    AppNameApp.swift
    AppEnvironment.swift
    AppCommands.swift
  Features/
    Home/
      HomeView.swift
      HomeViewModel.swift
      HomeModels.swift
      HomeTests.swift
    Settings/
      SettingsView.swift
      SettingsViewModel.swift
      SettingsTests.swift
  Shared/
    Models/
    Services/
    Networking/
    Persistence/
    Components/
    Utilities/
  Platform/
    iOS/
      iOSPermissionService.swift
      iOSDocumentPicker.swift
    macOS/
      MacMenuCommands.swift
      MacFileImporter.swift
      MacWindowController.swift
  Resources/
    Assets.xcassets
    Localizable.xcstrings
  Tests/
  UITests/
```

### 5.2 Larger Modular App

```text
AppName/
  AppName.xcodeproj
  App/
    AppNameApp.swift
  Packages/
    AppCore/
      Sources/
      Tests/
    AppNetworking/
      Sources/
      Tests/
    AppPersistence/
      Sources/
      Tests/
    AppFeatures/
      Sources/
      Tests/
    AppDesignSystem/
      Sources/
      Tests/
    AppTestingSupport/
      Sources/
```

### 5.3 Dependency Direction

Dependencies should flow inward.

Recommended dependency direction:

```text
App target
  -> Feature modules
      -> Core/domain module
      -> Networking module
      -> Persistence module
      -> Design system module
```

Avoid:

1. Core domain logic importing SwiftUI unnecessarily.
2. Low-level packages importing app targets.
3. Networking code depending on views.
4. Persistence models leaking everywhere without boundaries.
5. Circular package dependencies.

---

## 6. Swift Coding Standards

### 6.1 Naming

Use clear, idiomatic Swift names.

Good:

```swift
var isLoading: Bool
var hasUnsavedChanges: Bool
func loadProfile() async throws -> Profile
func saveDocument(_ document: Document) async throws
func deleteSelectedItems()
```

Avoid:

```swift
var loadingFlag: Bool
func getProfile()
func doSave()
func process()
```

Rules:

1. Use nouns for types.
2. Use verbs for actions.
3. Make Boolean names read naturally.
4. Avoid abbreviations unless standard in the domain.
5. Avoid meaningless names like `Manager`, `Helper`, `Processor`, unless the role is otherwise very clear.

### 6.2 Access Control

Use the narrowest reasonable access.

```swift
struct ProfileView: View {
    private let userID: User.ID
    @State private var viewModel: ProfileViewModel

    var body: some View {
        ProfileContentView(viewModel: viewModel)
    }
}
```

Rules:

1. Prefer `private` for implementation details.
2. Use `internal` by default within a module.
3. Use `public` only for package APIs.
4. Avoid `open` unless external subclassing is intentional.
5. Do not expose mutable state unnecessarily.

### 6.3 Optionals

Rules:

1. Avoid force unwraps in production code.
2. Use `guard let` for required values.
3. Use optional chaining for non-critical optional access.
4. Avoid implicitly unwrapped optionals except for framework integration or tests.
5. Prefer model design that eliminates impossible nil states.

Bad:

```swift
let name = user!.profile!.name
```

Better:

```swift
guard let profile = user.profile else {
    throw ProfileError.missingProfile
}

let name = profile.name
```

### 6.4 Error Handling

Use explicit errors.

```swift
enum ProfileError: LocalizedError {
    case missingUserID
    case networkUnavailable
    case invalidServerResponse

    var errorDescription: String? {
        switch self {
        case .missingUserID:
            return "The user ID is missing."
        case .networkUnavailable:
            return "The network is unavailable."
        case .invalidServerResponse:
            return "The server returned invalid data."
        }
    }
}
```

Rules:

1. Do not silently ignore errors.
2. Do not use `try?` unless failure is acceptable and documented.
3. Map low-level errors to domain errors at boundaries.
4. Provide user-safe messages.
5. Preserve technical details for logs where safe.
6. Never log secrets or full personal data.

### 6.5 Comments and Documentation

Use comments for intent, trade-offs, and non-obvious behavior.

Good:

```swift
// The backend sends dates without timezone information.
// Interpret them in the user's current calendar to avoid shifting displayed deadlines.
let dueDate = localDateParser.parse(response.dueDate)
```

Bad:

```swift
// Parse date.
let dueDate = parser.parse(response.dueDate)
```

Public package APIs should use documentation comments.

```swift
/// Loads the user's profile from the configured profile service.
///
/// - Parameter userID: Stable identifier for the user.
/// - Returns: A decoded profile.
/// - Throws: `ProfileError` if the profile cannot be loaded.
func loadProfile(for userID: User.ID) async throws -> Profile
```

---

## 7. SwiftUI Implementation Rules

### 7.1 View Responsibilities

SwiftUI views should:

1. Declare layout.
2. Bind to state.
3. Trigger user actions.
4. Display loading, empty, success, and error states.
5. Delegate business logic to view models or services.

SwiftUI views should not:

1. Perform networking directly.
2. Perform persistence directly except simple SwiftData view queries in small features.
3. Decode API responses.
4. Hold long-running business processes.
5. Create services repeatedly in `body`.
6. Perform side effects inside computed view properties.

### 7.2 View Size

Break up views when:

1. `body` becomes difficult to read.
2. There are multiple independent UI sections.
3. A section needs its own preview.
4. A section has distinct accessibility behavior.
5. A section is reused elsewhere.

### 7.3 Side Effects

Do not put side effects in `body`. Use `.task`, `.onAppear`, explicit user actions, or lifecycle coordination. Be aware that `.task` can rerun if view identity changes. Make load operations idempotent where practical.

### 7.4 Lists and Identity

Use stable identifiers.

Rules:

1. Prefer `Identifiable` models.
2. Do not generate random IDs during rendering.
3. Avoid changing IDs when content changes.
4. Use stable backend IDs where available.
5. Use local generated IDs only when persisted consistently.

### 7.5 Previews

Every reusable view should include previews for relevant states: loaded, loading, empty, error, long text, dark mode, large Dynamic Type, macOS resized layout if cross-platform. Previews must not depend on live network calls.

---

## 8. Observation and View Models

### 8.1 Preferred Pattern for New SwiftUI Code

For modern SwiftUI projects targeting OS versions that support Observation, prefer `@Observable`.

Rules:

1. Mark UI-facing view models as `@MainActor`.
2. Keep long-running work outside the main actor where possible.
3. Inject services through initializers.
4. Avoid singletons.
5. Avoid making every service observable.
6. Keep observable state focused on UI needs.

### 8.2 Existing ObservableObject Projects

If the project already uses `ObservableObject`, do not migrate everything unless requested.

Migration rule:

1. New isolated features may use `@Observable` if deployment targets allow it.
2. Existing large `ObservableObject` code should be migrated incrementally.
3. Do not mix patterns inside one feature without a reason.
4. Document any migration boundary.

---

## 9. Concurrency Rules

### 9.1 Default Approach

Use structured concurrency: `async/await`, `Task`, `TaskGroup`, `actor`, `@MainActor`, cancellation-aware async functions.

Avoid: uncontrolled `Task.detached`, callback pyramids, blocking the main thread, shared mutable global state, ignoring cancellation, suppressing concurrency warnings as noise.

### 9.2 MainActor Rules

UI state updates must occur on the main actor. Do not perform CPU-heavy work on the main actor.

### 9.3 Cancellation

Any long-running operation must support cancellation via `try Task.checkCancellation()`.

If the agent starts a task from a view, it must consider: what happens if the view disappears, whether duplicate calls are possible, whether cancellation leaves state consistent, whether loading flags reset correctly, whether stale results can overwrite newer results.

### 9.4 Swift 6 Concurrency Migration

When working with Swift 6 or preparing for Swift 6:

1. Enable strict concurrency warnings before forcing full Swift 6 mode.
2. Fix issues module by module.
3. Prefer value types for data crossing concurrency boundaries.
4. Add `Sendable` conformance only when true.
5. Use actors for shared mutable state.
6. Mark UI-facing types `@MainActor`.
7. Avoid `@unchecked Sendable`.
8. Avoid `nonisolated` unless the semantics are clear.
9. Do not use `Task.detached` to bypass isolation.
10. Document any remaining warnings.

### 9.5 Actor Usage

Use actors for shared mutable state accessed from concurrent contexts. Do not put all services into actors by default.

---

## 10. Networking Rules

### 10.1 API Client Pattern

Use `URLSession` with `async/await`, behind a protocol so it can be mocked.

### 10.2 Required Network Handling

The agent must handle: invalid URL, missing response, non-2xx HTTP status, empty body where body is expected, decoding failure, network timeout, offline state, cancellation, authentication failure, server error.

### 10.3 Network Testing

Do not unit test against live APIs. Use protocol-based API clients, mock services, fake URL protocol where appropriate, local fixtures, deterministic JSON samples.

Required tests: successful response, HTTP error, invalid JSON, empty response, network thrown error, cancellation where practical, date decoding, optional/missing fields, authentication failure, retry behavior if implemented.

---

## 11. Persistence Rules

### 11.1 UserDefaults

Use only for non-sensitive settings (theme, last tab, onboarding flag). Not acceptable: tokens, passwords, private keys, personal data, large structured data.

### 11.2 Keychain

Use Keychain for access tokens, refresh tokens, user-issued API keys, credentials, sensitive local secrets. If code stores any token-like value outside Keychain, flag it as a security issue.

### 11.3 SwiftData / Core Data

Use SwiftData when deployment targets support it, the model is simple/moderate, and migration is manageable. Use Core Data when the app already uses it, the data model is mature/complex, or migration control is important. Do not migrate Core Data to SwiftData without product reason.

### 11.4 SwiftData Test Pattern

Use an in-memory `ModelConfiguration(isStoredInMemoryOnly: true)` container for tests.

---

## 12. macOS-Specific Development Rules

### 12.1 macOS Is Not Large iOS

Respect macOS expectations: menu bar, keyboard shortcuts, window resizing, multiple windows where appropriate, file import/export, drag and drop, settings window, pointer and right-click, focus and keyboard navigation, standard document behavior when relevant.

### 12.2 macOS SwiftUI Rules

Use SwiftUI for standard app UI. Use AppKit bridges for: advanced window behavior, complex menus, status bar apps, advanced table/outline/text, file panels beyond simple import/export, automation, helper apps, low-level events, legacy AppKit integration. Put bridges in `Platform/macOS/`.

### 12.3 macOS File Access

If sandboxed, consider: user-selected files/folders, security-scoped bookmarks, persistent access after restart, entitlements, read-only vs read-write, App Store sandbox requirements, drag-and-drop access, export/save panel behavior.

### 12.4 macOS Signing and Distribution

Mac App Store: App Sandbox + appropriate entitlements + no private APIs.
Direct distribution: Developer ID signing + Hardened Runtime + notarization + Gatekeeper test on clean Mac. Do not modify signing settings unless requested.

---

## 13. iOS-Specific Development Rules

### 13.1 iOS UX Expectations

Fast launch, safe areas, touch-first layout, smooth scrolling, Dynamic Type, dark mode, contextual permission prompts, background/foreground transitions, poor network, memory pressure.

### 13.2 iPadOS

If iPad is supported, test split view, Stage Manager, rotation, keyboard shortcuts, pointer interaction, larger layout, multi-column navigation, popovers, drag and drop, external keyboard.

### 13.3 Permissions

Request permissions only when needed and after the UI explains why. Add Info.plist usage description strings. Handle denial. Provide a path to Settings. Test first-run, allowed, denied, restricted.

### 13.4 App Store Readiness

Privacy labels, privacy manifest, account deletion if accounts exist, no private APIs, no misleading metadata, real-device testing, poor network behavior, fresh install, upgrade from previous version, permission prompts.

---

## 14. Cross-Platform macOS/iOS Rules

### 14.1 Share Logic, Not UX Blindly

Share: domain models, validation, formatting, API clients, persistence layer where practical, business rules, test fixtures, shared SwiftUI components where appropriate.

Separate: navigation, window management, menu commands, keyboard shortcuts, file import/export workflows, permission flows, touch vs pointer, layout density, settings presentation, platform-specific integrations.

### 14.2 Conditional Compilation

Use sparingly. Keep platform-specific code in platform folders. Use protocols for behavior differences. Avoid `#if os(...)` peppered through business logic.

### 14.3 Platform Abstraction

Abstract platform behavior behind a protocol; implement per platform.

---

## 15. Accessibility Rules

### 15.1 Minimum Requirements

VoiceOver labels, Dynamic Type, dark mode, sufficient contrast, keyboard navigation on macOS, meaningful button labels, no meaning conveyed only by color, proper focus order, large enough touch targets on iOS, resizable windows on macOS.

### 15.2 SwiftUI Accessibility Pattern

Icon-only buttons must have `.accessibilityLabel(...)`. Add `.accessibilityHint(...)` where the action is non-obvious.

### 15.3 Accessibility Testing Checklist

For every UI change: VoiceOver label for each interactive control, Dynamic Type layout, dark mode, high contrast, reduced motion, keyboard navigation, long localized strings, error message visibility, empty state clarity, button roles and destructive actions.

---

## 16. Security and Privacy Rules

### 16.1 Secrets

Never store secrets in: source code, app bundle resources, `UserDefaults`, plain local files, logs, committed test fixtures, screenshots, crash reports, analytics events, public documentation. Use Keychain.

### 16.2 Logging

Structured, privacy-aware. Do not log tokens, passwords, full personal data. Redact sensitive values. Include correlation IDs where useful. Avoid noisy logs in loops.

### 16.3 App Transport Security

Do not disable ATS globally. Scope exceptions to a specific domain, document why, revisit before release.

### 16.4 Privacy Review

For every feature collecting or transmitting data, document: what is collected, why, whether it leaves the device, where stored, whether linked to identity, whether shared, analytics use, deletion, consent, App Store privacy disclosure changes.

---

## 17. Dependency Management Rules

### 17.1 Default Package Manager

Use Swift Package Manager. Do not introduce CocoaPods or Carthage unless already used.

### 17.2 Acceptance Checklist

Before adding a dependency: problem solved? Apple framework alternative? maintenance? platform support? deployment-target support? license? transitive dependencies? app size? privacy disclosures? mockable in tests?

### 17.3 Rejection Rules

Reject if unmaintained, duplicates a native framework, needs unnecessary permissions, unclear license, too large, fragile runtime swizzling, doesn't support required platforms, blocks Swift 6 migration, lacks basic tests/docs, creates vendor lock-in.

---

## 18. Testing Standard

### 18.1 Required Test Layers

Unit, integration, UI, performance, accessibility, manual.

### 18.2 Unit Test Requirements

For each non-trivial domain function or service, test: success, empty input, invalid input, boundary values, error mapping, cancellation, decoding failure, persistence failure, permission denied, concurrency-sensitive behavior.

### 18.5 UI Test Rules

Use accessibility identifiers for stable elements. No arbitrary sleeps; use `waitForExistence`. Reset app state before tests. Keep UI tests focused on critical flows.

---

## 19. Build and Validation Commands

```bash
xcodebuild -list
xcodebuild -scheme AppName -destination 'platform=iOS Simulator,name=iPhone 16' build
xcodebuild -scheme AppName -destination 'platform=iOS Simulator,name=iPhone 16' test
xcodebuild -scheme AppName -destination 'platform=macOS' build
xcodebuild -scheme AppName -destination 'platform=macOS' test
swift build
swift test
xcodebuild clean -scheme AppName
```

In this repo, the canonical macOS build + install path is `llamacpp-manager install-gui` (see `CLAUDE.md` and `gui-macos/install_gui.sh`). Do not delete DerivedData automatically unless approved.

---

## 20. Performance Standard

Keep main thread responsive. Do not decode large payloads or process images on the main actor. Avoid repeated expensive work in SwiftUI `body`. Use lazy containers for large lists, stable list identity, pagination for large datasets. Test on real devices. Use Instruments before speculative optimization.

---

## 21. Common Gotchas

1. SwiftUI `body` recomputes frequently — keep side effects out.
2. `.onAppear` / `.task` can rerun — make loading idempotent.
3. Bad list identity (UUID() in render, index identity) — use stable IDs.
4. MainActor overuse — keep heavy work off main.
5. Swift 6 Sendable errors — fix actual safety, don't `@unchecked`.
6. Xcode signing failures — report exact error, don't rewrite settings.
7. macOS sandboxed file access — check entitlements / security-scoped bookmarks.
8. iOS permission denied — handle denied/restricted state.
9. Previews fail but build passes — fix previews when touching reusable views.
10. Tests fail only in CI — avoid timing sleeps, reset state, no order deps.

---

## 22. CI/CD Standard

PR checks: package resolution, iOS build, macOS build if applicable, unit tests, integration where applicable, UI smoke tests where practical, lint/format, strict concurrency warnings, release-config build where practical, test reports.

The agent must: use explicit schemes and destinations, capture logs, distinguish test failures from infra failures, avoid modifying signing to satisfy CI unless requested, keep CI changes minimal, document required secrets, avoid printing secrets.

---

## 23. Release Readiness Checklist

iOS: archive succeeds, real-device launch, critical flows, fresh install, upgrade, permissions clear, privacy labels reviewed, screenshots match behavior, no private APIs, safe crash/logging.

macOS: archive succeeds, launches outside Xcode, sandbox behavior tested, file access tested, signing valid, Hardened Runtime enabled if notarizing, Developer ID build notarized for direct distribution, Gatekeeper passes on downloaded artifact, clean-account test, update path tested.

---

## 24. Agent Reporting Format

Every coding response must include:

```text
Summary:
- What changed.

Files changed:
- Path 1
- Path 2

Validation:
- Build command run:
- Test command run:
- Result:

Known risks:
- Risk 1
- Risk 2

Assumptions:
- Assumption 1

Next steps:
- Concrete next step, if any.
```

If validation was not possible:

```text
Validation not completed:
- Reason:
- Exact command the user or CI should run:
- Expected result:
```

Do not claim tests passed unless they were actually run and passed.

---

## 25. Definition of Done

A Swift macOS/iOS task is complete only when:

1. The relevant target builds, or failure is documented as pre-existing or environmental.
2. Relevant tests pass, or skipped tests are explained.
3. New business logic has unit tests.
4. UI changes have at least basic preview or UI validation.
5. Interactive controls have accessibility labels.
6. iOS layout handles small and large devices.
7. macOS layout handles resizing if macOS is supported.
8. Errors are handled.
9. No secrets are introduced.
10. The final report is complete.

---

## 26. Practical Agent Prompt Addendum

When assigning a Swift task to an agent in this repo, include:

```text
Follow docs/SWIFT-AGENT-STANDARD.md.

Before changing code:
1. Inspect project structure, schemes, targets, deployment targets, Swift version, test setup.
2. Build the current project if possible (`llamacpp-manager install-gui --no-launch` for gui-macos).
3. Record pre-existing failures.

During implementation:
1. Make the smallest safe change.
2. Keep platform-specific code isolated.
3. Prefer SwiftUI for new UI unless the existing code or platform behavior requires UIKit/AppKit.
4. Use structured concurrency.
5. Add or update tests.
6. Do not alter signing, entitlements, bundle IDs, or deployment targets unless explicitly required.

After implementation:
1. Build affected targets.
2. Run relevant tests.
3. Report changed files, validation commands, results, assumptions, risks.
4. If validation cannot be run, provide exact commands for the user or CI.
```

---

## 27. Summary

Default for new Swift work in this repo:

1. SwiftUI for new UI.
2. Swift structured concurrency.
3. Swift Package Manager.
4. Swift Testing for new pure Swift unit tests.
5. XCTest/XCUITest for UI and performance tests.
6. Keychain for any secrets.
7. SwiftData or Core Data based on project needs.
8. Native macOS UX expectations (menu bar, keyboard, window resize, file panels).
9. Minimal dependencies.
10. Explicit build + test validation before claiming completion.

Inspect first, change narrowly, test realistically, document honestly.
