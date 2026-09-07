import XCTest

enum UIEnv {
    static var username: String? { ProcessInfo.processInfo.environment["NEXUS_UI_TEST_USERNAME"] }
    static var password: String? { ProcessInfo.processInfo.environment["NEXUS_UI_TEST_PASSWORD"] }
}

extension XCTestCase {

    @MainActor
    func signInIfNeeded(_ app: XCUIApplication) throws {
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
