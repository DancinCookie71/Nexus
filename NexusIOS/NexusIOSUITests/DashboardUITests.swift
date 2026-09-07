import XCTest

final class DashboardUITests: XCTestCase {

    @MainActor
    private func signInIfNeeded(_ app: XCUIApplication) {
        let usernameField = app.textFields["Username"]
        if usernameField.waitForExistence(timeout: 5) {
            usernameField.tap()
            usernameField.typeText("cookie")
            let passwordField = app.secureTextFields["Password"]
            passwordField.tap()
            passwordField.typeText("qogduf-0piFqi-doxziz")
            app.buttons["Sign In"].tap()
        }
    }

    @MainActor
    func testDashboardLoadsLiveMetrics() throws {
        let app = XCUIApplication()
        app.launch()
        signInIfNeeded(app)

        let overall = app.staticTexts["Overall Status"]
        XCTAssertTrue(overall.waitForExistence(timeout: 20), "Dashboard did not load after sign-in")

        XCTAssertTrue(app.staticTexts["CPU"].exists, "CPU metric missing")
        XCTAssertTrue(app.staticTexts["Memory"].exists, "Memory metric missing")
        XCTAssertTrue(app.staticTexts["Storage"].exists, "Storage section missing")
        XCTAssertTrue(app.staticTexts["System"].exists, "System section missing")
    }
}
