import XCTest

enum UIEnv {
    static var username: String? { ProcessInfo.processInfo.environment["NEXUS_UI_TEST_USERNAME"] }
    static var password: String? { ProcessInfo.processInfo.environment["NEXUS_UI_TEST_PASSWORD"] }
}

extension XCTestCase {

    @MainActor
    func signInIfNeeded(_ app: XCUIApplication) {
        guard let username = UIEnv.username, let password = UIEnv.password else {
            throw XCTSkip("Set NEXUS_UI_TEST_USERNAME and NEXUS_UI_TEST_PASSWORD to run sign-in tests")
        }
        let usernameField = app.textFields["Username"]
        if usernameField.waitForExistence(timeout: 5) {
            usernameField.tap()
            usernameField.typeText(username)
            let passwordField = app.secureTextFields["Password"]
            passwordField.tap()
            passwordField.typeText(password)
            app.buttons["Sign In"].tap()
        }
    }
}

final class DashboardUITests: XCTestCase {

    @MainActor
    func testDashboardLoadsLiveMetrics() throws {
        let app = XCUIApplication()
        app.launch()
        try signInIfNeeded(app)

        let overall = app.staticTexts["Overall Status"]
        XCTAssertTrue(overall.waitForExistence(timeout: 20), "Dashboard did not load after sign-in")

        XCTAssertTrue(app.staticTexts["CPU"].exists, "CPU metric missing")
        XCTAssertTrue(app.staticTexts["Memory"].exists, "Memory metric missing")
        XCTAssertTrue(app.staticTexts["Storage"].exists, "Storage section missing")
        XCTAssertTrue(app.staticTexts["System"].exists, "System section missing")
    }
}
