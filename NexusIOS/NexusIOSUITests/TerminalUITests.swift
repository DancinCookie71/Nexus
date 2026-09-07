import XCTest

final class TerminalUITests: XCTestCase {

    @MainActor
    private func openTerminal(_ app: XCUIApplication) {
        app.tabBars.buttons["Terminal"].tap()
        let connected = app.staticTexts["Connected"]
        XCTAssertTrue(connected.waitForExistence(timeout: 15), "Terminal did not connect")
    }

    @MainActor
    func testTerminalConnectsAndEchoes() throws {
        let app = XCUIApplication()
        app.launch()
        try signInIfNeeded(app)
        openTerminal(app)

        let commandField = app.textFields["Command"]
        XCTAssertTrue(commandField.waitForExistence(timeout: 10))
        commandField.tap()
        commandField.typeText("echo nexus-terminal-ok\n")

        let echoText = app.staticTexts.containing(NSPredicate(format: "label CONTAINS 'nexus-terminal-ok'")).firstMatch
        XCTAssertTrue(echoText.waitForExistence(timeout: 15), "Terminal did not show echoed output")
    }

    @MainActor
    func testTerminalSelectionMenuAppears() throws {
        let app = XCUIApplication()
        app.launch()
        try signInIfNeeded(app)
        openTerminal(app)

        let commandField = app.textFields["Command"]
        commandField.tap()
        commandField.typeText("echo selectable-text-12345\n")

        let outputText = app.staticTexts.containing(NSPredicate(format: "label CONTAINS 'selectable-text-12345'")).firstMatch
        XCTAssertTrue(outputText.waitForExistence(timeout: 15), "Terminal output missing before selection test")

        outputText.press(forDuration: 2.0)

        let copyItem = app.menuItems["Copy"]
        let selectAllItem = app.menuItems["Select All"]
        XCTAssertTrue(
            copyItem.waitForExistence(timeout: 5) || selectAllItem.waitForExistence(timeout: 5),
            "Text selection menu (Copy/Select All) did not appear"
        )
    }
}
